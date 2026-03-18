# File: pipeline/clean.py
"""
Feature engineering pipeline: raw match data → model-ready features.

Key engineering decisions (ML hat):
  - Rolling window = 5 games (closed='left' to avoid leakage)
  - Opponent stats merged on (team_code, date) to capture form of both teams
  - Category codes saved as deterministic JSON mappings for inference-time consistency
  - Date-based split at 2024-01-01 (not random) to prevent temporal leakage

Produces:
  - data/processed/cleaned_laliga_matches.csv  (all teams, all features)
  - data/processed/train.csv                   (RM-only, pre-2024)
  - data/processed/test.csv                    (RM-only, 2024+)
  - data/processed/opponent_mapping.json       (opponent name → numeric code)
  - data/processed/venue_mapping.json          (venue → numeric code)
  - data/processed/team_mapping.json           (team name → numeric code)

Usage:
    python3 -m pipeline.clean --input data/raw/ --output data/processed/
"""

import argparse
import json
import os

import pandas as pd


ROLLING_WINDOW = 5
STAT_COLS = ["gf", "ga", "sh", "sot", "dist", "fk", "pk", "pkatt"]
ROLLING_COLS = [f"{c}_rolling" for c in STAT_COLS]
OPP_ROLLING_COLS = [f"opp_{c}" for c in ROLLING_COLS]
SPLIT_DATE = "2024-01-01"

FEATURES = [
    "venue_code", "opp_code", "hour", "day_code",
    *ROLLING_COLS,
    *OPP_ROLLING_COLS,
]


def _rolling_average(group: pd.DataFrame) -> pd.DataFrame:
    """Compute rolling 5-game averages for stat columns.

    closed='left' excludes the current row, preventing target leakage.
    O(n) per group.
    """
    group = group.sort_values("date")
    rolling = group[STAT_COLS].rolling(ROLLING_WINDOW, closed="left").mean()
    for stat, roll_col in zip(STAT_COLS, ROLLING_COLS):
        group[roll_col] = rolling[stat]
    return group.dropna(subset=ROLLING_COLS)


def _build_deterministic_mapping(series: pd.Series) -> dict[str, int]:
    """Create a sorted, deterministic mapping from category values to integer codes.

    Sorting ensures the mapping is stable across runs regardless of data order.
    """
    unique_values = sorted(series.dropna().unique())
    return {str(val): idx for idx, val in enumerate(unique_values)}


def clean(input_dir: str, output_dir: str) -> None:
    """Full cleaning pipeline: load → encode → rolling averages → opponent merge → split."""
    input_file = os.path.join(input_dir, "la_liga_10_seasons.csv")
    print(f"Loading {input_file}")
    matches = pd.read_csv(input_file)
    print(f"  {len(matches)} rows, {len(matches.columns)} columns")

    # Parse date and basic features
    matches["date"] = pd.to_datetime(matches["date"])

    # Build deterministic mappings (sorted alphabetically → stable across runs)
    venue_mapping = _build_deterministic_mapping(matches["venue"])
    opponent_mapping = _build_deterministic_mapping(matches["opponent"])
    team_mapping = _build_deterministic_mapping(matches["team"])

    matches["venue_code"] = matches["venue"].map(venue_mapping)
    matches["opp_code"] = matches["opponent"].map(opponent_mapping)
    matches["team_code"] = matches["team"].map(team_mapping)

    # Time features
    matches["hour"] = matches["time"].str.replace(r":.+", "", regex=True).astype(int)
    matches["day_code"] = matches["date"].dt.dayofweek

    # Target encoding: W=2, D=1, L=0
    matches["target"] = matches["result"].map({"W": 2, "D": 1, "L": 0})

    # Compute per-team rolling averages
    print("Computing rolling averages (window=5)...")
    matches_rolling = (
        matches.groupby("team_code", group_keys=False)[
            ["date", "team_code", "opp_code", "venue_code", "hour", "day_code", "target"]
            + STAT_COLS
        ]
        .apply(_rolling_average)
        .reset_index(drop=True)
    )

    # Merge opponent's rolling stats
    print("Merging opponent rolling stats...")
    opp_stats = matches_rolling[["team_code", "date"] + ROLLING_COLS].rename(
        columns={col: f"opp_{col}" for col in ROLLING_COLS}
    )
    merged = matches_rolling.merge(
        opp_stats,
        left_on=["opp_code", "date"],
        right_on=["team_code", "date"],
        how="left",
        suffixes=("", "_opp"),
    )
    merged = merged.drop(columns=["team_code_opp"], errors="ignore")

    # Select final columns and drop NaN rows from failed opponent merges
    all_columns = ["date", "team_code"] + FEATURES + ["target"]
    cleaned = merged[[c for c in all_columns if c in merged.columns]].dropna()
    print(f"Cleaned dataset: {len(cleaned)} rows")

    # Save full cleaned dataset
    os.makedirs(output_dir, exist_ok=True)
    cleaned.to_csv(os.path.join(output_dir, "cleaned_laliga_matches.csv"), index=False)

    # Filter to Real Madrid
    rm_code = team_mapping.get("Real Madrid")
    if rm_code is None:
        raise ValueError("'Real Madrid' not found in team mapping. Check team names in raw data.")

    rm = cleaned[cleaned["team_code"] == rm_code].copy()
    print(f"Real Madrid: {len(rm)} rows")

    # Target distribution (ML diagnostic)
    target_dist = rm["target"].value_counts().to_dict()
    print(f"  Target distribution: W={target_dist.get(2, 0)}, D={target_dist.get(1, 0)}, L={target_dist.get(0, 0)}")

    # Date-based temporal split (no random shuffle → no temporal leakage)
    train = rm[rm["date"] < SPLIT_DATE][FEATURES + ["target"]]
    test = rm[rm["date"] >= SPLIT_DATE][FEATURES + ["target"]]
    print(f"  Train: {len(train)} rows (before {SPLIT_DATE})")
    print(f"  Test:  {len(test)} rows (from {SPLIT_DATE})")

    train.to_csv(os.path.join(output_dir, "train.csv"), index=False)
    test.to_csv(os.path.join(output_dir, "test.csv"), index=False)

    # Save deterministic mappings for inference
    with open(os.path.join(output_dir, "opponent_mapping.json"), "w") as f:
        json.dump(opponent_mapping, f, indent=2)
    with open(os.path.join(output_dir, "venue_mapping.json"), "w") as f:
        json.dump(venue_mapping, f, indent=2)
    with open(os.path.join(output_dir, "team_mapping.json"), "w") as f:
        json.dump(team_mapping, f, indent=2)

    print(f"\nAll outputs saved to {output_dir}")
    print(f"  Mappings: {len(opponent_mapping)} opponents, {len(venue_mapping)} venues, {len(team_mapping)} teams")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Clean and engineer features from raw La Liga data")
    parser.add_argument("--input", type=str, default="data/raw/", help="Directory with la_liga_10_seasons.csv")
    parser.add_argument("--output", type=str, default="data/processed/", help="Output directory")
    args = parser.parse_args()
    clean(args.input, args.output)
