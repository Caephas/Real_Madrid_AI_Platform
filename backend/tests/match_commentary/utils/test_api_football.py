import pytest
from backend.match_commentary.utils.api_football import fetch_live_match_events

def test_fetch_live_match_events_valid_response(mocker):
    """Test fetch_live_match_events with a valid response from the API"""
    mocker.patch(
        "backend.match_commentary.utils.api_football.requests.get",
        return_value=mocker.Mock(
            status_code=200,
            json=lambda: {
                "response": [
                    {
                        "teams": {
                            "home": {"id": 1, "name": "Real Madrid"},
                            "away": {"id": 2, "name": "Barcelona"}
                        },
                        "events": [
                            {
                                "type": "Goal",
                                "time": {"elapsed": 23},
                                "player": {"name": "Benzema"},
                                "detail": "Normal Goal"
                            }
                        ]
                    }
                ]
            },
        ),
    )

    events = fetch_live_match_events(1)
    assert events == [
        {
            "type": "Goal",
            "time": {"elapsed": 23},
            "player": {"name": "Benzema"},
            "detail": "Normal Goal"
        }
    ]
def test_fetch_live_match_events_no_response(mocker):
    """Test fetch_live_match_events with no response"""
    mocker.patch(
        "backend.match_commentary.utils.api_football.requests.get",
        return_value=mocker.Mock(
            status_code=200,
            json=lambda: {"response": []},
        ),
    )

    events = fetch_live_match_events(1)
    assert events == []