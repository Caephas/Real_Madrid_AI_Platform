"""Real Madrid fixture schedule for the current season.

The static schedule lives in `app/fixtures_2026_27.json` so the app works
offline. When API_FOOTBALL_KEY is configured, live kickoff dates and venues
from API-Football override the static entries (matched by matchday), and
finished fixtures can be enriched with real results.

An optional override file at `data/fixtures_2026_27.json` takes precedence
over the packaged schedule, making it easy to correct dates without a rebuild.
"""

import json
import logging
import re
import threading
import time
from datetime import date, datetime
from pathlib import Path
from typing import Any

from app.config import settings

logger = logging.getLogger("app.fixtures")

_PACKAGED_SCHEDULE = Path(__file__).parent / "fixtures_2026_27.json"
_OVERRIDE_SCHEDULE = Path("data") / "fixtures_2026_27.json"
_API_CACHE_TTL_SECONDS = 6 * 60 * 60  # 6h — free tier is rate limited

_api_cache: dict[str, tuple[float, Any]] = {}
_api_cache_lock = threading.Lock()


# ---------------------------------------------------------------------------
# Static schedule loading
# ---------------------------------------------------------------------------


def _load_static_schedule() -> list[dict]:
    """Load the packaged schedule, preferring a local override file."""
    source = _PACKAGED_SCHEDULE
    if _OVERRIDE_SCHEDULE.exists():
        source = _OVERRIDE_SCHEDULE
        logger.info("Using fixture override file: %s", _OVERRIDE_SCHEDULE)

    with open(source, encoding="utf-8") as f:
        payload = json.load(f)
    return payload.get("fixtures", [])


def _season_metadata() -> dict:
    """Season-level metadata from the packaged schedule."""
    with open(_PACKAGED_SCHEDULE, encoding="utf-8") as f:
        payload = json.load(f)
    return {
        "season": payload.get("season", "2026/27"),
        "competition": payload.get("competition", "La Liga"),
        "start_date": payload.get("start_date"),
        "end_date": payload.get("end_date"),
    }


def _normalize_date(value: str) -> date:
    """Parse YYYY-MM-DD (possibly with time) into a date."""
    return datetime.strptime(value[:10], "%Y-%m-%d").date()


# ---------------------------------------------------------------------------
# API-Football enrichment (cached)
# ---------------------------------------------------------------------------


def _cached_api_fixtures() -> dict[int, dict]:
    """Fetch the team's season fixtures from API-Football with a TTL cache.

    Returns {matchday: {"date": iso, "venue": name, "home": bool, "api_round": str}}.
    Empty dict when the key is missing or the request fails.
    """
    if not settings.api_football_key:
        return {}

    with _api_cache_lock:
        cached = _api_cache.get("fixtures")
        if cached and time.time() - cached[0] < _API_CACHE_TTL_SECONDS:
            return cached[1]

    import httpx

    url = f"{settings.api_football_base_url}fixtures"
    headers = {
        "x-rapidapi-host": settings.api_football_base_url.split("//")[1].rstrip("/"),
        "x-rapidapi-key": settings.api_football_key,
    }
    params = {"team": settings.real_madrid_team_id, "season": 2026}
    try:
        resp = httpx.get(url, headers=headers, params=params, timeout=10)
        resp.raise_for_status()
        raw = resp.json().get("response", [])
    except Exception as e:  # httpx.HTTPError, JSON errors — never block the app
        logger.warning("API-Football fixtures fetch failed: %s", e)
        return {}

    parsed: dict[int, dict] = {}
    for match in raw:
        round_str = match.get("league", {}).get("round", "")
        round_num = _extract_round(round_str)
        if round_num is None:
            continue
        parsed[round_num] = {
            "date": match.get("fixture", {}).get("date", ""),
            "venue": match.get("fixture", {}).get("venue", {}).get("name", ""),
            "home": match.get("teams", {}).get("home", {}).get("id")
            == settings.real_madrid_team_id,
            "api_round": round_str,
        }

    if parsed:
        with _api_cache_lock:
            _api_cache["fixtures"] = (time.time(), parsed)
    return parsed


def _extract_round(round_str: str) -> int | None:
    """Pull the matchday number out of strings like 'Regular Season - 7'."""
    match = re.search(r"(\d+)", round_str or "")
    return int(match.group(1)) if match else None


def _cached_api_results() -> list[dict]:
    """Fetch finished fixtures with real scores from API-Football (cached)."""
    if not settings.api_football_key:
        return []

    with _api_cache_lock:
        cached = _api_cache.get("results")
        if cached and time.time() - cached[0] < _API_CACHE_TTL_SECONDS:
            return cached[1]

    import httpx

    url = f"{settings.api_football_base_url}fixtures"
    headers = {
        "x-rapidapi-host": settings.api_football_base_url.split("//")[1].rstrip("/"),
        "x-rapidapi-key": settings.api_football_key,
    }
    params = {"team": settings.real_madrid_team_id, "season": 2026, "status": "FT"}
    try:
        resp = httpx.get(url, headers=headers, params=params, timeout=10)
        resp.raise_for_status()
        raw = resp.json().get("response", [])
    except Exception as e:
        logger.warning("API-Football results fetch failed: %s", e)
        return []

    results = []
    for match in raw:
        teams = match.get("teams", {})
        goals = match.get("goals", {})
        home, away = teams.get("home", {}), teams.get("away", {})
        rm_home = home.get("id") == settings.real_madrid_team_id
        score_home, score_away = goals.get("home") or 0, goals.get("away") or 0
        rm_score = score_home if rm_home else score_away
        opp_score = score_away if rm_home else score_home
        result = "W" if rm_score > opp_score else "D" if rm_score == opp_score else "L"
        results.append(
            {
                "date": (match.get("fixture", {}).get("date") or "")[:10],
                "opponent": away.get("name") if rm_home else home.get("name"),
                "venue": "Home" if rm_home else "Away",
                "score": f"{score_home}-{score_away}",
                "result": result,
            }
        )
    results.sort(key=lambda r: r["date"])

    if results:
        with _api_cache_lock:
            _api_cache["results"] = (time.time(), results)
    return results


# ---------------------------------------------------------------------------
# Public schedule API
# ---------------------------------------------------------------------------


def get_schedule() -> list[dict]:
    """All season fixtures, enriched with live dates/venues when available.

    Returns a list sorted by date with keys:
      matchday, date, opponent, venue, kickoff (optional), api_source (bool).
    """
    static = _load_static_schedule()
    api = _cached_api_fixtures()

    merged: dict[int, dict] = {}
    for entry in static:
        matchday = entry["matchday"]
        fixture = {
            "matchday": matchday,
            "date": entry["date"],
            "opponent": entry["opponent"],
            "venue": entry["venue"],
            "kickoff": None,
            "api_source": False,
        }
        live = api.get(matchday)
        if live:
            fixture["date"] = live["date"][:10]
            fixture["kickoff"] = live["date"]
            fixture["venue"] = "Home" if live["home"] else "Away"
            fixture["api_source"] = True
        merged[matchday] = fixture

    # Append any rounds the static schedule is missing (schedule updates)
    known = set(merged)
    for matchday, live in api.items():
        if matchday not in known:
            merged[matchday] = {
                "matchday": matchday,
                "date": live["date"][:10],
                "opponent": "",
                "venue": "Home" if live["home"] else "Away",
                "kickoff": live["date"],
                "api_source": True,
            }

    return sorted(merged.values(), key=lambda f: f["date"])


def get_season_info() -> dict:
    """Full season info: metadata, next match, fixtures with status + results."""
    fixtures = get_schedule()
    today = date.today()
    upcoming = [f for f in fixtures if _normalize_date(f["date"]) >= today]
    past = [f for f in fixtures if _normalize_date(f["date"]) < today]

    # Merge real results into past fixtures when available
    results = _cached_api_results()
    results_by_date = {r["date"]: r for r in results}
    for fixture in past:
        result = results_by_date.get(fixture["date"])
        if result:
            fixture["result"] = result["result"]
            fixture["score"] = result["score"]
        fixture["status"] = "finished"
    for fixture in upcoming:
        fixture["status"] = "upcoming"

    return {
        **_season_metadata(),
        "next_match": get_next_match(),
        "fixtures": fixtures,
    }


def get_next_match() -> dict | None:
    """Return the next upcoming fixture (date >= today)."""
    today = date.today()
    for fixture in get_schedule():
        if _normalize_date(fixture["date"]) >= today:
            return fixture
    return None


def get_remaining_fixtures() -> list[dict]:
    """Return all fixtures from today onwards, sorted by date."""
    today = date.today()
    return [fixture for fixture in get_schedule() if _normalize_date(fixture["date"]) >= today]


def get_recent_results(limit: int = 5) -> list[dict]:
    """Recent finished fixtures with scores. Best-effort: empty list offline."""
    return _cached_api_results()[-limit:]


def clear_cache() -> None:
    """Drop cached API responses (used by tests and manual refresh)."""
    with _api_cache_lock:
        _api_cache.clear()
