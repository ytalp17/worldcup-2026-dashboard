from src.data.live.shots import ShotRecord
from src.data.live import shots_store


def test_roundtrip_upsert_and_load(tmp_path):
    p = tmp_path / "live_shots.csv"
    rows = [ShotRecord(1, "England", "K. Bowie", "15'", "Blocked", "Low Centre"),
            ShotRecord(1, "England", "M. Olise", "45+1", "Missed", None)]
    shots_store.upsert(p, 1, "finished", rows, stage="group")
    loaded = shots_store.load(p)
    assert set(loaded) == {1}
    assert len(loaded[1]) == 2
    r0 = loaded[1][0]
    assert r0.team == "England" and r0.goal_target == "Low Centre"
    assert r0.stage == "group"
    # null goal_target round-trips as None, not the string "None"
    assert any(r.goal_target is None for r in loaded[1])


def test_missing_file_is_empty():
    assert shots_store.load("/no/such/file.csv") == {}
    assert shots_store.stored_match_states("/no/such/file.csv") == {}


def test_stored_states_and_replace_by_match(tmp_path):
    p = tmp_path / "live_shots.csv"
    shots_store.upsert(p, 1, "live",
                       [ShotRecord(1, "A", "P", "5'", "Saved", "Low Left")])
    shots_store.upsert(p, 2, "finished",
                       [ShotRecord(2, "B", "Q", "9'", "Goal", "Low Right")], "knockout")
    assert shots_store.stored_match_states(p) == {1: "live", 2: "finished"}
    # re-upsert match 1 replaces only its rows, leaves match 2 intact
    shots_store.upsert(p, 1, "finished",
                       [ShotRecord(1, "A", "P", "5'", "Goal", "High Left")])
    loaded = shots_store.load(p)
    assert len(loaded[1]) == 1 and loaded[1][0].outcome == "Goal"
    assert loaded[2][0].stage == "knockout"
