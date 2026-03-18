# File: app/fixtures.py
"""Static La Liga 2025/26 Real Madrid fixture schedule.

La Liga fixtures are public and don't change once published.
This approach avoids API-Football rate limits and free-tier restrictions.
Auto-selects the next upcoming match based on current date.
"""

from datetime import date, datetime


# Real Madrid La Liga 2025/26 — remaining fixtures (as of March 2026)
# Format: (date, opponent, venue)
SCHEDULE: list[tuple[str, str, str]] = [
    ("2026-03-22", "Atlético Madrid", "Home"),
    ("2026-04-04", "Mallorca", "Away"),
    ("2026-04-22", "Alavés", "Home"),
    ("2026-05-03", "Espanyol", "Away"),
    ("2026-05-10", "Barcelona", "Away"),
    ("2026-05-13", "Real Sociedad", "Home"),
    ("2026-05-17", "Sevilla", "Away"),
    ("2026-05-24", "Athletic Club", "Home"),
]


def get_next_match() -> dict | None:
    """Return the next upcoming fixture based on today's date.

    Returns dict with keys: opponent, venue, date.
    Returns None if season is over (no future fixtures).
    """
    today = date.today()
    for match_date_str, opponent, venue in SCHEDULE:
        match_date = datetime.strptime(match_date_str, "%Y-%m-%d").date()
        if match_date >= today:
            return {
                "opponent": opponent,
                "venue": venue,
                "date": match_date_str,
            }
    return None


def get_remaining_fixtures() -> list[dict]:
    """Return all remaining fixtures from today onwards."""
    today = date.today()
    return [
        {"opponent": opp, "venue": venue, "date": d}
        for d, opp, venue in SCHEDULE
        if datetime.strptime(d, "%Y-%m-%d").date() >= today
    ]
