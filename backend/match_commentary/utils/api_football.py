import requests
from .env import API_FOOTBALL_BASE_URL, API_FOOTBALL_KEY

headers = {
    "x-rapidapi-host": API_FOOTBALL_BASE_URL.split("//")[1],
    "x-rapidapi-key": API_FOOTBALL_KEY
}

def get_team_id(team_name):
    """
    Fetch team ID by team name.
    """
    url = f"{API_FOOTBALL_BASE_URL}teams?search={team_name}"
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()

def fetch_live_match_events(team_id):
    """
    Fetch live match events for a specific team ID.
    """
    url = f"{API_FOOTBALL_BASE_URL}fixtures?live=all"
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    data = response.json()

    # Filter matches for the specific team
    live_matches = [
        match for match in data["response"] if match["teams"]["home"]["id"] == team_id or match["teams"]["away"]["id"] == team_id
    ]

    if not live_matches:
        return []

    return live_matches[0]["events"]