"""Unit tests for the season fixture module."""

from unittest.mock import patch

from app.fixtures import (
    _extract_round,
    clear_cache,
    get_next_match,
    get_remaining_fixtures,
    get_schedule,
    get_season_info,
)


def test_static_schedule_has_38_fixtures():
    fixtures = get_schedule()
    assert len(fixtures) == 38
    matchdays = {f["matchday"] for f in fixtures}
    assert matchdays == set(range(1, 39))
    # Sorted by date
    dates = [f["date"] for f in fixtures]
    assert dates == sorted(dates)


def test_schedule_contains_key_fixtures():
    fixtures = {f["matchday"]: f for f in get_schedule()}
    assert fixtures[1]["opponent"] == "Real Sociedad"
    assert fixtures[1]["venue"] == "Home"
    assert fixtures[10]["opponent"] == "Barcelona"
    assert fixtures[10]["venue"] == "Away"
    assert fixtures[35]["opponent"] == "Barcelona"
    assert fixtures[35]["venue"] == "Home"
    assert fixtures[38]["opponent"] == "Deportivo La Coruña"


def test_get_next_match_returns_future_fixture():
    next_match = get_next_match()
    assert next_match is not None
    assert next_match["date"] >= "2026-08-22"


def test_get_remaining_fixtures_sorted_and_future():
    remaining = get_remaining_fixtures()
    assert remaining
    assert all(f["date"] >= "2026-08-18" for f in remaining)
    dates = [f["date"] for f in remaining]
    assert dates == sorted(dates)


def test_season_info_marks_statuses():
    info = get_season_info()
    assert info["season"] == "2026/27"
    assert info["competition"] == "La Liga"
    assert info["next_match"] is not None
    assert len(info["fixtures"]) == 38
    for fixture in info["fixtures"]:
        assert fixture["status"] in ("upcoming", "finished")


def test_api_enrichment_overrides_static_schedule():
    fake_api = {
        1: {
            "date": "2026-08-26T20:00:00+02:00",
            "venue": "Santiago Bernabéu",
            "home": True,
            "api_round": "Regular Season - 1",
        }
    }
    with patch("app.fixtures._cached_api_fixtures", return_value=fake_api):
        fixture = {f["matchday"]: f for f in get_schedule()}[1]
        assert fixture["api_source"] is True
        assert fixture["kickoff"] == "2026-08-26T20:00:00+02:00"
        assert fixture["date"] == "2026-08-26"
    clear_cache()


def test_extract_round():
    assert _extract_round("Regular Season - 7") == 7
    assert _extract_round("Matchday 12") == 12
    assert _extract_round("") is None
    assert _extract_round("Final") is None
