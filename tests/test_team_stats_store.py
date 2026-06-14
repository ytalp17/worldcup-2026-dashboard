from __future__ import annotations

from src.data.live import team_stats_store
from src.data.live.team_match_stats import STAT_KEYS, TeamMatchStat


def _row(match_id, team, **overrides):
    stats = {k: 0.0 for k in STAT_KEYS}
    stats.update(overrides)
    return TeamMatchStat(match_id=match_id, team=team, stats=stats)


def test_load_missing_file_returns_empty(tmp_path):
    assert team_stats_store.load(tmp_path / "nope.csv") == {}
    assert team_stats_store.stored_match_states(tmp_path / "nope.csv") == {}


def test_upsert_then_load_roundtrip(tmp_path):
    path = tmp_path / "ts.csv"
    team_stats_store.upsert(path, 1, "finished",
                            [_row(1, "Mexico", xg=1.8, shots_on=4, possession=0.6)])
    loaded = team_stats_store.load(path)
    assert set(loaded) == {1}
    row = loaded[1][0]
    assert row.team == "Mexico"
    assert row.stats["xg"] == 1.8
    assert row.stats["shots_on"] == 4.0
    assert row.stats["possession"] == 0.6
    assert set(row.stats) == set(STAT_KEYS)
    assert team_stats_store.stored_match_states(path) == {1: "finished"}


def test_upsert_replaces_only_target_match(tmp_path):
    path = tmp_path / "ts.csv"
    team_stats_store.upsert(path, 1, "finished", [_row(1, "Mexico", xg=1.0)])
    team_stats_store.upsert(path, 2, "live", [_row(2, "Brazil", xg=3.0)])
    team_stats_store.upsert(path, 1, "finished", [_row(1, "Mexico", xg=5.0)])
    loaded = team_stats_store.load(path)
    assert loaded[1][0].stats["xg"] == 5.0
    assert loaded[2][0].stats["xg"] == 3.0
    assert team_stats_store.stored_match_states(path) == {1: "finished", 2: "live"}
