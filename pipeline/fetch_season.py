"""
pipeline/fetch_season.py — pull a full La Liga season into the raw CSV format.

Source priority:
  1. API-Football (when the season exists there): real xG, possession, shots.
  2. football-data.co.uk CSV (default): complete results + goals + shots + SOT.
     Advanced stats it lacks (xG, xGA, possession, shot distance, FK goals,
     penalties) are filled with league-average priors computed from the
     historical dataset, so rolling features stay on a sensible scale.
  3. pipeline/scrape.py (fbref) remains the gold-standard full-fidelity source
     for when it's run from a network fbref allows.

Usage:
    python3 -m pipeline.fetch_season --season 2526 --output data/raw/
"""

import argparse
import io
import logging
import os
from datetime import datetime

import httpx
import pandas as pd

logger = logging.getLogger("pipeline.fetch_season")

FD_BASE = "https://www.football-data.co.uk/mmz4281"

# football-data.co.uk names → canonical names used in the raw CSV / mappings
TEAM_NAME_MAP = {
    "Alaves": "Alaves",
    "Ath Bilbao": "Athletic Club",
    "Ath Madrid": "Atletico Madrid",
    "Barcelona": "Barcelona",
    "Betis": "Real Betis",
    "Celta": "Celta Vigo",
    "Elche": "Elche",
    "Espanol": "Espanyol",
    "Getafe": "Getafe",
    "Girona": "Girona",
    "Levante": "Levante",
    "Mallorca": "Mallorca",
    "Osasuna": "Osasuna",
    "Oviedo": "Oviedo",
    "Real Madrid": "Real Madrid",
    "Santander": "Racing Santander",
    "Dep. A Coruna": "Deportivo La Coruna",
    "Sevilla": "Sevilla",
    "Sociedad": "Real Sociedad",
    "Valencia": "Valencia",
    "Vallecano": "Rayo Vallecano",
    "Villarreal": "Villarreal",
}

RAW_COLUMNS = [
    "date",
    "time",
    "comp",
    "round",
    "day",
    "venue",
    "result",
    "gf",
    "ga",
    "opponent",
    "xg",
    "xga",
    "poss",
    "attendance",
    "captain",
    "formation",
    "opp formation",
    "referee",
    "match report",
    "notes",
    "sh",
    "sot",
    "dist",
    "fk",
    "pk",
    "pkatt",
    "season",
    "team",
]

# Columns football-data.co.uk cannot provide — filled with league priors
PRIOR_COLS = ["xg", "xga", "poss", "dist", "fk", "pk", "pkatt"]


def _season_parts(season_code: str) -> tuple[int, int]:
    """'2526' → (2025, 2026); '2425' → (2024, 2025)."""
    return int(season_code[:2]) + 2000, int(season_code[2:]) + 2000


def _league_priors(historical_path: str) -> dict[str, float]:
    """League-wide per-match averages for stats missing from fd.co.uk data."""
    if not os.path.exists(historical_path):
        return {col: 0.0 for col in PRIOR_COLS}
    df = pd.read_csv(historical_path, usecols=lambda c: c in PRIOR_COLS)
    return {col: float(df[col].mean()) if col in df.columns else 0.0 for col in PRIOR_COLS}


def fetch_football_data_co_uk(season_code: str) -> pd.DataFrame:
    """Download a season from football-data.co.uk and reshape to raw format."""
    start_year, _ = _season_parts(season_code)
    url = f"{FD_BASE}/{season_code}/SP1.csv"
    logger.info("Downloading %s", url)
    resp = httpx.get(url, timeout=30, follow_redirects=True)
    resp.raise_for_status()
    raw = pd.read_csv(io.StringIO(resp.text))

    rows = []
    for _, m in raw.iterrows():
        home = TEAM_NAME_MAP.get(m["HomeTeam"], m["HomeTeam"])
        away = TEAM_NAME_MAP.get(m["AwayTeam"], m["AwayTeam"])
        match_date = datetime.strptime(m["Date"], "%d/%m/%Y").date()
        rows.append(
            {
                "date": match_date.isoformat(),
                "time": str(m.get("Time", "20:00")),
                "comp": "La Liga",
                "season": start_year,
                "team": home,
                "opponent": away,
                "venue": "Home",
                "result": {"H": "W", "D": "D", "A": "L"}[m["FTR"]],
                "gf": int(m["FTHG"]),
                "ga": int(m["FTAG"]),
                "sh": float(m["HS"]),
                "sot": float(m["HST"]),
            }
        )
        rows.append(
            {
                "date": match_date.isoformat(),
                "time": str(m.get("Time", "20:00")),
                "comp": "La Liga",
                "season": start_year,
                "team": away,
                "opponent": home,
                "venue": "Away",
                "result": {"H": "L", "D": "D", "A": "W"}[m["FTR"]],
                "gf": int(m["FTAG"]),
                "ga": int(m["FTHG"]),
                "sh": float(m["AS"]),
                "sot": float(m["AST"]),
            }
        )

    df = pd.DataFrame(rows)
    df["day"] = pd.to_datetime(df["date"]).dt.dayofweek
    # Matchday: cumulative count per team over the season
    df["round"] = df.groupby("team").cumcount() + 1
    return df


def fetch_api_football_season(season: int) -> pd.DataFrame | None:
    """Full-stats season from API-Football; None when the season isn't covered."""
    from app.config import settings

    if not settings.api_football_key:
        return None
    base = settings.api_football_base_url
    headers = {
        "x-rapidapi-host": base.split("//")[1].rstrip("/"),
        "x-rapidapi-key": settings.api_football_key,
    }
    resp = httpx.get(
        f"{base}fixtures",
        headers=headers,
        params={"league": 140, "season": season, "status": "FT"},
        timeout=20,
    )
    resp.raise_for_status()
    fixtures = resp.json().get("response", [])
    if not fixtures:
        return None
    return fixtures  # shape handled by caller in future versions


def fetch_season(
    season_code: str,
    output_dir: str,
    historical: str,
    source: str = "auto",
) -> str:
    """Fetch one season and write a raw-format CSV. Returns output path."""
    start_year, _ = _season_parts(season_code)
    priors = _league_priors(historical)

    if source in ("auto", "api-football"):
        api = fetch_api_football_season(start_year)
        if api:
            if source == "api-football":
                raise NotImplementedError(
                    f"API-Football full-stat mapping not implemented (season {start_year})."
                )
            logger.warning(
                "API-Football covers %s but full-stat mapping isn't implemented yet; "
                "using football-data.co.uk instead.",
                start_year,
            )

    df = fetch_football_data_co_uk(season_code)
    for col in PRIOR_COLS:
        df[col] = priors.get(col, 0.0)
    for col in RAW_COLUMNS:
        if col not in df.columns:
            df[col] = ""

    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, f"la_liga_{season_code}.csv")
    df[RAW_COLUMNS].to_csv(out_path, index=False)
    logger.info("Wrote %d rows to %s", len(df), out_path)
    return out_path


def merge_into_raw(season_csv: str, raw_path: str, base_path: str | None = None) -> None:
    """Append a fetched season to the canonical raw CSV, deduped by (date, team)."""
    new = pd.read_csv(season_csv)
    if os.path.exists(raw_path):
        existing = pd.read_csv(raw_path)
    elif base_path and os.path.exists(base_path):
        existing = pd.read_csv(base_path)
    elif os.path.exists("data/la_liga_10_seasons.csv"):
        existing = pd.read_csv("data/la_liga_10_seasons.csv")
    else:
        existing = pd.DataFrame(columns=new.columns)
    combined = pd.concat([existing, new], ignore_index=True)
    combined = combined.drop_duplicates(subset=["date", "team"], keep="last")
    combined = combined.sort_values(["date", "team"]).reset_index(drop=True)
    combined.to_csv(raw_path, index=False)
    logger.info("Merged: %d rows in %s", len(combined), raw_path)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Fetch a La Liga season into raw CSV format")
    parser.add_argument("--season", default="2526", help="Season code, e.g. 2526 for 2025/26")
    parser.add_argument("--output", default="data/raw/", help="Where to write the fetched CSV")
    parser.add_argument(
        "--historical",
        default="data/la_liga_10_seasons.csv",
        help="Historical CSV used for league-average priors",
    )
    parser.add_argument(
        "--source", default="auto", choices=["auto", "api-football", "football-data"]
    )
    parser.add_argument(
        "--merge", action="store_true", help="Merge into data/raw/la_liga_10_seasons.csv"
    )
    args = parser.parse_args()

    out = fetch_season(args.season, args.output, args.historical, source=args.source)
    if args.merge:
        merge_into_raw(
            out,
            os.path.join(args.output, "la_liga_10_seasons.csv"),
            base_path=args.historical,
        )
