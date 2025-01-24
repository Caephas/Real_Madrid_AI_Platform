from fastapi.testclient import TestClient
from backend.match_commentary.api import app

# Initialize the test client
client = TestClient(app)

def test_root_endpoint():
    """Test the root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Match Commentary API is running!"}

def test_get_live_commentary_no_events(mocker):
    """Test the /commentary/{team_id} endpoint when no events are found"""
    # Mock fetch_live_match_events to return an empty list
    mocker.patch(
        "backend.match_commentary.utils.api_football.fetch_live_match_events",
        return_value=[]
    )

    response = client.get("/commentary/1")
    assert response.status_code == 200
    assert response.json() == {"message": "No live matches found for this team."}

def test_get_live_commentary_with_events(mocker):
    """Test the /commentary/{team_id} endpoint with valid events"""
    # Mock fetch_live_match_events to return a list of events
    mocker.patch(
        "backend.match_commentary.utils.api_football.fetch_live_match_events",
        return_value=[
            {"event_type": "goal", "team": "Real Madrid", "player": "Benzema", "time": "23'"},
        ]
    )

    # Mock generate_commentary to return a string
    mocker.patch(
        "backend.match_commentary.utils.commentary.generate_commentary",
        return_value="Benzema scored a goal at 23 minutes."
    )

    # Mock store_events_in_firestore to do nothing
    mocker.patch(
        "backend.shared.firestore.store_events_in_firestore",
        return_value=None
    )

    response = client.get("/commentary/1")
    assert response.status_code == 200
    assert response.json() == {
        "team_id": 1,
        "commentary": ["Benzema scored a goal at 23 minutes."],
    }