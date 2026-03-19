# File: app/chatbot/agent.py
"""Agent loop: LLM generates text, if it contains tool calls we execute and feed back.

Uses Ollama's native tool-calling API for reliable tool invocation.
Max iterations = 5 to prevent runaway loops.
"""

import json
import logging

from sqlalchemy.orm import Session

from app.chatbot.llm import LLMProvider, SYSTEM_PROMPT, OLLAMA_TOOLS
from app.chatbot.tools import TOOLS

logger = logging.getLogger("app.chatbot")

MAX_ITERATIONS = 5


def _parse_tool_calls(text: str) -> list[dict] | None:
    """Extract tool calls from the LLM response.

    Handles two formats:
    1. Native Ollama tool calls: {"tool_calls": [{"function": {"name": ..., "arguments": ...}}]}
    2. Legacy JSON format: {"tool": "...", "args": {...}}

    Returns list of {name, args} dicts, or None if no tool calls found.
    """
    cleaned = text.strip()
    for prefix in ("```json", "```"):
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix):]
            break
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()

    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            # Native Ollama format
            if "tool_calls" in parsed:
                calls = []
                for tc in parsed["tool_calls"]:
                    fn = tc.get("function", {})
                    calls.append({
                        "name": fn.get("name", ""),
                        "args": fn.get("arguments", {}),
                    })
                return calls if calls else None

            # Legacy format
            if "tool" in parsed:
                return [{"name": parsed["tool"], "args": parsed.get("args", {})}]
    except json.JSONDecodeError:
        pass

    # Try line-by-line for embedded JSON
    for line in text.strip().splitlines():
        line = line.strip()
        if line.startswith("{"):
            try:
                parsed = json.loads(line)
                if isinstance(parsed, dict) and "tool" in parsed:
                    return [{"name": parsed["tool"], "args": parsed.get("args", {})}]
            except json.JSONDecodeError:
                continue

    return None


def run_agent(user_message: str, provider: LLMProvider, db: Session) -> str:
    """Execute the agent loop with native tool calling.

    1. Send user message to LLM with tool definitions
    2. If LLM response contains tool calls, execute them
    3. Feed tool results back as context
    4. Repeat until LLM gives a plain text answer or max iterations hit

    Returns the final text response.
    """
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]

    for iteration in range(MAX_ITERATIONS):
        logger.info("Agent iteration %d/%d", iteration + 1, MAX_ITERATIONS)

        response_text = provider.generate(messages, tools=OLLAMA_TOOLS)
        tool_calls = _parse_tool_calls(response_text)

        if tool_calls is None:
            # Plain text response — agent is done
            return response_text

        # Execute each tool call
        tool_results = []
        for tc in tool_calls:
            tool_name = tc["name"]
            tool_args = tc["args"]

            if tool_name not in TOOLS:
                tool_results.append(f"Unknown tool '{tool_name}'. Available: {', '.join(TOOLS.keys())}")
                continue

            logger.info("Agent calling tool: %s(%s)", tool_name, tool_args)
            result = TOOLS[tool_name](tool_args, db)
            tool_results.append(result)

        # Feed tool results back
        messages.append({"role": "assistant", "content": response_text})
        combined_results = "\n\n".join(
            f"Tool result:\n{r}" for r in tool_results
        )
        messages.append({
            "role": "user",
            "content": f"{combined_results}\n\nNow answer the user's question using this real data. Do not make up any information.",
        })

    # Max iterations reached — return last LLM response
    logger.warning("Agent hit max iterations (%d)", MAX_ITERATIONS)
    return response_text
