# File: app/chatbot/llm.py
"""LLM provider abstraction. Swap between Ollama (local) and Gemini (cloud).

Deep module pattern: simple interface (generate), complex internals (two backends).
"""

import json
import logging
from abc import ABC, abstractmethod

import httpx

from app.config import settings

logger = logging.getLogger("app.chatbot")

SYSTEM_PROMPT = """You are Hala Bot, an AI assistant for Real Madrid fans. You have access to tools that provide real data.

Rules:
- ALWAYS respond in English, regardless of the topic
- You ONLY discuss Real Madrid and La Liga football topics
- You MUST use tools to get real data before answering factual questions — do NOT make up facts
- To answer "who do we play next" questions, call get_next_match FIRST, then use its exact date and venue when calling predict_match
- Be concise and informative about Real Madrid
- If asked about non-football topics, politely redirect to Real Madrid

IMPORTANT: When the user asks about news, predictions, or live matches, you MUST call the appropriate tool FIRST. Never answer from your own knowledge for factual Real Madrid questions."""

# Ollama native tool definitions for structured tool calling
OLLAMA_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "predict_match",
            "description": "Predict the outcome of a Real Madrid La Liga match. Returns win/draw/loss probabilities.",
            "parameters": {
                "type": "object",
                "properties": {
                    "opponent": {
                        "type": "string",
                        "description": "Opponent team name, e.g. 'Barcelona'",
                    },
                    "venue": {
                        "type": "string",
                        "description": "'Home' or 'Away'",
                        "enum": ["Home", "Away"],
                    },
                    "date": {"type": "string", "description": "Match date in YYYY-MM-DD format"},
                },
                "required": ["opponent", "venue", "date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_commentary",
            "description": "Get live match commentary and score for any current Real Madrid match.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_articles",
            "description": "Get the latest Real Madrid news articles. Call this for ANY question about news, transfers, injuries, or recent events. Call with no arguments to get all latest news.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Number of articles to fetch (default 5, max 10)",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_next_match",
            "description": "Get the next upcoming Real Madrid fixture with its exact date and venue. Call this before predict_match for 'who do we play next' or 'what are our chances' questions.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
]


class LLMProvider(ABC):
    """Interface for LLM providers."""

    @abstractmethod
    def generate(self, messages: list[dict[str, str]], tools: list | None = None) -> str:
        """Generate a response given a conversation history. Returns raw text."""

    def generate_stream(self, messages: list[dict[str, str]], tools: list | None = None):
        """Generate a response as an event stream.

        Yields dicts:
          {"type": "delta", "content": str}
          {"type": "tool_calls", "calls": [{"name": str, "args": dict}]}
        """
        raise NotImplementedError


class OllamaProvider(LLMProvider):
    """Local Ollama LLM. Connects to the Ollama container via HTTP."""

    def __init__(self):
        self.base_url = settings.ollama_base_url
        self.model = settings.ollama_model

    def generate(self, messages: list[dict[str, str]], tools: list | None = None) -> str:
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"num_predict": 512},
            "think": False,
        }
        if tools:
            payload["tools"] = tools
        try:
            resp = httpx.post(url, json=payload, timeout=120)
            resp.raise_for_status()
            data = resp.json()
            msg = data.get("message", {})

            # Check for native tool calls in the response
            if msg.get("tool_calls"):
                # Return as JSON for the agent loop to parse
                import json

                return json.dumps({"tool_calls": msg["tool_calls"]})

            return msg.get("content", "")
        except httpx.HTTPError as e:
            logger.error("Ollama request failed: %s", e)
            raise RuntimeError(f"Ollama unavailable: {e}") from e

    def generate_stream(self, messages: list[dict[str, str]], tools: list | None = None):
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "options": {"num_predict": 512},
            "think": False,
        }
        if tools:
            payload["tools"] = tools

        try:
            with httpx.stream("POST", url, json=payload, timeout=120) as resp:
                resp.raise_for_status()
                tool_calls: list[dict] | None = None
                for line in resp.iter_lines():
                    if not line.strip():
                        continue
                    chunk = json.loads(line)
                    msg = chunk.get("message", {})

                    calls = msg.get("tool_calls")
                    if calls:
                        tool_calls = [
                            {
                                "name": c.get("function", {}).get("name", ""),
                                "args": c.get("function", {}).get("arguments", {}),
                            }
                            for c in calls
                        ]
                        continue

                    content = msg.get("content", "")
                    if content:
                        yield {"type": "delta", "content": content}

                if tool_calls:
                    yield {"type": "tool_calls", "calls": tool_calls}
        except httpx.HTTPError as e:
            logger.error("Ollama stream request failed: %s", e)
            raise RuntimeError(f"Ollama unavailable: {e}") from e


class GeminiProvider(LLMProvider):
    """Google Gemini cloud LLM. Optional fallback."""

    def __init__(self):
        self.api_key = settings.gemini_api_key
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not set")

    def generate(self, messages: list[dict[str, str]], tools: list | None = None) -> str:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={self.api_key}"
        contents = []
        for m in messages:
            role = "user" if m["role"] in ("user", "system") else "model"
            contents.append({"role": role, "parts": [{"text": m["content"]}]})

        try:
            resp = httpx.post(url, json={"contents": contents}, timeout=30)
            resp.raise_for_status()
            return resp.json()["candidates"][0]["content"]["parts"][0]["text"]
        except httpx.HTTPError as e:
            logger.error("Gemini request failed: %s", e)
            raise RuntimeError(f"Gemini unavailable: {e}") from e

    def generate_stream(self, messages: list[dict[str, str]], tools: list | None = None):
        """Stream from Gemini via SSE; falls back to a single non-streamed chunk."""
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"gemini-2.0-flash:streamGenerateContent?alt=sse&key={self.api_key}"
        )
        contents = []
        for m in messages:
            role = "user" if m["role"] in ("user", "system") else "model"
            contents.append({"role": role, "parts": [{"text": m["content"]}]})

        try:
            with httpx.stream("POST", url, json={"contents": contents}, timeout=60) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    payload = json.loads(line[5:].strip())
                    parts = payload.get("candidates", [{}])[0].get("content", {}).get("parts", [])
                    text = "".join(p.get("text", "") for p in parts)
                    if text:
                        yield {"type": "delta", "content": text}
        except (httpx.HTTPError, json.JSONDecodeError) as e:
            logger.warning("Gemini streaming failed (%s) — falling back to single response", e)
            yield {"type": "delta", "content": self.generate(messages, tools)}


class DeepSeekProvider(LLMProvider):
    """DeepSeek cloud LLM via the OpenAI-compatible Chat Completions API.

    Supports native function calling and SSE streaming. The model name is
    configurable (DEEPSEEK_MODEL); if the configured name is rejected by the
    endpoint, we retry once with the classic 'deepseek-chat' model.
    """

    def __init__(self):
        self.api_key = settings.deepseek_api_key
        if not self.api_key:
            raise ValueError("DEEPSEEK_API_KEY not set")
        self.base_url = settings.deepseek_base_url.rstrip("/")
        self.model = settings.deepseek_model

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _payload(self, messages: list[dict[str, str]], tools: list | None, stream: bool) -> dict:
        payload: dict = {
            "model": self.model,
            "messages": messages,
            "stream": stream,
            "max_tokens": 512,
        }
        if tools:
            payload["tools"] = tools
        return payload

    def _call(self, payload: dict, retried: bool = False):
        url = f"{self.base_url}/chat/completions"
        try:
            resp = httpx.post(url, json=payload, headers=self._headers(), timeout=120)
            if resp.status_code in (400, 404) and "model" in resp.text.lower() and not retried:
                logger.warning("Model '%s' rejected — retrying with 'deepseek-chat'", self.model)
                payload["model"] = "deepseek-chat"
                return self._call(payload, retried=True)
            resp.raise_for_status()
            return resp
        except httpx.HTTPError as e:
            logger.error("DeepSeek request failed: %s", e)
            raise RuntimeError(f"DeepSeek unavailable: {e}") from e

    def generate(self, messages: list[dict[str, str]], tools: list | None = None) -> str:
        resp = self._call(self._payload(messages, tools, stream=False))
        data = resp.json()
        message = data["choices"][0]["message"]

        if message.get("tool_calls"):
            calls = []
            for tc in message["tool_calls"]:
                fn = tc.get("function", {})
                raw_args = fn.get("arguments") or "{}"
                if isinstance(raw_args, str):
                    try:
                        args = json.loads(raw_args)
                    except json.JSONDecodeError:
                        args = {}
                else:
                    args = raw_args
                calls.append({"function": {"name": fn.get("name", ""), "arguments": args}})
            return json.dumps({"tool_calls": calls})
        return message.get("content") or ""

    def generate_stream(self, messages: list[dict[str, str]], tools: list | None = None):
        payload = self._payload(messages, tools, stream=True)
        url = f"{self.base_url}/chat/completions"
        try:
            with httpx.stream(
                "POST", url, json=payload, headers=self._headers(), timeout=120
            ) as resp:
                if resp.status_code in (400, 404) and payload["model"] != "deepseek-chat":
                    logger.warning(
                        "Model '%s' rejected — retrying with 'deepseek-chat'", self.model
                    )
                    payload["model"] = "deepseek-chat"
                    return self.generate_stream(messages, tools)
                resp.raise_for_status()

                tool_calls: dict[int, dict[str, str]] = {}
                for line in resp.iter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    raw = line[5:].strip()
                    if raw == "[DONE]":
                        break
                    chunk = json.loads(raw)
                    delta = chunk.get("choices", [{}])[0].get("delta", {})

                    calls = delta.get("tool_calls")
                    if calls:
                        for c in calls:
                            idx = c.get("index", 0)
                            fn = c.get("function", {})
                            entry = tool_calls.setdefault(idx, {"name": "", "args": ""})
                            if fn.get("name"):
                                entry["name"] = fn["name"]
                            if fn.get("arguments"):
                                entry["args"] += fn["arguments"]
                        continue

                    content = delta.get("content")
                    if content:
                        yield {"type": "delta", "content": content}

                if tool_calls:
                    calls = [
                        {
                            "name": entry["name"],
                            "args": json.loads(entry["args"] or "{}"),
                        }
                        for _, entry in sorted(tool_calls.items())
                    ]
                    yield {"type": "tool_calls", "calls": calls}
        except httpx.HTTPError as e:
            logger.error("DeepSeek stream request failed: %s", e)
            raise RuntimeError(f"DeepSeek unavailable: {e}") from e


def create_provider() -> LLMProvider:
    """Factory: create the configured LLM provider."""
    if settings.llm_provider == "deepseek":
        return DeepSeekProvider()
    if settings.llm_provider == "gemini":
        return GeminiProvider()
    return OllamaProvider()
