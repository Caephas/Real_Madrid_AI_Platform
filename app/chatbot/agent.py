# File: app/chatbot/agent.py
"""Agent loop: LLM generates text, if it contains tool calls we execute and feed back.

Uses Ollama's native tool-calling API for reliable tool invocation.
Max iterations = 5 to prevent runaway loops.
"""

import json
import logging
from datetime import date as _date

from sqlalchemy.orm import Session

from app.chatbot.llm import LLMProvider, SYSTEM_PROMPT, OLLAMA_TOOLS
from app.chatbot.tools import TOOLS

logger = logging.getLogger("app.chatbot")

MAX_ITERATIONS = 5
MAX_HISTORY_MESSAGES = 8  # keep recent context bounded for small local models


def _system_messages() -> list[dict[str, str]]:
    """System prompt with current date injected (helps the model pick correct fixtures)."""
    return [
        {
            "role": "system",
            "content": (
                f"{SYSTEM_PROMPT}\n\n"
                f"Today's date: {_date.today().isoformat()} (current La Liga season). "
                "Use today's date when reasoning about upcoming fixtures."
            ),
        }
    ]


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
            cleaned = cleaned[len(prefix) :]
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
                    raw_args = fn.get("arguments", {})
                    if isinstance(raw_args, str):
                        try:
                            raw_args = json.loads(raw_args)
                        except json.JSONDecodeError:
                            raw_args = {}
                    calls.append(
                        {
                            "name": fn.get("name", ""),
                            "args": raw_args,
                        }
                    )
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


def run_agent(
    user_message: str,
    provider: LLMProvider,
    db: Session,
    history: list[dict[str, str]] | None = None,
) -> str:
    """Execute the agent loop with native tool calling.

    1. Send user message to LLM with tool definitions
    2. If LLM response contains tool calls, execute them
    3. Feed tool results back as context
    4. Repeat until LLM gives a plain text answer or max iterations hit

    Returns the final text response.
    """
    messages = _system_messages()
    if history:
        messages.extend(history[-MAX_HISTORY_MESSAGES:])
    messages.append({"role": "user", "content": user_message})

    for iteration in range(MAX_ITERATIONS):
        logger.info("Agent iteration %d/%d", iteration + 1, MAX_ITERATIONS)

        response_text = provider.generate(messages, tools=OLLAMA_TOOLS)
        tool_calls = _parse_tool_calls(response_text)

        if tool_calls is None:
            if not response_text.strip() and iteration < MAX_ITERATIONS - 1:
                # Some models spend their budget on reasoning and emit an empty
                # final message — nudge once before giving up.
                logger.warning("Empty LLM response (iteration %d) — retrying", iteration + 1)
                messages.append({"role": "assistant", "content": ""})
                messages.append(
                    {
                        "role": "user",
                        "content": "Your previous response was empty. Answer the user's question directly, using the tools if needed.",
                    }
                )
                continue
            # Plain text response — agent is done
            return response_text

        # Execute each tool call
        tool_results = []
        for tc in tool_calls:
            tool_name = tc["name"]
            tool_args = tc["args"]

            if tool_name not in TOOLS:
                tool_results.append(
                    f"Unknown tool '{tool_name}'. Available: {', '.join(TOOLS.keys())}"
                )
                continue

            logger.info("Agent calling tool: %s(%s)", tool_name, tool_args)
            result = TOOLS[tool_name](tool_args, db)
            tool_results.append(result)

        # Feed tool results back
        messages.append({"role": "assistant", "content": response_text})
        combined_results = "\n\n".join(f"Tool result:\n{r}" for r in tool_results)
        messages.append(
            {
                "role": "user",
                "content": f"{combined_results}\n\nNow answer the user's question using this real data. Do not make up any information.",
            }
        )

    # Max iterations reached — return last LLM response
    logger.warning("Agent hit max iterations (%d)", MAX_ITERATIONS)
    return response_text


def run_agent_stream(
    user_message: str,
    provider: LLMProvider,
    db: Session,
    history: list[dict[str, str]] | None = None,
):
    """Agent loop with streaming: yields dict events for SSE transport.

    Events:
      {"type": "delta", "content": str}   — a text chunk from the final answer
      {"type": "tool", "name": str}       — a tool is being invoked
      {"type": "error", "message": str}   — fatal provider error

    The final plain-text generation is streamed token-by-token; tool
    invocations in earlier iterations are reported but not streamed.
    """
    messages = _system_messages()
    if history:
        messages.extend(history[-MAX_HISTORY_MESSAGES:])
    messages.append({"role": "user", "content": user_message})

    for iteration in range(MAX_ITERATIONS):
        logger.info("Agent stream iteration %d/%d", iteration + 1, MAX_ITERATIONS)

        stream = provider.generate_stream(messages, tools=OLLAMA_TOOLS)
        tool_calls: list[dict] | None = None
        full_text_parts: list[str] = []
        emitted = False

        for event in stream:
            if event["type"] == "delta":
                emitted = True
                full_text_parts.append(event["content"])
                yield {"type": "delta", "content": event["content"]}
            elif event["type"] == "tool_calls":
                tool_calls = event["calls"]

        if tool_calls is None:
            if not emitted and iteration < MAX_ITERATIONS - 1:
                logger.warning("Empty LLM stream (iteration %d) — retrying", iteration + 1)
                messages.append({"role": "assistant", "content": ""})
                messages.append(
                    {
                        "role": "user",
                        "content": "Your previous response was empty. Answer the user's question directly, using the tools if needed.",
                    }
                )
                continue
            return  # answer fully streamed

        # Execute tool calls and feed results back
        tool_results = []
        for tc in tool_calls:
            tool_name = tc.get("name", "")
            tool_args = tc.get("args", {})
            if tool_name not in TOOLS:
                tool_results.append(
                    f"Unknown tool '{tool_name}'. Available: {', '.join(TOOLS.keys())}"
                )
                continue
            logger.info("Agent calling tool: %s(%s)", tool_name, tool_args)
            yield {"type": "tool", "name": tool_name}
            tool_results.append(TOOLS[tool_name](tool_args, db))

        response_text = "".join(full_text_parts)
        messages.append({"role": "assistant", "content": response_text})
        combined = "\n\n".join(f"Tool result:\n{r}" for r in tool_results)
        messages.append(
            {
                "role": "user",
                "content": f"{combined}\n\nNow answer the user's question using this real data. Do not make up any information.",
            }
        )

    logger.warning("Agent hit max iterations (%d)", MAX_ITERATIONS)
    yield {"type": "delta", "content": "\n\nI've gathered what I could — here's where I landed."}
