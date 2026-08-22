# File: pipeline/refresh_stats.py
"""Lightweight stats refresh: scrape current season only, update team_stats.

Unlike the full `scrape.py` (7 seasons, ~47 min), this targets only the
current La Liga season (~3 min, 20 teams × 2 requests).

After scraping, recomputes 5-game rolling averages and upserts into the
PostgreSQL team_stats table. The prediction model then automatically
uses fresh rolling stats on the next /predict call.

If fbref is unreachable (403 on some networks), falls back to
football-data.co.uk via pipeline/fetch_season.py, which works anywhere.

Usage:
    python3 -m pipeline.refresh_stats
    python3 -m pipeline.refresh_stats --check-only   # exit 0 if stale, 1 if fresh
"""

import argparse
import logging
import os
import time as time_module
from datetime import datetime, timezone, timedelta

import pandas as pd
import requests
from bs4 import BeautifulSoup
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.database import Base
from app.models import TeamStats
from app.prediction.features import STAT_COLS, normalize_team_name

logger = logging.getLogger("pipeline.refresh")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

FBREF_BASE = "https://fbref.com"
STANDINGS_URL = f"{FBREF_BASE}/en/comps/12/La-Liga-Stats"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}
REQUEST_DELAY_S = 10
ROLLING_WINDOW = 5
STALENESS_HOURS = 48  # refresh if team_stats older than this


def _get(url: str) -> requests.Response:
    """GET with retry."""
    for attempt in range(3):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=30)
            resp.raise_for_status()
            return resp
        except requests.RequestException as e:
            wait = (attempt + 1) * 5
            logger.warning("Retry %d for %s (%s), waiting %ds", attempt + 1, url, e, wait)
            time_module.sleep(wait)
    raise RuntimeError(f"Failed to fetch {url}")


def is_stale() -> bool:
    """Check if team_stats are older than STALENESS_HOURS. Returns True if refresh needed."""
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    rm = session.get(TeamStats, "Real Madrid")
    session.close()
    engine.dispose()

    if rm is None:
        logger.info("team_stats empty — refresh needed")
        return True

    age = datetime.now(timezone.utc) - rm.updated_at
    stale = age > timedelta(hours=STALENESS_HOURS)
    logger.info("team_stats age: %s — %s", age, "stale" if stale else "fresh")
    return stale


def scrape_current_season() -> pd.DataFrame:
    """Scrape match + shooting data for all La Liga teams in the current season only.

    Returns DataFrame with columns matching the raw CSV format.
    O(teams × 2) requests ≈ 40 requests, ~7 min at 10s/req.
    """
    logger.info("Scraping current La Liga season from fbref...")
    resp = _get(STANDINGS_URL)
    soup = BeautifulSoup(resp.text, "html.parser")

    tables = soup.select("table.stats_table")
    if not tables:
        raise RuntimeError("No standings table found")

    links = [a.get("href") for a in tables[0].find_all("a") if "/squads/" in (a.get("href") or "")]
    team_urls = [f"{FBREF_BASE}{link}" for link in links]
    logger.info("Found %d teams", len(team_urls))

    all_matches: list[pd.DataFrame] = []

    for team_url in team_urls:
        team_name = normalize_team_name(
            team_url.split("/")[-1].replace("-Stats", "").replace("-", " ")
        )
        logger.info("  %s", team_name)

        try:
            team_resp = _get(team_url)
        except RuntimeError:
            logger.warning("  Skipping %s (fetch failed)", team_name)
            continue
        time_module.sleep(REQUEST_DELAY_S)

        try:
            matches = pd.read_html(team_resp.text, match="Scores & Fixtures")[0]
        except ValueError:
            logger.warning("  No Scores & Fixtures table")
            continue

        # Find shooting stats link
        team_soup = BeautifulSoup(team_resp.text, "html.parser")
        shooting_links = [
            a.get("href")
            for a in team_soup.find_all("a")
            if a.get("href") and "all_comps/shooting/" in a.get("href")
        ]
        if not shooting_links:
            logger.warning("  No shooting link")
            continue

        try:
            shoot_resp = _get(f"{FBREF_BASE}{shooting_links[0]}")
        except RuntimeError:
            logger.warning("  Shooting fetch failed")
            continue
        time_module.sleep(REQUEST_DELAY_S)

        try:
            shooting = pd.read_html(shoot_resp.text, match="Shooting")[0]
            shooting.columns = shooting.columns.droplevel()
        except (ValueError, KeyError):
            logger.warning("  Shooting table parse failed")
            continue

        try:
            merged = matches.merge(
                shooting[["Date", "Sh", "SoT", "Dist", "FK", "PK", "PKatt"]],
                on="Date",
            )
        except (ValueError, KeyError) as e:
            logger.warning("  Merge failed: %s", e)
            continue

        merged = merged[merged["Comp"] == "La Liga"]
        merged["Season"] = datetime.now().year
        merged["Team"] = team_name
        all_matches.append(merged)

    if not all_matches:
        raise RuntimeError("No match data scraped")

    result = pd.concat(all_matches, ignore_index=True)
    result.columns = [c.lower() for c in result.columns]
    logger.info("Scraped %d match rows", len(result))
    return result


def compute_and_upsert(matches: pd.DataFrame) -> int:
    """Compute latest 5-game rolling averages per team and upsert into team_stats.

    Returns number of teams upserted.
    """
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    now = datetime.now(timezone.utc)
    upserted = 0

    for team_name, group in matches.groupby("team"):
        group = group.sort_values("date")
        if len(group) < ROLLING_WINDOW:
            continue

        latest = group[STAT_COLS].tail(ROLLING_WINDOW).mean()
        rolling = {f"{c}_rolling": float(latest[c]) for c in STAT_COLS}

        existing = session.get(TeamStats, team_name)
        if existing:
            for col, val in rolling.items():
                setattr(existing, col, val)
            existing.updated_at = now
        else:
            session.add(TeamStats(team_name=team_name, **rolling, updated_at=now))
        upserted += 1

    session.commit()
    session.close()
    engine.dispose()
    logger.info("Upserted %d teams", upserted)
    return upserted


def refresh(force: bool = False) -> bool:
    """Full refresh flow: check staleness → scrape → update.

    Returns True if refresh was performed.
    """
    if not force and not is_stale():
        logger.info("Stats are fresh, skipping refresh")
        return False

    # Check if we have existing raw data to append to
    raw_path = "data/raw/la_liga_10_seasons.csv"
    try:
        matches = scrape_current_season()
    except RuntimeError as e:
        # fbref blocks many networks (403) — fall back to football-data.co.uk,
        # which works everywhere. Best effort: current season, then last season.
        logger.warning("fbref unreachable (%s) — falling back to football-data.co.uk", e)
        if _refresh_via_football_data(raw_path):
            logger.info("Refresh complete via football-data.co.uk")
            return True
        raise

    # Also merge with existing data if available (for rolling window continuity)
    if os.path.exists(raw_path):
        logger.info("Merging with existing data at %s", raw_path)
        existing = pd.read_csv(raw_path)
        existing["date"] = pd.to_datetime(existing["date"])
        matches["date"] = pd.to_datetime(matches["date"])
        # Remove old rows for the current season teams, keep the fresh ones
        combined = pd.concat([existing, matches], ignore_index=True)
        combined = combined.drop_duplicates(subset=["date", "team"], keep="last")
        combined = combined.sort_values(["team", "date"])
        matches = combined

    compute_and_upsert(matches)
    logger.info("Refresh complete")
    return True


def _refresh_via_football_data(raw_path: str) -> bool:
    """Fetch the current + previous season from football-data.co.uk and update stats.

    The current season alone rarely has enough matches per team to compute the
    rolling window (5 games), so the previous season is merged in for
    continuity. Both files are freely downloadable without an API key.
    """
    from pipeline.fetch_season import fetch_season, merge_into_raw

    year = datetime.now().year
    season_codes = [
        f"{year % 100:02d}{(year + 1) % 100:02d}",  # e.g. 2627
        f"{(year - 1) % 100:02d}{year % 100:02d}",  # e.g. 2526
    ]
    fetched = 0
    for code in season_codes:
        try:
            out = fetch_season(code, "data/raw/", raw_path, source="football-data")
        except Exception as e:
            logger.warning("fetch_season %s failed: %s", code, e)
            continue
        merge_into_raw(out, raw_path, base_path=raw_path)
        fetched += 1
    if not fetched:
        return False
    matches = pd.read_csv(raw_path)
    matches["date"] = pd.to_datetime(matches["date"])
    compute_and_upsert(matches)
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Refresh team_stats with current season data")
    parser.add_argument(
        "--force", action="store_true", help="Force refresh even if stats are fresh"
    )
    parser.add_argument(
        "--check-only", action="store_true", help="Only check staleness, exit 0=stale 1=fresh"
    )
    args = parser.parse_args()

    if args.check_only:
        import sys

        sys.exit(0 if is_stale() else 1)

    refresh(force=args.force)
