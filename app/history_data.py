"""Read-only access to the historical match dataset (raw CSV).

Powers the standings table, form guide, season history, and head-to-head
records. The raw CSV is the same file the training pipeline produces, so the
UI always reflects the freshest data available.
"""

import logging
import threading
import time
from pathlib import Path

import pandas as pd

logger = logging.getLogger("app.history_data")

CANDIDATE_PATHS = [
    Path("data/raw/la_liga_10_seasons.csv"),
    Path("data/la_liga_10_seasons.csv"),
]
_CACHE_TTL_SECONDS = 120

_cache: dict[str, tuple[float, pd.DataFrame]] = {}
_cache_lock = threading.Lock()


def _find_csv() -> Path | None:
    for path in CANDIDATE_PATHS:
        if path.exists():
            return path
    return None


def load_matches() -> pd.DataFrame:
    """Load the raw match dataset with a short TTL cache."""
    with _cache_lock:
        cached = _cache.get("matches")
        if cached and time.time() - cached[0] < _CACHE_TTL_SECONDS:
            return cached[1]

    path = _find_csv()
    if path is None:
        logger.warning("No raw match CSV found; season data endpoints will return empty")
        return pd.DataFrame()

    df = pd.read_csv(path)
    df["date"] = pd.to_datetime(df["date"])
    # Normalize to canonical names and standard start-year season labels
    df["team"] = df["team"].str.strip()
    df["opponent"] = df["opponent"].str.strip()
    df["season"] = (
        df["date"].dt.year.where(df["date"].dt.month >= 8, df["date"].dt.year - 1).astype(int)
    )
    df["gf"] = pd.to_numeric(df["gf"], errors="coerce").fillna(0)
    df["ga"] = pd.to_numeric(df["ga"], errors="coerce").fillna(0)

    with _cache_lock:
        _cache["matches"] = (time.time(), df)
    return df


def available_seasons() -> list[int]:
    df = load_matches()
    if df.empty:
        return []
    return sorted(int(s) for s in df["season"].unique())


def get_standings(season: int) -> list[dict]:
    """League table for a season: position, played, W/D/L, GF/GA, GD, points."""
    df = load_matches()
    if df.empty:
        return []
    season_df = df[df["season"] == season]
    if season_df.empty:
        return []

    rows = []
    for team, group in season_df.groupby("team"):
        wins = int((group["result"] == "W").sum())
        draws = int((group["result"] == "D").sum())
        losses = int((group["result"] == "L").sum())
        gf = int(group["gf"].sum())
        ga = int(group["ga"].sum())
        rows.append(
            {
                "position": 0,
                "team": team,
                "played": int(len(group)),
                "won": wins,
                "drawn": draws,
                "lost": losses,
                "gf": gf,
                "ga": ga,
                "gd": gf - ga,
                "points": wins * 3 + draws,
                "form": get_form(team, season=season, limit=5),
            }
        )

    rows.sort(key=lambda r: (-r["points"], -r["gd"], -r["gf"]))
    for i, row in enumerate(rows, start=1):
        row["position"] = i
    return rows


def get_form(team: str, season: int | None = None, limit: int = 5) -> list[str]:
    """Recent results for a team as W/D/L, most recent first."""
    df = load_matches()
    if df.empty:
        return []
    team_df = df[df["team"] == team]
    if season is not None:
        team_df = team_df[team_df["season"] == season]
    return team_df.sort_values("date")["result"].tolist()[-limit:][::-1]


def get_history(season: int) -> list[dict]:
    """Real Madrid's matches for a season, oldest first."""
    df = load_matches()
    if df.empty:
        return []
    rm = df[(df["team"] == "Real Madrid") & (df["season"] == season)]
    return [
        {
            "date": row.date.strftime("%Y-%m-%d"),
            "opponent": row.opponent,
            "venue": row.venue,
            "result": row.result,
            "gf": int(row.gf),
            "ga": int(row.ga),
        }
        for row in rm.sort_values("date").itertuples()
    ]


def get_h2h(opponent: str, limit: int = 5) -> dict:
    """Head-to-head between Real Madrid and an opponent across all seasons."""
    df = load_matches()
    empty = {
        "opponent": opponent,
        "meetings": 0,
        "rm_wins": 0,
        "draws": 0,
        "opponent_wins": 0,
        "rm_goals": 0,
        "opponent_goals": 0,
        "recent": [],
    }
    if df.empty:
        return empty

    meetings = df[(df["team"] == "Real Madrid") & (df["opponent"] == opponent)]
    if meetings.empty:
        return empty

    rm_wins = int((meetings["result"] == "W").sum())
    draws = int((meetings["result"] == "D").sum())
    recent = [
        {
            "date": row.date.strftime("%Y-%m-%d"),
            "venue": row.venue,
            "result": row.result,
            "gf": int(row.gf),
            "ga": int(row.ga),
        }
        for row in meetings.sort_values("date").tail(limit).itertuples()
    ][::-1]
    return {
        "opponent": opponent,
        "meetings": int(len(meetings)),
        "rm_wins": rm_wins,
        "draws": draws,
        "opponent_wins": int(len(meetings)) - rm_wins - draws,
        "rm_goals": int(meetings["gf"].sum()),
        "opponent_goals": int(meetings["ga"].sum()),
        "recent": recent,
    }
