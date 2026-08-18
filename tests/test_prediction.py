# File: tests/test_prediction.py
"""Unit tests for the prediction module."""

from unittest.mock import patch

import pytest

from app.prediction.mappings import (
    get_opponent_code,
    get_venue_code,
    get_known_opponents,
)
from app.prediction.features import ROLLING_COLS, build_feature_vector
from app.prediction.features import compute_insights
from app.prediction.model import load_model, get_model


# --- Mapping tests ---


@pytest.fixture(autouse=True)
def mock_mappings(tmp_path):
    """Populate mapping globals for each test."""
    import app.prediction.mappings as m

    m._opponent_mapping = {"Barcelona": 4, "Sevilla": 23}
    m._venue_mapping = {"Away": 0, "Home": 1}
    m.reset_unknown_codes()
    yield
    m._opponent_mapping = None
    m._venue_mapping = None
    m.reset_unknown_codes()


def test_get_opponent_code_valid():
    assert get_opponent_code("Barcelona") == 4


def test_get_opponent_code_unknown_gets_stable_fallback():
    """New-season opponents get a deterministic code beyond the trained range."""
    first = get_opponent_code("Málaga")
    second = get_opponent_code("Málaga")
    assert first == second
    assert first > 23  # beyond every trained code


def test_get_opponent_code_unknown_different_names_distinct():
    assert get_opponent_code("Málaga") != get_opponent_code("Racing Santander")


def test_get_venue_code_home():
    assert get_venue_code("Home") == 1


def test_get_venue_code_case_insensitive():
    assert get_venue_code("away") == 0


def test_get_venue_code_invalid():
    with pytest.raises(ValueError, match="Must be 'Home' or 'Away'"):
        get_venue_code("Neutral")


def test_get_known_opponents():
    opps = get_known_opponents()
    assert opps == ["Barcelona", "Sevilla"]


# --- Feature builder tests ---


def test_build_feature_vector(db_session):
    """Feature vector has correct shape when team_stats exist."""
    from app.models import TeamStats

    # Seed team_stats
    db_session.add(
        TeamStats(
            team_name="Real Madrid",
            gf_rolling=2.0,
            ga_rolling=0.8,
            sh_rolling=15.0,
            sot_rolling=5.0,
            dist_rolling=18.0,
            fk_rolling=0.5,
            pk_rolling=0.1,
            pkatt_rolling=0.1,
            xg_rolling=1.9,
            xga_rolling=0.9,
            poss_rolling=58.0,
        )
    )
    db_session.add(
        TeamStats(
            team_name="Barcelona",
            gf_rolling=1.8,
            ga_rolling=1.0,
            sh_rolling=14.0,
            sot_rolling=4.5,
            dist_rolling=19.0,
            fk_rolling=0.3,
            pk_rolling=0.0,
            pkatt_rolling=0.0,
            xg_rolling=1.6,
            xga_rolling=1.1,
            poss_rolling=55.0,
        )
    )
    db_session.commit()

    features = build_feature_vector("Barcelona", "Home", "2025-04-13", db_session)
    assert features.shape == (1, 26)
    assert features["venue_code"].iloc[0] == 1  # Home
    assert features["opp_code"].iloc[0] == 4  # Barcelona
    assert list(features.columns) == [
        "venue_code",
        "opp_code",
        "hour",
        "day_code",
        *ROLLING_COLS,
        *[f"opp_{c}" for c in ROLLING_COLS],
    ]


def test_build_feature_vector_unknown_team(db_session):
    """Missing team_stats for the opponent should raise ValueError."""
    # No team_stats seeded in this test — db is clean
    from app.models import TeamStats

    assert db_session.get(TeamStats, "Barcelona") is None
    with pytest.raises(ValueError, match="No rolling stats found"):
        build_feature_vector("Barcelona", "Home", "2025-04-13", db_session)


# --- Model tests ---


def test_get_model_not_loaded():
    """get_model raises if load_model hasn't been called."""
    import app.prediction.model as m

    original = m._model
    m._model = None
    with pytest.raises(RuntimeError, match="not loaded"):
        get_model()
    m._model = original


def test_compute_insights_highlights_extreme_features():
    """Z-score insights flag features far from the training distribution."""
    import app.prediction.features as f

    original = f._feature_stats
    f._feature_stats = {
        "mean": {c: 50.0 for c in ROLLING_COLS + [f"opp_{c}" for c in ROLLING_COLS]},
        "std": {c: 1.0 for c in ROLLING_COLS + [f"opp_{c}" for c in ROLLING_COLS]},
    }
    features = {c: 50.0 for c in ROLLING_COLS + [f"opp_{c}" for c in ROLLING_COLS]}
    features["gf_rolling"] = 56.0  # 6σ above
    features["opp_ga_rolling"] = 47.0  # 3σ below

    insights = compute_insights(features, "Barcelona", "Away")
    assert any("scoring form" in i and "above" in i for i in insights)
    assert any("defensive form" in i and "below" in i for i in insights)
    assert insights[0] == "Away fixture — historically tougher"
    f._feature_stats = original


def test_load_model_missing_file():
    with patch("app.prediction.model.settings") as mock_settings:
        mock_settings.model_dir = "/nonexistent"
        with pytest.raises(FileNotFoundError):
            load_model()
