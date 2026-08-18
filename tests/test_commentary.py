# File: tests/test_commentary.py
"""Unit tests for the commentary module."""

from app.commentary.generator import generate_commentary, generate_match_summary


def test_goal_commentary():
    event = {
        "type": "Goal",
        "time": {"elapsed": 23},
        "player": {"name": "Vinicius Jr"},
        "detail": "Normal Goal",
    }
    result = generate_commentary(event)
    assert "GOAL" in result
    assert "Vinicius Jr" in result
    assert "23'" in result


def test_own_goal():
    event = {
        "type": "Goal",
        "time": {"elapsed": 55},
        "player": {"name": "Defender"},
        "detail": "Own Goal",
    }
    result = generate_commentary(event)
    assert "OWN GOAL" in result


def test_penalty_goal():
    event = {
        "type": "Goal",
        "time": {"elapsed": 90},
        "player": {"name": "Bellingham"},
        "detail": "Penalty",
    }
    result = generate_commentary(event)
    assert "penalty" in result.lower()


def test_yellow_card():
    event = {
        "type": "Card",
        "time": {"elapsed": 30},
        "player": {"name": "Casemiro"},
        "detail": "Yellow Card",
    }
    result = generate_commentary(event)
    assert "Yellow" in result


def test_red_card():
    event = {
        "type": "Card",
        "time": {"elapsed": 78},
        "player": {"name": "Ramos"},
        "detail": "Red Card",
    }
    result = generate_commentary(event)
    assert "Red" in result


def test_substitution():
    event = {
        "type": "subst",
        "time": {"elapsed": 60},
        "player": {"name": "Rodrygo"},
        "assist": {"name": "Modric"},
    }
    result = generate_commentary(event)
    assert "Rodrygo" in result
    assert "Modric" in result
    assert "Substitution" in result


def test_var_event():
    event = {
        "type": "Var",
        "time": {"elapsed": 45},
        "player": {"name": "Benzema"},
        "detail": "Goal cancelled",
    }
    result = generate_commentary(event)
    assert "VAR" in result


def test_unknown_event():
    event = {
        "type": "SomeNewType",
        "time": {"elapsed": 10},
        "player": {"name": "Player"},
        "detail": "",
    }
    result = generate_commentary(event)
    assert "10'" in result


def test_generate_match_summary():
    events = [
        {
            "event": {
                "type": "Goal",
                "time": {"elapsed": 12},
                "player": {"name": "Vini Jr"},
                "detail": "",
            }
        },
        {
            "event": {
                "type": "Card",
                "time": {"elapsed": 30},
                "player": {"name": "Ramos"},
                "detail": "Yellow Card",
            }
        },
    ]
    summary = generate_match_summary(events)
    assert len(summary) == 2
    assert summary[0]["type"] == "Goal"
    assert summary[1]["type"] == "Card"
    assert all("text" in s for s in summary)
