"""Unit tests for season standings / form / history / H2H data access."""

import pandas as pd

import app.history_data as hd


def _write_csv(tmp_path) -> str:
    rows = [
        # Real Madrid vs Barcelona, 2024/25 season
        ("2024-08-15", "Real Madrid", "Barcelona", "Home", "W", 3, 1, 2024),
        ("2025-01-03", "Real Madrid", "Barcelona", "Away", "L", 0, 2, 2024),
        ("2025-08-15", "Real Madrid", "Barcelona", "Home", "D", 1, 1, 2025),
        # Another team for standings
        ("2024-08-16", "Sevilla", "Getafe", "Home", "W", 2, 0, 2024),
        ("2025-01-04", "Getafe", "Sevilla", "Away", "L", 0, 1, 2024),
    ]
    df = pd.DataFrame(
        rows, columns=["date", "team", "opponent", "venue", "result", "gf", "ga", "season"]
    )
    path = tmp_path / "matches.csv"
    df.to_csv(path, index=False)
    return str(path)


def _use_csv(tmp_path, monkeypatch):
    path = _write_csv(tmp_path)
    monkeypatch.setattr(hd, "CANDIDATE_PATHS", [__import__("pathlib").Path(path)])
    hd._cache.clear()


def test_standings_points_and_sorting(tmp_path, monkeypatch):
    _use_csv(tmp_path, monkeypatch)
    table = hd.get_standings(2024)
    rm = next(r for r in table if r["team"] == "Real Madrid")
    assert table[0]["team"] == "Sevilla"  # 3 pts, GD +1 beats RM's GD 0
    assert (rm["won"], rm["drawn"], rm["lost"], rm["points"]) == (1, 0, 1, 3)
    assert rm["form"] == ["L", "W"]  # most recent first


def test_form_most_recent_first(tmp_path, monkeypatch):
    _use_csv(tmp_path, monkeypatch)
    assert hd.get_form("Real Madrid", season=2024) == ["L", "W"]
    assert hd.get_form("Real Madrid", season=2024, limit=1) == ["L"]


def test_history_only_real_madrid(tmp_path, monkeypatch):
    _use_csv(tmp_path, monkeypatch)
    matches = hd.get_history(2024)
    assert len(matches) == 2
    assert matches[0]["opponent"] == "Barcelona"
    assert matches[1]["result"] == "L"


def test_h2h_totals(tmp_path, monkeypatch):
    _use_csv(tmp_path, monkeypatch)
    h2h = hd.get_h2h("Barcelona")
    assert h2h["meetings"] == 3
    assert h2h["rm_wins"] == 1
    assert h2h["draws"] == 1
    assert h2h["opponent_wins"] == 1
    assert h2h["rm_goals"] == 4
    assert len(h2h["recent"]) == 3
