# File: tests/test_chatbot.py
"""Unit tests for the chatbot module."""

from unittest.mock import MagicMock

from app.chatbot.agent import _parse_tool_call, run_agent


# --- Tool call parsing ---


def test_parse_tool_call_valid_json():
    text = '{"tool": "predict_match", "args": {"opponent": "Barcelona"}}'
    result = _parse_tool_call(text)
    assert result is not None
    assert result["tool"] == "predict_match"


def test_parse_tool_call_with_markdown_fences():
    text = '```json\n{"tool": "get_articles", "args": {}}\n```'
    result = _parse_tool_call(text)
    assert result is not None
    assert result["tool"] == "get_articles"


def test_parse_tool_call_embedded_in_text():
    text = 'Let me check that for you.\n{"tool": "get_commentary", "args": {}}'
    result = _parse_tool_call(text)
    assert result is not None
    assert result["tool"] == "get_commentary"


def test_parse_tool_call_plain_text():
    text = "Real Madrid is the best team in the world!"
    result = _parse_tool_call(text)
    assert result is None


def test_parse_tool_call_invalid_json():
    text = '{"not_a_tool": true}'
    result = _parse_tool_call(text)
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
    # Always return a tool call — should hit max iterations
    mock_provider.generate.return_value = '{"tool": "predict_match", "args": {"opponent": "Barcelona", "venue": "Home", "date": "2025-01-01"}}'
    mock_db = MagicMock()

    with MagicMock() as mock_tools:
        import app.chatbot.tools as tools_module
        original_tools = tools_module.TOOLS.copy()
        tools_module.TOOLS["predict_match"] = lambda args, db: "Win: 60%"

        result = run_agent("predict", mock_provider, mock_db)
        # Should have been called MAX_ITERATIONS (5) times
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

    result = run_agent("do something", mock_provider, mock_db)
    assert mock_provider.generate.call_count == 2
