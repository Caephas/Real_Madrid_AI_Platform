# File: app/prediction/features.py
"""Feature vector construction for match prediction.

Builds the 20-feature vector that the model expects:
  [venue_code, opp_code, hour, day_code,
   gf_rolling, ga_rolling, sh_rolling, sot_rolling, dist_rolling, fk_rolling, pk_rolling, pkatt_rolling,
   opp_gf_rolling, opp_ga_rolling, opp_sh_rolling, opp_sot_rolling, opp_dist_rolling, opp_fk_rolling, opp_pk_rolling, opp_pkatt_rolling]

RM's rolling stats come from the team_stats PostgreSQL table.
Opponent's rolling stats also come from team_stats.
"""

from datetime import datetime

import pandas as pd
from sqlalchemy.orm import Session

from app.models import TeamStats
from app.prediction.mappings import get_opponent_code, get_venue_code

ROLLING_COLS = [
    "gf_rolling", "ga_rolling", "sh_rolling", "sot_rolling",
    "dist_rolling", "fk_rolling", "pk_rolling", "pkatt_rolling",
]


def _get_team_rolling(db: Session, team_name: str) -> dict[str, float]:
    """Lookup rolling stats for a team from PostgreSQL. O(1) — PK lookup."""
    stats = db.get(TeamStats, team_name)
    if stats is None:
        raise ValueError(f"No rolling stats found for '{team_name}'. Run `make pipeline` to populate team_stats.")
    return {col: getattr(stats, col) for col in ROLLING_COLS}


def build_feature_vector(
    opponent: str,
    venue: str,
    date: str,
    db: Session,
    team_name: str = "Real Madrid",
) -> pd.DataFrame:
    """Construct a single-row DataFrame with the 20 features the model expects.

    Args:
        opponent: Opponent team name (must match training data, e.g. "Barcelona")
        venue: "Home" or "Away"
        date: Match date string (YYYY-MM-DD), used for hour/day_code extraction
        db: SQLAlchemy session for team_stats lookup
        team_name: Team to predict for (default: Real Madrid)

    Returns:
        DataFrame with shape (1, 20) — ready for model.predict() / model.predict_proba()
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
