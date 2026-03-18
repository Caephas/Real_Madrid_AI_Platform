# File: pipeline/update_team_stats.py
"""
Updates the PostgreSQL `team_stats` table with latest rolling averages.

Reads the processed cleaned data, computes the most recent rolling average
for each team, and upserts into the team_stats table. This powers the
prediction module's feature lookup at inference time.

Usage:
    python3 -m pipeline.update_team_stats
    python3 -m pipeline.update_team_stats --input data/raw/la_liga_10_seasons.csv
"""

import argparse
import os
from datetime import datetime, timezone

import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Import from app to reuse config and models
from app.config import settings
from app.database import Base
from app.models import TeamStats


ROLLING_WINDOW = 5
STAT_COLS = ["gf", "ga", "sh", "sot", "dist", "fk", "pk", "pkatt"]


def _compute_latest_rolling(input_path: str) -> pd.DataFrame:
    """Compute the most recent rolling average per team from raw data."""
    matches = pd.read_csv(input_path)
    matches["date"] = pd.to_datetime(matches["date"])

    rows = []
    for team_name, group in matches.groupby("team"):
        group = group.sort_values("date")
        if len(group) < ROLLING_WINDOW:
            continue

        latest = group[STAT_COLS].tail(ROLLING_WINDOW).mean()
        rows.append({"team_name": team_name, **{f"{c}_rolling": latest[c] for c in STAT_COLS}})

    return pd.DataFrame(rows)


def update_team_stats(input_path: str) -> None:
    """Upsert latest rolling stats into PostgreSQL team_stats table."""
    print(f"Loading data from {input_path}")
    stats_df = _compute_latest_rolling(input_path)
    print(f"Computed rolling stats for {len(stats_df)} teams")

    engine = create_engine(settings.database_url, pool_pre_ping=True)
    Base.metadata.create_all(bind=engine)  # Ensure table exists
    Session = sessionmaker(bind=engine)
    session = Session()

    now = datetime.now(timezone.utc)
    upserted = 0

    for _, row in stats_df.iterrows():
        existing = session.get(TeamStats, row["team_name"])
        if existing:
            for col in STAT_COLS:
                setattr(existing, f"{col}_rolling", row[f"{col}_rolling"])
            existing.updated_at = now
        else:
            session.add(TeamStats(
                team_name=row["team_name"],
                **{f"{col}_rolling": row[f"{col}_rolling"] for col in STAT_COLS},
                updated_at=now,
            ))
        upserted += 1

    session.commit()
    session.close()
    print(f"Upserted {upserted} teams into team_stats table")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Update team_stats table with latest rolling averages")
    parser.add_argument(
        "--input",
        type=str,
        default="data/raw/la_liga_10_seasons.csv",
        help="Path to raw match data CSV",
    )
    args = parser.parse_args()

    if not os.path.exists(args.input):
        # Fall back to the data/ directory root if raw/ doesn't exist
        alt = "data/la_liga_10_seasons.csv"
        if os.path.exists(alt):
            args.input = alt
        else:
            raise FileNotFoundError(f"Neither {args.input} nor {alt} found")

    update_team_stats(args.input)
