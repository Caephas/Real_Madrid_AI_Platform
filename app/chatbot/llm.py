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
- Use tools to get real data before answering factual questions
- Be concise and enthusiastic about Real Madrid
- If asked about non-football topics, politely redirect to Real Madrid

Available tools:
- predict_match: Predict the outcome of a Real Madrid match (pass opponent, venue, date)
- get_commentary: Get live match commentary for Real Madrid
- get_articles: Get latest Real Madrid news articles (optional category filter)

When you need to call a tool, respond with a JSON object:
{"tool": "<tool_name>", "args": {<arguments>}}

When you have enough information to answer the user, respond with plain text (no JSON).
"""


class LLMProvider(ABC):
    """Interface for LLM providers."""

    @abstractmethod
    def generate(self, messages: list[dict[str, str]]) -> str:
        """Generate a response given a conversation history. Returns raw text."""
        ...


class OllamaProvider(LLMProvider):
    """Local Ollama LLM. Connects to the Ollama container via HTTP."""

    def __init__(self):
        self.base_url = settings.ollama_base_url
        self.model = settings.ollama_model

    def generate(self, messages: list[dict[str, str]]) -> str:
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
        }
        try:
            resp = httpx.post(url, json=payload, timeout=120)
            resp.raise_for_status()
            return resp.json()["message"]["content"]
        except httpx.HTTPError as e:
            logger.error("Ollama request failed: %s", e)
            raise RuntimeError(f"Ollama unavailable: {e}") from e


class GeminiProvider(LLMProvider):
    """Google Gemini cloud LLM. Optional fallback."""

    def __init__(self):
        import google.generativeai as genai

        if not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY not set")
        genai.configure(api_key=settings.gemini_api_key)
        self.model = genai.GenerativeModel("gemini-2.0-flash")

    def generate(self, messages: list[dict[str, str]]) -> str:
        # Convert chat format to Gemini format
        history = []
        for msg in messages:
            role = "user" if msg["role"] == "user" else "model"
            history.append({"role": role, "parts": [msg["content"]]})

        try:
            chat = self.model.start_chat(history=history[:-1])
            response = chat.send_message(history[-1]["parts"][0])
            return response.text
        except Exception as e:
            logger.error("Gemini request failed: %s", e)
            raise RuntimeError(f"Gemini unavailable: {e}") from e


def create_provider() -> LLMProvider:
    """Factory: create the configured LLM provider."""
    if settings.llm_provider == "gemini":
        return GeminiProvider()
    return OllamaProvider()
