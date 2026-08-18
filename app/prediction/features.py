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
import json
import logging
from pathlib import Path

import pandas as pd
from sqlalchemy.orm import Session

from app.config import settings
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

_feature_stats: dict | None = None

INSIGHT_LABELS = {
    "gf_rolling": "Real Madrid's scoring form",
    "ga_rolling": "Real Madrid's defensive form",
    "sh_rolling": "Real Madrid's shot volume",
    "sot_rolling": "Real Madrid's shots on target",
    "xg_rolling": "Real Madrid's xG form",
    "xga_rolling": "Real Madrid's xGA form",
    "poss_rolling": "Real Madrid's possession share",
    "opp_gf_rolling": "{opp}'s scoring form",
    "opp_ga_rolling": "{opp}'s defensive form",
    "opp_sh_rolling": "{opp}'s shot volume",
    "opp_sot_rolling": "{opp}'s shots on target",
    "opp_xg_rolling": "{opp}'s xG form",
    "opp_xga_rolling": "{opp}'s xGA form",
    "opp_poss_rolling": "{opp}'s possession share",
}


def load_feature_stats() -> None:
    """Load per-feature mean/std from training (for per-prediction insights)."""
    global _feature_stats
    path = Path(settings.model_dir) / "feature_stats.json"
    if not path.exists():
        _feature_stats = None
        return
    with open(path) as f:
        _feature_stats = json.load(f)


def compute_insights(
    features: dict[str, float],
    opponent: str,
    venue: str,
    top_k: int = 3,
    z_threshold: float = 1.2,
) -> list[str]:
    """Explain a prediction via z-scores vs the training distribution.

    Picks the rolling features that deviate most from the league-average match
    and phrases them as readable insights (no SHAP dependency needed).
    """
    if _feature_stats is None:
        return []

    candidates: list[tuple[float, str]] = []
    for col in ROLLING_COLS + OPP_ROLLING_COLS:
        mean = _feature_stats["mean"].get(col)
        std = _feature_stats["std"].get(col)
        if mean is None or not std:
            continue
        z = (features[col] - mean) / std
        if abs(z) >= z_threshold:
            label = INSIGHT_LABELS.get(col, col).format(opp=opponent)
            direction = "above" if z > 0 else "below"
            candidates.append((abs(z), f"{label} is {abs(z):.1f}σ {direction} league average"))

    candidates.sort(key=lambda item: item[0], reverse=True)
    insights = [
        (
            "Home advantage at the Bernabéu"
            if venue.lower() == "home"
            else "Away fixture — historically tougher"
        )
    ]
    insights.extend(text for _, text in candidates[:top_k])
    return insights


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
