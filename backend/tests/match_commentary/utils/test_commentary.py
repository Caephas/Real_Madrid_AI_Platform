from backend.match_commentary.utils.commentary import generate_commentary

def test_generate_commentary_goal_event():
    """Test commentary generation for a goal event"""
    event = {
        "type": "Goal",
        "time": {"elapsed": 23},
        "player": {"name": "Bellingham"},
    }
    commentary = generate_commentary(event)
    assert commentary == "GOAL! Bellingham scores a brilliant goal at 23'!"


def test_generate_commentary_unknown_event():
    """Test commentary generation for an unknown event type"""
    event = {
        "type": "Unknown",
        "time": {"elapsed": 45},
    }
    commentary = generate_commentary(event)
    assert commentary == "An event occurred at 45'!"

def test_generate_commentary_substitution_event():
    """Test commentary generation for a substitution event"""
    event = {
        "type": "Substitution",
        "time": {"elapsed": 65},
        "player": {"name": "Rodrygo"},
        "assist": {"name": "Vinicius Jr"}
    }
    commentary = generate_commentary(event)
    assert commentary == "Vinicius Jr is substituted by Rodrygo at 65'!"