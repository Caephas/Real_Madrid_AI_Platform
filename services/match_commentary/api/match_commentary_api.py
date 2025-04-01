from fastapi import FastAPI
from utils.api_football import fetch_live_match_events
from utils.commentary import generate_commentary
from dynamodb import store_events_in_dynamodb

app = FastAPI()

@app.get("/")
def root():
    return {"message": "Match Commentary API is running!"}


@app.get("/commentary/{team_id}")
def get_live_commentary(team_id: int):
    """
    Fetch live match commentary for a given team.
    """
    events = fetch_live_match_events(team_id)
    if not events:
        return {"message": "No live matches found for this team."}

    # Store events in Dynamodb
    store_events_in_dynamodb(events)

    # Generate commentary
    commentary = [generate_commentary(event) for event in events]

    return {"team_id": team_id, "commentary": commentary}