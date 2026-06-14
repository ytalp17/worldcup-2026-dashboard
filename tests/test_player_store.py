from __future__ import annotations

from src.data.live import player_store
from src.data.live.player_stats import PlayerMatchStat


def _row(match_id, player, pid, goals=0, rating=None, team="USA"):
    return PlayerMatchStat(match_id=match_id, team=team, player=player,
                           player_id=pid, goals=goals, assists=0, yellow=0,
                           red=0, rating=rating)


def test_load_missing_file_returns_empty(tmp_path):
    assert player_store.load(tmp_path / "nope.csv") == {}
    assert player_store.stored_match_states(tmp_path / "nope.csv") == {}


def test_upsert_then_load_roundtrip(tmp_path):
    path = tmp_path / "ps.csv"
    player_store.upsert(path, 1, "finished",
                        [_row(1, "F. Balogun", 22352589, goals=2, rating=8.4)])
    loaded = player_store.load(path)
    assert set(loaded) == {1}
    row = loaded[1][0]
    assert row.player_id == 22352589
    assert row.goals == 2
    assert row.rating == 8.4
    assert player_store.stored_match_states(path) == {1: "finished"}


def test_upsert_replaces_only_target_match(tmp_path):
    path = tmp_path / "ps.csv"
    player_store.upsert(path, 1, "finished", [_row(1, "A", 1, goals=1)])
    player_store.upsert(path, 2, "live", [_row(2, "B", 2, goals=3, team="Brazil")])
    # Re-upsert match 1 with new rows; match 2 must survive untouched.
    player_store.upsert(path, 1, "finished", [_row(1, "A", 1, goals=5)])
    loaded = player_store.load(path)
    assert loaded[1][0].goals == 5
    assert loaded[2][0].goals == 3
    assert player_store.stored_match_states(path) == {1: "finished", 2: "live"}


def test_null_id_and_rating_roundtrip_as_none(tmp_path):
    path = tmp_path / "ps.csv"
    player_store.upsert(path, 1, "finished", [_row(1, "Top Player", None)])
    row = player_store.load(path)[1][0]
    assert row.player_id is None
    assert row.rating is None
