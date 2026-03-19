# File: app/chatbot/llm.py
"""LLM provider abstraction. Swap between Ollama (local) and Gemini (cloud).

Deep module pattern: simple interface (generate), complex internals (two backends).
"""

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
                    "opponent": {"type": "string", "description": "Opponent team name, e.g. 'Barcelona'"},
                    "venue": {"type": "string", "description": "'Home' or 'Away'", "enum": ["Home", "Away"]},
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
                    "limit": {"type": "integer", "description": "Number of articles to fetch (default 5, max 10)"},
                },
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


def create_provider() -> LLMProvider:
    """Factory: create the configured LLM provider."""
    if settings.llm_provider == "gemini":
        return GeminiProvider()
    return OllamaProvider()
