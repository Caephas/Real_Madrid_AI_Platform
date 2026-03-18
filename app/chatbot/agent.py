# File: app/chatbot/agent.py
"""Agent loop: LLM generates text, if it's a tool call we execute and feed back.

Max iterations = 5 to prevent runaway loops.
"""

import json
import logging

from sqlalchemy.orm import Session

from app.chatbot.llm import LLMProvider, SYSTEM_PROMPT
from app.chatbot.tools import TOOLS

logger = logging.getLogger("app.chatbot")

MAX_ITERATIONS = 5


def _parse_tool_call(text: str) -> dict | None:
    """Extract a tool-call JSON from the LLM response.

    The LLM is prompted to respond with {"tool": "...", "args": {...}}
    when it wants to call a tool. Returns None if the response is plain text.
    """
    # Strip markdown code fences
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
        if isinstance(parsed, dict) and "tool" in parsed:
            return parsed
    except json.JSONDecodeError:
        pass

    # Try each line individually (LLM may prepend text before JSON)
    for line in text.strip().splitlines():
        line = line.strip()
        if line.startswith("{"):
            try:
                parsed = json.loads(line)
                if isinstance(parsed, dict) and "tool" in parsed:
                    return parsed
            except json.JSONDecodeError:
                continue

    return None


def run_agent(user_message: str, provider: LLMProvider, db: Session) -> str:
    """Execute the agent loop.

    1. Send user message to LLM (with system prompt)
    2. If LLM response is a tool call, execute the tool
    3. Feed tool result back as context
    4. Repeat until LLM gives a plain text answer or max iterations hit

    Returns the final text response.
    """
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]

    for iteration in range(MAX_ITERATIONS):
        logger.info("Agent iteration %d/%d", iteration + 1, MAX_ITERATIONS)

        response_text = provider.generate(messages)
        tool_call = _parse_tool_call(response_text)

        if tool_call is None:
            # Plain text response — agent is done
            return response_text

        tool_name = tool_call.get("tool", "")
        tool_args = tool_call.get("args", {})

        if tool_name not in TOOLS:
            # Unknown tool — tell LLM and let it retry
            messages.append({"role": "assistant", "content": response_text})
            messages.append({
                "role": "user",
                "content": f"Unknown tool '{tool_name}'. Available tools: {', '.join(TOOLS.keys())}",
            })
            continue

        logger.info("Agent calling tool: %s(%s)", tool_name, tool_args)
        tool_result = TOOLS[tool_name](tool_args, db)

        # Feed tool result back into conversation
        messages.append({"role": "assistant", "content": response_text})
        messages.append({
            "role": "user",
            "content": f"Tool result for {tool_name}:\n{tool_result}\n\nNow answer the user's question using this data.",
        })

    # Max iterations reached — return last LLM response
    logger.warning("Agent hit max iterations (%d)", MAX_ITERATIONS)
    return response_text
