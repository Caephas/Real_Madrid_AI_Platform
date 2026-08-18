"""Unit tests for the data pipeline (clean, train, stats sync)."""

import pandas as pd
import pytest

from app.prediction.features import (
    MODEL_FEATURES,
    ROLLING_COLS,
    STAT_COLS,
    normalize_team_name,
)
from pipeline.clean import _rolling_average, _split_seasons, clean
from pipeline.fetch_season import TEAM_NAME_MAP, _league_priors, merge_into_raw
from pipeline.update_team_stats import _compute_latest_rolling


def _stats_frame(stat_values: list[float]) -> pd.DataFrame:
    """Single-team frame with enough columns for rolling math."""
    n = len(stat_values)
    df = pd.DataFrame(
        {
            "date": pd.date_range("2026-08-01", periods=n),
            "team_code": [0] * n,
            "opp_code": [1] * n,
            "venue_code": [1] * n,
            "hour": [20] * n,
            "day_code": [0] * n,
            "target": [2] * n,
            "season": [2026] * n,
        }
    )
    for col in STAT_COLS:
        df[col] = stat_values if col == "gf" else [1.0] * n
    return df


def test_model_features_consistent():
    """The 26-feature contract: 4 basic + 11 team + 11 opponent rolling."""
    assert len(STAT_COLS) == 11
    assert len(ROLLING_COLS) == 11
    assert len(MODEL_FEATURES) == 26
    assert MODEL_FEATURES[:4] == ["venue_code", "opp_code", "hour", "day_code"]
    assert MODEL_FEATURES[4:15] == ROLLING_COLS
    assert MODEL_FEATURES[15:] == [f"opp_{c}" for c in ROLLING_COLS]
    assert len(set(MODEL_FEATURES)) == 26  # no duplicates


def test_rolling_average_has_no_leakage():
    """closed='left' means the current match's own stats never leak in."""
    df = _stats_frame([1, 2, 3, 4, 5, 6, 7])
    result = _rolling_average(df).sort_values("date")
    gf_rolling = result["gf_rolling"]
    # Rows without 5 prior games are dropped entirely; no NaNs survive.
    assert len(result) == 2
    assert not gf_rolling.isna().any()
    assert gf_rolling.iloc[0] == pytest.approx(3.0)  # mean of games 1-5
    assert gf_rolling.iloc[1] == pytest.approx(4.0)  # mean of games 2-6


def test_split_seasons_holds_out_last_n():
    rm = pd.DataFrame({"season": [2019, 2020, 2021, 2022, 2023, 2024, 2025]})
    train, test, info = _split_seasons(rm, test_seasons=2)
    assert set(train["season"]) == {2019, 2020, 2021, 2022, 2023}
    assert set(test["season"]) == {2024, 2025}
    assert info["test_season_values"] == [2024, 2025]


def test_split_seasons_rejects_too_few_seasons():
    rm = pd.DataFrame({"season": [2024, 2025]})
    with pytest.raises(ValueError, match="test split"):
        _split_seasons(rm, test_seasons=2)


def test_compute_latest_rolling(tmp_path):
    """Rolling stats use the last 5 games and skip teams with fewer."""
    rows = []
    for team, results in {
        "Real Madrid": [1, 2, 3, 4, 5, 6],
        "Atlético Madrid": [3, 3, 3, 3, 3, 3],  # normalized + averaged
    }.items():
        for i, gf in enumerate(results):
            rows.append(
                {
                    "date": f"2026-08-{i + 1:02d}",
                    "team": team,
                    "gf": gf,
                    "ga": 1,
                    "sh": 10,
                    "sot": 4,
                    "dist": 18,
                    "fk": 0.2,
                    "pk": 0.1,
                    "pkatt": 0.1,
                    "xg": 1.5,
                    "xga": 1.0,
                    "poss": 55,
                }
            )
    path = tmp_path / "matches.csv"
    pd.DataFrame(rows).to_csv(path, index=False)

    stats = _compute_latest_rolling(str(path))
    assert set(stats["team_name"]) == {"Real Madrid", "Atletico Madrid"}
    rm = stats[stats["team_name"] == "Real Madrid"].iloc[0]
    assert rm["gf_rolling"] == pytest.approx(4.0)  # mean of last 5: 2..6
    assert rm["xg_rolling"] == pytest.approx(1.5)
    assert rm["poss_rolling"] == pytest.approx(55.0)
    atleti = stats[stats["team_name"] == "Atletico Madrid"].iloc[0]
    assert atleti["gf_rolling"] == pytest.approx(3.0)


def test_normalize_team_name_aliases():
    assert normalize_team_name("Atlético Madrid") == "Atletico Madrid"
    assert normalize_team_name("Málaga") == "Malaga"
    assert normalize_team_name("Deportivo La Coruña") == "Deportivo La Coruna"
    assert normalize_team_name("Barcelona") == "Barcelona"


def test_clean_rejects_missing_columns(tmp_path):
    """clean() fails loudly on data that lacks expected columns."""
    raw = tmp_path / "raw"
    raw.mkdir()
    pd.DataFrame({"date": [], "result": []}).to_csv(raw / "la_liga_10_seasons.csv", index=False)
    with pytest.raises(KeyError):
        clean(str(raw), str(tmp_path / "out"))


def test_team_name_map_covers_fd_co_uk_names():
    """Every football-data.co.uk La Liga name must map to a canonical name."""
    fd_names = {
        "Alaves",
        "Ath Bilbao",
        "Ath Madrid",
        "Barcelona",
        "Betis",
        "Celta",
        "Elche",
        "Espanol",
        "Getafe",
        "Girona",
        "Levante",
        "Mallorca",
        "Osasuna",
        "Oviedo",
        "Real Madrid",
        "Sevilla",
        "Sociedad",
        "Santander",
        "Dep. A Coruna",
        "Valencia",
        "Vallecano",
        "Villarreal",
    }
    mapped = {name: TEAM_NAME_MAP[name] for name in fd_names}
    assert mapped["Ath Madrid"] == "Atletico Madrid"
    assert mapped["Sociedad"] == "Real Sociedad"
    assert mapped["Betis"] == "Real Betis"
    assert mapped["Santander"] == "Racing Santander"
    assert mapped["Dep. A Coruna"] == "Deportivo La Coruna"
    assert len(set(mapped.values())) == len(fd_names)  # no collisions


def test_league_priors_from_historical_csv(tmp_path):
    path = tmp_path / "hist.csv"
    pd.DataFrame({"xg": [1.0, 2.0], "poss": [40.0, 60.0], "dist": [17.0, 19.0]}).to_csv(
        path, index=False
    )
    priors = _league_priors(str(path))
    assert priors["xg"] == pytest.approx(1.5)
    assert priors["poss"] == pytest.approx(50.0)
    assert priors["dist"] == pytest.approx(18.0)
    assert "fk" in priors  # missing columns default to 0.0


def test_merge_into_raw_dedupes(tmp_path):
    base = tmp_path / "base.csv"
    new = tmp_path / "new.csv"
    pd.DataFrame(
        {"date": ["2025-08-15"], "team": ["Real Madrid"], "result": ["W"], "gf": [3], "ga": [0]}
    ).to_csv(base, index=False)
    pd.DataFrame(
        {
            "date": ["2025-08-15", "2025-08-22"],
            "team": ["Real Madrid", "Espanyol"],
            "result": ["D", "L"],
            "gf": [1, 0],
            "ga": [1, 2],
        }
    ).to_csv(new, index=False)

    target = tmp_path / "merged.csv"
    merge_into_raw(str(new), str(target), base_path=str(base))
    merged = pd.read_csv(target)
    assert len(merged) == 2  # duplicate (date, team) replaced by the new row
    assert (merged["result"] == "D").any()
