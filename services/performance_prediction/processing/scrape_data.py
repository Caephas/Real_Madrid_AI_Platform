import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import os
import argparse

def scrape_la_liga(output_dir):
    standings_url = "https://fbref.com/en/comps/12/La-Liga-Stats"
    years = list(range(2025, 2018, -1))
    all_matches = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    }
    
    for year in years:
        print(f"Scraping season: {year}")
        data = requests.get(standings_url, headers=headers)
        soup = BeautifulSoup(data.text, 'html.parser')
        tables = soup.select('table.stats_table')
        if not tables:
            print("No standings table found on page. Check if the site structure has changed or adjust the selector.")
            continue  # or consider breaking out if it's critical
        standings_table = tables[0]

        links = [l.get("href") for l in standings_table.find_all('a')]
        links = [l for l in links if '/squads/' in l]
        team_urls = [f"https://fbref.com{l}" for l in links]

        previous_season = soup.select("a.prev")
        if previous_season:
            previous_season_url = previous_season[0].get("href")
            standings_url = f"https://fbref.com{previous_season_url}"
        else:
            print("Previous season link not found. Terminating loop.")
            break

        for team_url in team_urls:
            team_name = team_url.split("/")[-1].replace("-Stats", "").replace("-", " ")
            print(f"Scraping team: {team_name} for season {year}")
            team_data_resp = requests.get(team_url, headers=headers)
            try:
                matches = pd.read_html(team_data_resp.text, match="Scores & Fixtures")[0]
            except ValueError:
                print(f"Scores & Fixtures table not found for {team_name}, season {year}")
                continue

            team_soup = BeautifulSoup(team_data_resp.text, 'html.parser')
            links = [l.get("href") for l in team_soup.find_all('a')]
            links = [l for l in links if l and 'all_comps/shooting/' in l]
            if not links:
                print(f"Skipping shooting stats for {team_name}, season {year}")
                continue

            shooting_url = f"https://fbref.com{links[0]}"
            shooting_resp = requests.get(shooting_url, headers=headers)
            try:
                shooting = pd.read_html(shooting_resp.text, match="Shooting")[0]
            except ValueError:
                print(f"Shooting stats table not found for {team_name}, season {year}")
                continue

            shooting.columns = shooting.columns.droplevel()
            
            try:
                merged_data = matches.merge(
                    shooting[["Date", "Sh", "SoT", "Dist", "FK", "PK", "PKatt"]],
                    on="Date"
                )
            except ValueError:
                print(f"Data mismatch for {team_name}, season {year}")
                continue

            merged_data = merged_data[merged_data["Comp"] == "La Liga"]
            merged_data["Season"] = year
            merged_data["Team"] = team_name
            all_matches.append(merged_data)
            time.sleep(5)

    if all_matches:
        match_df = pd.concat(all_matches, ignore_index=True)
        match_df.columns = [c.lower() for c in match_df.columns]

        os.makedirs(output_dir, exist_ok=True)
        match_df.to_csv(os.path.join(output_dir, "la_liga_10_seasons.csv"), index=False)
        print("Scraping complete. File saved!")
    else:
        print("No data was scraped.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output_dir", type=str, required=True)
    args = parser.parse_args()
    scrape_la_liga(args.output_dir)