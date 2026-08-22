"""Vision provider for frame-by-frame match-call analysis.

DeepSeek's chat endpoint is text-only, so image analysis runs through Gemini
(configurable via GEMINI_API_KEY). The provider interface stays small so other
vision models can be dropped in later.
"""

import base64
import json
import logging
import re
import time

import httpx

from app.config import settings

logger = logging.getLogger("app.callanalysis.vision")

VISION_MODEL = settings.gemini_model

SYSTEM_PROMPT = """You are an expert football referee analyst with deep knowledge of the FIFA Laws of the Game.
You are shown a sequence of frames from a single match incident and must judge the referee's decision.

Rules:
- Judge ONLY what is visible in the provided frames. Never speculate about angles you cannot see.
- Apply the Laws of the Game precisely (fouls, penalties, offside, handball, cards, advantage).
- Reference the timestamp of each frame you rely on (e.g. 12.3s) and note which frame file you mean.
- Be decisive but honest: if the footage is inconclusive, say so ("unclear").

Respond with STRICT JSON only (no markdown fences), using this schema:
{
  "verdict": "correct_call" | "incorrect_call" | "unclear",
  "decision_type": "penalty" | "foul" | "offside" | "handball" | "red_card" | "yellow_card" | "clean" | "other",
  "confidence": <0-100>,
  "summary": "<2-3 sentence explanation>",
  "reasoning": [
    {"timestamp": <seconds>, "observation": "<what is visible in the frames at this moment>", "assessment": "<why it supports or contradicts the call>"}
  ],
  "laws_cited": ["<Law number and clause you applied, e.g. Law 12.1>"],
  "key_frames": [
    {"timestamp": <seconds>, "caption": "<what the frame shows>"}
  ]
}"""


class VisionUnavailable(RuntimeError):
    """Raised when no vision model is configured (e.g. missing GEMINI_API_KEY)."""


def _parse_json(text: str) -> dict:
    cleaned = text.strip()
    for fence in ("```json", "```"):
        if cleaned.startswith(fence):
            cleaned = cleaned[len(fence) :]
            break
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    match = re.search(r"\{.*\}", cleaned, re.S)
    if match:
        cleaned = match.group(0)
    return json.loads(cleaned)


def analyze_frames(
    frames: list[dict],
    context: str = "",
    rules_text: str | None = None,
) -> dict:
    """Send sampled frames to the vision model and return the structured verdict."""
    if not settings.gemini_api_key:
        raise VisionUnavailable(
            "Vision analysis requires a GEMINI_API_KEY (DeepSeek's chat API is text-only). "
            "Add one to .env to enable Call Review."
        )

    user_note = f"\n\nUser context: {context}" if context else ""
    # The Laws of the Game are read BEFORE judging, per the user's requirement.
    system = f"{rules_text}\n\n{SYSTEM_PROMPT}" if rules_text else SYSTEM_PROMPT
    parts = [{"text": system + user_note}]
    for frame in frames:
        with open(frame["file"], "rb") as f:
            parts.append(
                {
                    "inline_data": {
                        "mime_type": "image/jpeg",
                        "data": base64.b64encode(f.read()).decode(),
                    }
                }
            )

    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{VISION_MODEL}:generateContent?key={settings.gemini_api_key}"
    )
    payload = {
        "contents": [{"role": "user", "parts": parts}],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 2048},
    }
    text = None
    last_error: Exception | None = None
    resp = None
    for attempt in range(3):
        try:
            resp = httpx.post(url, json=payload, timeout=180)
            resp.raise_for_status()
            text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
            break
        except httpx.HTTPError as e:
            last_error = e
            status = getattr(resp, "status_code", None)
            if status in (429, 500, 502, 503, 504):
                logger.warning("Vision model transient failure (%s) — retry %d", e, attempt + 1)
                time.sleep(2**attempt)
                continue
            logger.error("Gemini vision request failed: %s", e)
            raise RuntimeError(f"Vision model unavailable: {e}") from e
        except (KeyError, IndexError) as e:
            last_error = e
            break
    if text is None:
        raise RuntimeError(f"Vision model failed after retries: {last_error}")

    try:
        return _parse_json(text)
    except json.JSONDecodeError as e:
        logger.error("Vision model returned non-JSON: %s", text[:300])
        raise RuntimeError("Vision model returned an unparseable response.") from e
