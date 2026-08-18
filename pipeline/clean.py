"""
Feature engineering pipeline: raw match data → model-ready features.

Key engineering decisions (ML hat):
  - Rolling window = 5 games (closed='left' to avoid leakage)
  - Opponent stats merged on (opp_code, date) to capture form of both teams
  - Features are imported from app.prediction.features — single source of truth
    shared with inference, so training and serving can never drift
  - Temporal split: the last N seasons (default 2) are held out as test
  - Team names normalized (accents → fbref ASCII) for stable mapping keys

Produces:
  - data/processed/cleaned_laliga_matches.csv  (all teams, all features)
  - data/processed/train.csv                   (RM-only, earlier seasons)
  - data/processed/test.csv                    (RM-only, last N seasons)
  - data/processed/*_mapping.json              (deterministic code mappings)
  - data/processed/metadata.json               (features, split, coverage)

Usage:
    python3 -m pipeline.clean --input data/raw/ --output data/processed/
"""

import argparse
import json
import os
from datetime import datetime

import pandas as pd

from app.prediction.features import MODEL_FEATURES, ROLLING_COLS, STAT_COLS, normalize_team_name


ROLLING_WINDOW = 5
DEFAULT_TEST_SEASONS = 2


def _rolling_average(group: pd.DataFrame) -> pd.DataFrame:
    """Compute rolling averages for stat columns.

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


def _split_seasons(rm: pd.DataFrame, test_seasons: int) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Temporal split on the last N season values (no random shuffle)."""
    seasons = sorted(int(s) for s in rm["season"].unique())
    if len(seasons) < test_seasons + 1:
        raise ValueError(
            f"Need at least {test_seasons + 1} seasons for a {test_seasons}-season test split; "
            f"only found {len(seasons)} ({seasons})."
        )
    test_season_values = set(seasons[-test_seasons:])
    train = rm[~rm["season"].isin(test_season_values)].copy()
    test = rm[rm["season"].isin(test_season_values)].copy()
    split_info = {
        "test_seasons": test_seasons,
        "test_season_values": sorted(test_season_values),
        "train_seasons": [s for s in seasons if s not in test_season_values],
    }
    return train, test, split_info


def _validate_cleaned(df: pd.DataFrame, required: list[str]) -> None:
    """Fail loudly on data-quality problems instead of training on garbage."""
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing expected columns after cleaning: {missing}")
    if df[required].isna().any().any():
        bad = df[required].isna().sum()
        raise ValueError(f"NaN values remain in cleaned features:\n{bad[bad > 0]}")
    if df.empty:
        raise ValueError("Cleaned dataset is empty — check the raw data and rolling window.")


def clean(input_dir: str, output_dir: str, test_seasons: int = DEFAULT_TEST_SEASONS) -> None:
    """Full cleaning pipeline: load → normalize → encode → rolling → merge → split."""
    input_file = os.path.join(input_dir, "la_liga_10_seasons.csv")
    print(f"Loading {input_file}")
    matches = pd.read_csv(input_file)
    print(f"  {len(matches)} rows, {len(matches.columns)} columns")

    # Normalize team names (accents → fbref ASCII) before building mappings so
    # "Betis" and "Real Betis" never create two codes for the same club.
    matches["team"] = matches["team"].map(normalize_team_name)
    matches["opponent"] = matches["opponent"].map(normalize_team_name)

    matches["date"] = pd.to_datetime(matches["date"])

    # Fill sparse nulls (e.g. a few missing shot-distance cells) with team median
    for col in STAT_COLS:
        if matches[col].isna().any():
            matches[col] = matches.groupby("team")[col].transform(lambda s: s.fillna(s.median()))

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
    print(f"Computing rolling averages (window={ROLLING_WINDOW}, closed left)...")
    matches_rolling = (
        matches.groupby("team_code", group_keys=False)[
            ["date", "team_code", "opp_code", "venue_code", "hour", "day_code", "target", "season"]
            + STAT_COLS
        ]
        .apply(_rolling_average)
        .reset_index(drop=True)
    )

    # Merge opponent's rolling stats (their form coming into the match)
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
    all_columns = ["date", "team_code", "season"] + MODEL_FEATURES + ["target"]
    cleaned = merged[[c for c in all_columns if c in merged.columns]].dropna()
    _validate_cleaned(cleaned, MODEL_FEATURES + ["target"])
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
    print(
        f"  Target distribution: W={target_dist.get(2, 0)}, D={target_dist.get(1, 0)}, L={target_dist.get(0, 0)}"
    )

    # Temporal split (last N seasons held out)
    train, test, split_info = _split_seasons(rm, test_seasons)
    train.to_csv(os.path.join(output_dir, "train.csv"), index=False)
    test.to_csv(os.path.join(output_dir, "test.csv"), index=False)
    print(f"  Train: {len(train)} rows ({split_info['train_seasons']})")
    print(f"  Test:  {len(test)} rows ({split_info['test_season_values']})")

    # Save deterministic mappings for inference
    for name, mapping in (
        ("opponent_mapping.json", opponent_mapping),
        ("venue_mapping.json", venue_mapping),
        ("team_mapping.json", team_mapping),
    ):
        with open(os.path.join(output_dir, name), "w") as f:
            json.dump(mapping, f, indent=2)

    # Metadata: training/feature provenance + data coverage snapshot
    metadata = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "input_file": input_file,
        "data_date_range": [
            matches["date"].min().isoformat(),
            matches["date"].max().isoformat(),
        ],
        "rolling_window": ROLLING_WINDOW,
        "features": MODEL_FEATURES,
        "stat_columns": STAT_COLS,
        "n_rows_raw": int(len(matches)),
        "n_rows_cleaned": int(len(cleaned)),
        "n_train": int(len(train)),
        "n_test": int(len(test)),
        "test_seasons": split_info["test_seasons"],
        "train_seasons": split_info["train_seasons"],
        "test_season_values": split_info["test_season_values"],
        "season_coverage": {
            str(int(s)): int(n) for s, n in matches.groupby("season").size().items()
        },
    }
    with open(os.path.join(output_dir, "metadata.json"), "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"\nAll outputs saved to {output_dir}")
    print(
        f"  Mappings: {len(opponent_mapping)} opponents, {len(venue_mapping)} venues, "
        f"{len(team_mapping)} teams"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Clean and engineer features from raw La Liga data"
    )
    parser.add_argument(
        "--input", type=str, default="data/raw/", help="Directory with la_liga_10_seasons.csv"
    )
    parser.add_argument("--output", type=str, default="data/processed/", help="Output directory")
    parser.add_argument(
        "--test-seasons",
        type=int,
        default=DEFAULT_TEST_SEASONS,
        help="Hold out the last N seasons as the test set (default 2)",
    )
    args = parser.parse_args()
    clean(args.input, args.output, test_seasons=args.test_seasons)
