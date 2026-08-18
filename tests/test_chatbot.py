# File: tests/test_chatbot.py
"""Unit tests for the chatbot module."""

from unittest.mock import MagicMock

from app.chatbot.agent import _parse_tool_calls, run_agent


# --- Tool call parsing ---


def test_parse_tool_calls_native_format():
    """Ollama native tool_calls format."""
    text = '{"tool_calls": [{"function": {"name": "get_articles", "arguments": {}}}]}'
    result = _parse_tool_calls(text)
    assert result is not None
    assert len(result) == 1
    assert result[0]["name"] == "get_articles"


def test_parse_tool_calls_openai_string_arguments():
    """DeepSeek/OpenAI send tool arguments as a JSON string — must be decoded."""
    text = '{"tool_calls": [{"function": {"name": "predict_match", "arguments": "{\\"opponent\\": \\"Espanyol\\", \\"venue\\": \\"Away\\", \\"date\\": \\"2026-08-22\\"}"}}]}'
    result = _parse_tool_calls(text)
    assert result is not None
    assert result[0]["name"] == "predict_match"
    assert result[0]["args"] == {
        "opponent": "Espanyol",
        "venue": "Away",
        "date": "2026-08-22",
    }


def test_parse_tool_calls_legacy_json():
    text = '{"tool": "predict_match", "args": {"opponent": "Barcelona"}}'
    result = _parse_tool_calls(text)
    assert result is not None
    assert result[0]["name"] == "predict_match"


def test_parse_tool_calls_with_markdown_fences():
    text = '```json\n{"tool": "get_articles", "args": {}}\n```'
    result = _parse_tool_calls(text)
    assert result is not None
    assert result[0]["name"] == "get_articles"


def test_parse_tool_calls_embedded_in_text():
    text = 'Let me check that for you.\n{"tool": "get_commentary", "args": {}}'
    result = _parse_tool_calls(text)
    assert result is not None
    assert result[0]["name"] == "get_commentary"


def test_parse_tool_calls_plain_text():
    text = "Real Madrid is the best team in the world!"
    result = _parse_tool_calls(text)
    assert result is None


def test_parse_tool_calls_invalid_json():
    text = '{"not_a_tool": true}'
    result = _parse_tool_calls(text)
    assert result is None


# --- Agent loop ---


def test_agent_returns_plain_text():
    """Agent returns LLM response directly when no tool call detected."""
    mock_provider = MagicMock()
    mock_provider.generate.return_value = "Hala Madrid! Real Madrid is the best."
    mock_db = MagicMock()

    result = run_agent("Tell me about Real Madrid", mock_provider, mock_db)
    assert "Real Madrid" in result
    assert mock_provider.generate.call_count == 1


def test_agent_max_iterations():
    """Agent stops after MAX_ITERATIONS even if LLM keeps calling tools."""
    mock_provider = MagicMock()
    mock_provider.generate.return_value = '{"tool": "predict_match", "args": {"opponent": "Barcelona", "venue": "Home", "date": "2025-01-01"}}'
    mock_db = MagicMock()

    import app.chatbot.tools as tools_module

    original_tools = tools_module.TOOLS.copy()
    tools_module.TOOLS["predict_match"] = lambda args, db: "Win: 60%"

    run_agent("predict", mock_provider, mock_db)
    assert mock_provider.generate.call_count == 5

    tools_module.TOOLS = original_tools


def test_agent_unknown_tool():
    """Agent handles unknown tool name gracefully."""
    mock_provider = MagicMock()
    mock_provider.generate.side_effect = [
        '{"tool": "nonexistent_tool", "args": {}}',
        "Sorry, I could not process that.",
    ]
    mock_db = MagicMock()

    run_agent("do something", mock_provider, mock_db)
    assert mock_provider.generate.call_count == 2


# --- Conversation memory + streaming endpoints ---


def _mock_llm_provider(monkeypatch, response_text: str = "Hala Madrid!"):
    provider = MagicMock()
    provider.generate.return_value = response_text
    provider.generate_stream.return_value = iter(
        [
            {"type": "delta", "content": response_text},
        ]
    )
    monkeypatch.setattr("app.chatbot.router._get_provider", lambda: provider)
    return provider


def test_chat_endpoint_persists_conversation(client, db_session, monkeypatch):
    """POST /chat stores user + assistant messages and returns a conversation id."""
    _mock_llm_provider(monkeypatch)

    first = client.post("/chat", json={"message": "Who are we playing next?"})
    assert first.status_code == 200
    conversation_id = first.json()["conversation_id"]
    assert first.json()["response"] == "Hala Madrid!"

    second = client.post(
        "/chat",
        json={
            "message": "And the week after?",
            "conversation_id": conversation_id,
        },
    )
    assert second.status_code == 200
    assert second.json()["conversation_id"] == conversation_id

    history = client.get(f"/conversations/{conversation_id}")
    assert history.status_code == 200
    messages = history.json()["messages"]
    assert [m["role"] for m in messages] == ["user", "assistant", "user", "assistant"]


def test_chat_stream_endpoint_emits_sse(client, db_session, monkeypatch):
    """POST /chat/stream returns delta + done events and persists the thread."""
    _mock_llm_provider(monkeypatch, response_text="Streamed answer")

    resp = client.post("/chat/stream", json={"message": "Stream this"})
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers["content-type"]

    body = resp.text
    assert 'data: {"type": "delta", "content": "Streamed answer"}' in body
    assert 'data: {"type": "done"' in body

    # Persisted after completion
    from app.models import ChatMessage

    stored = db_session.query(ChatMessage).all()
    assert {m.role for m in stored} == {"user", "assistant"}


def test_chat_stream_reports_tool_events(client, db_session, monkeypatch):
    """Tool invocations surface as SSE events before the final answer."""
    provider = MagicMock()
    provider.generate_stream.return_value = iter(
        [
            {"type": "tool_calls", "calls": [{"name": "get_articles", "args": {}}]},
            {"type": "delta", "content": "Here's the news."},
        ]
    )
    monkeypatch.setattr("app.chatbot.router._get_provider", lambda: provider)

    resp = client.post("/chat/stream", json={"message": "Any news?"})
    assert resp.status_code == 200
    assert '"type": "tool"' in resp.text
    assert '"name": "get_articles"' in resp.text
    assert "Here's the news." in resp.text
