# File: app/commentary/api_football.py
"""API-Football client for live match events.

Uses httpx (async-capable, connection-pooled). Reads credentials from app config.
Endpoint docs: https://www.api-football.com/documentation-v3
"""

import logging

import httpx

from app.config import settings

logger = logging.getLogger("app.commentary")


def _headers() -> dict[str, str]:
    return {
        "x-rapidapi-host": settings.api_football_base_url.split("//")[1].rstrip("/"),
        "x-rapidapi-key": settings.api_football_key,
    }


def get_live_events(team_id: int | None = None) -> list[dict]:
    """Fetch live match events for a team (defaults to Real Madrid).

    Returns list of API-Football event dicts, or empty list if no live match.
    """
    tid = team_id or settings.real_madrid_team_id

    if not settings.api_football_key:
        logger.warning("API_FOOTBALL_KEY not set; returning empty events")
        return []

    url = f"{settings.api_football_base_url}fixtures"
    params = {"live": "all"}

    try:
        resp = httpx.get(url, headers=_headers(), params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except httpx.HTTPError as e:
        logger.error("API-Football request failed: %s", e)
        return []

    # Filter for the requested team
    matches = [
        m
        for m in data.get("response", [])
        if m["teams"]["home"]["id"] == tid or m["teams"]["away"]["id"] == tid
    ]

    if not matches:
        return []

    match = matches[0]
    events = match.get("events", [])
    fixture_info = {
        "fixture_id": match["fixture"]["id"],
        "home": match["teams"]["home"]["name"],
        "away": match["teams"]["away"]["name"],
        "score_home": match["goals"]["home"],
        "score_away": match["goals"]["away"],
        "status": match["fixture"]["status"]["long"],
        "elapsed": match["fixture"]["status"].get("elapsed"),
    }

    return [{"fixture": fixture_info, "event": e} for e in events]


def get_fixture_events(fixture_id: int) -> list[dict]:
    """Fetch events for a specific fixture (past or live)."""
    if not settings.api_football_key:
        return []

    url = f"{settings.api_football_base_url}fixtures/events"
    params = {"fixture": fixture_id}

    try:
        resp = httpx.get(url, headers=_headers(), params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except httpx.HTTPError as e:
        logger.error("API-Football events request failed: %s", e)
        return []

    return data.get("response", [])


def get_next_fixture(team_id: int | None = None) -> dict | None:
    """Fetch the next scheduled fixture for a team from API-Football.

    Returns dict with keys: opponent, venue, date, fixture_id, competition.
    Returns None if no key is set or no fixture found.
    """
    tid = team_id or settings.real_madrid_team_id

    if not settings.api_football_key:
        logger.warning("API_FOOTBALL_KEY not set; cannot fetch next fixture")
        return None

    url = f"{settings.api_football_base_url}fixtures"
    params = {"team": tid, "next": 1}

    try:
        resp = httpx.get(url, headers=_headers(), params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except httpx.HTTPError as e:
        logger.error("API-Football next fixture request failed: %s", e)
        return None

    fixtures = data.get("response", [])
    if not fixtures:
        return None

    fix = fixtures[0]
    home_team = fix["teams"]["home"]
    away_team = fix["teams"]["away"]
    is_home = home_team["id"] == tid

    return {
        "fixture_id": fix["fixture"]["id"],
        "opponent": away_team["name"] if is_home else home_team["name"],
        "venue": "Home" if is_home else "Away",
        "date": fix["fixture"]["date"][:10],  # YYYY-MM-DD
        "competition": fix.get("league", {}).get("name", "La Liga"),
    }
