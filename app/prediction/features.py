# File: app/prediction/features.py
"""Feature vector construction for match prediction.

This module is the single source of truth for model features. The offline
pipeline (pipeline/clean.py, pipeline/train.py) imports these constants so
training and inference can never drift apart.

Features (26):
  [venue_code, opp_code, hour, day_code] + 11 RM rolling stats + 11 opponent rolling stats

Rolling stats are 5-game averages (closed left — no target leakage):
  goals for, goals against, shots, shots on target, avg shot distance,
  free-kick goals, penalties scored, penalty attempts, xG, xGA, possession.
"""

from datetime import datetime
import logging

import pandas as pd
from sqlalchemy.orm import Session

from app.models import TeamStats
from app.prediction.mappings import get_opponent_code, get_venue_code

logger = logging.getLogger("app.prediction")

STAT_COLS = ["gf", "ga", "sh", "sot", "dist", "fk", "pk", "pkatt", "xg", "xga", "poss"]
ROLLING_COLS = [f"{c}_rolling" for c in STAT_COLS]
OPP_ROLLING_COLS = [f"opp_{c}" for c in ROLLING_COLS]
MODEL_FEATURES = ["venue_code", "opp_code", "hour", "day_code", *ROLLING_COLS, *OPP_ROLLING_COLS]

# fbref uses ASCII names; fixture schedule / opponent mapping may use accented names
TEAM_NAME_ALIASES: dict[str, str] = {
    "Atlético Madrid": "Atletico Madrid",
    "Alavés": "Alaves",
    "Cádiz": "Cadiz",
    "Leganés": "Leganes",
    "Betis": "Real Betis",
    "Málaga": "Malaga",
    "Deportivo La Coruña": "Deportivo La Coruna",
}


def normalize_team_name(name: str) -> str:
    """Map accented / alternate names to the fbref ASCII form stored in team_stats."""
    return TEAM_NAME_ALIASES.get(name, name)


def _get_team_rolling(db: Session, team_name: str) -> dict[str, float]:
    """Lookup rolling stats for a team from PostgreSQL.

    Falls back to the league average when a team has no row yet (e.g. a
    promoted side early in the season) so predictions never hard-fail.
    """
    normalized = normalize_team_name(team_name)
    stats = db.get(TeamStats, normalized)
    if stats is not None:
        return {col: getattr(stats, col) for col in ROLLING_COLS}
    return _league_average_rolling(db, team_name)


def _league_average_rolling(db: Session, team_name: str) -> dict[str, float]:
    """Average rolling stats across all teams in team_stats."""
    rows = db.query(TeamStats).all()
    if not rows:
        raise ValueError(
            f"No rolling stats found for '{team_name}' (team_stats is empty). "
            "Run `make refresh` or `make pipeline` to populate team_stats."
        )
    avg = {col: sum(getattr(r, col) for r in rows) / len(rows) for col in ROLLING_COLS}
    logger.info("No team_stats row for '%s' — using league average for feature vector", team_name)
    return avg


def build_feature_vector(
    opponent: str,
    venue: str,
    date: str,
    db: Session,
    team_name: str = "Real Madrid",
) -> pd.DataFrame:
    """Construct a single-row DataFrame with the model's feature vector.

    Args:
        opponent: Opponent team name (must match training data, e.g. "Barcelona")
        venue: "Home" or "Away"
        date: Match date string (YYYY-MM-DD), used for hour/day_code extraction
        db: SQLAlchemy session for team_stats lookup
        team_name: Team to predict for (default: Real Madrid)

    Returns:
        DataFrame with shape (1, len(MODEL_FEATURES)) — ready for model.predict().
    """
    opp_code = get_opponent_code(opponent)
    venue_code = get_venue_code(venue)

    match_date = datetime.strptime(date, "%Y-%m-%d")
    day_code = match_date.weekday()
    # Default to common kickoff time. Exact hour has low feature importance.
    hour = 20

    # RM rolling stats
    rm_rolling = _get_team_rolling(db, team_name)

    # Opponent rolling stats
    opp_rolling = _get_team_rolling(db, opponent)

    feature_dict = {
        "venue_code": venue_code,
        "opp_code": opp_code,
        "hour": hour,
        "day_code": day_code,
        **rm_rolling,
        **{f"opp_{col}": val for col, val in opp_rolling.items()},
    }

    return pd.DataFrame([feature_dict])
