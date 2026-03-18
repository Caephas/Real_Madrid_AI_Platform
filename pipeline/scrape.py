# File: pipeline/scrape.py
"""
Scrapes La Liga match + shooting stats from fbref.com.

Produces: data/raw/la_liga_10_seasons.csv
Columns: date, time, comp, round, day, venue, result, gf, ga, opponent,
         xg, xga, poss, attendance, captain, formation, opp formation,
         referee, match report, notes, sh, sot, dist, fk, pk, pkatt, season, team

Usage:
    python3 -m pipeline.scrape --output data/raw/
"""

import argparse
import os
import time as time_module

import pandas as pd
import requests
from bs4 import BeautifulSoup

FBREF_BASE = "https://fbref.com"
STANDINGS_URL = f"{FBREF_BASE}/en/comps/12/La-Liga-Stats"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}
# Rate limit: fbref allows ~6 requests/minute. 10s between requests is safe.
REQUEST_DELAY_S = 10
MAX_RETRIES = 3


def _get(url: str) -> requests.Response:
    """GET with retry and backoff."""
    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=30)
            resp.raise_for_status()
            return resp
        except requests.RequestException as e:
            wait = (attempt + 1) * 5
            print(f"  Retry {attempt + 1}/{MAX_RETRIES} for {url} ({e}), waiting {wait}s")
            time_module.sleep(wait)
    raise RuntimeError(f"Failed to fetch {url} after {MAX_RETRIES} attempts")


def _scrape_team_season(team_url: str, year: int) -> pd.DataFrame | None:
    """Scrape match + shooting data for one team in one season."""
    team_name = team_url.split("/")[-1].replace("-Stats", "").replace("-", " ")
    print(f"  {team_name} ({year})")

    resp = _get(team_url)
    time_module.sleep(REQUEST_DELAY_S)

    # Parse Scores & Fixtures table
    try:
        matches = pd.read_html(resp.text, match="Scores & Fixtures")[0]
    except ValueError:
        print(f"    Scores & Fixtures table not found, skipping")
        return None

    # Find shooting stats link
    soup = BeautifulSoup(resp.text, "html.parser")
    shooting_links = [
        a.get("href")
        for a in soup.find_all("a")
        if a.get("href") and "all_comps/shooting/" in a.get("href")
    ]
    if not shooting_links:
        print(f"    No shooting stats link, skipping")
        return None

    shooting_resp = _get(f"{FBREF_BASE}{shooting_links[0]}")
    time_module.sleep(REQUEST_DELAY_S)

    try:
        shooting = pd.read_html(shooting_resp.text, match="Shooting")[0]
    except ValueError:
        print(f"    Shooting table not found, skipping")
        return None

    # Flatten multi-level columns from shooting table
    shooting.columns = shooting.columns.droplevel()

    try:
        merged = matches.merge(
            shooting[["Date", "Sh", "SoT", "Dist", "FK", "PK", "PKatt"]],
            on="Date",
        )
    except (ValueError, KeyError) as e:
        print(f"    Merge failed ({e}), skipping")
        return None

    # Filter to La Liga only
    merged = merged[merged["Comp"] == "La Liga"]
    merged["Season"] = year
    merged["Team"] = team_name
    return merged


def scrape(output_dir: str, start_year: int = 2025, end_year: int = 2018) -> None:
    """Scrape all La Liga teams across multiple seasons. O(seasons * teams)."""
    years = list(range(start_year, end_year, -1))
    all_matches: list[pd.DataFrame] = []
    standings_url = STANDINGS_URL

    for year in years:
        print(f"\nSeason {year}/{year - 1}")
        resp = _get(standings_url)
        soup = BeautifulSoup(resp.text, "html.parser")

        tables = soup.select("table.stats_table")
        if not tables:
            print("  No standings table found, stopping")
            break

        # Extract team URLs from standings
        links = [a.get("href") for a in tables[0].find_all("a") if "/squads/" in (a.get("href") or "")]
        team_urls = [f"{FBREF_BASE}{link}" for link in links]

        # Navigate to previous season
        prev = soup.select("a.prev")
        if prev:
            standings_url = f"{FBREF_BASE}{prev[0].get('href')}"
        else:
            print("  No previous season link, stopping after this season")

        for team_url in team_urls:
            df = _scrape_team_season(team_url, year)
            if df is not None and not df.empty:
                all_matches.append(df)

        time_module.sleep(REQUEST_DELAY_S)

    if not all_matches:
        print("\nNo data scraped.")
        return

    result = pd.concat(all_matches, ignore_index=True)
    result.columns = [c.lower() for c in result.columns]

    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, "la_liga_10_seasons.csv")
    result.to_csv(out_path, index=False)
    print(f"\nDone. {len(result)} rows saved to {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape La Liga data from fbref.com")
    parser.add_argument("--output", type=str, default="data/raw/", help="Output directory")
    parser.add_argument("--start-year", type=int, default=2025)
    parser.add_argument("--end-year", type=int, default=2018)
    args = parser.parse_args()
    scrape(args.output, args.start_year, args.end_year)
