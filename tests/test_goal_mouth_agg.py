# tests/test_goal_mouth_agg.py
from src.data.live.shots import ShotRecord
from src.data.live.goal_mouth import aggregate_goal_mouth


def _r(target, outcome="Saved", time="10'", player="P", stage="group"):
    return ShotRecord(1, "England", player, time, outcome, target, stage=stage)


def test_empty_gives_valid_empty_structure():
    agg = aggregate_goal_mouth([])
    assert set(agg["zones"]) == {"high_left", "high_centre", "high_right",
                                 "low_left", "low_centre", "low_right"}
    assert all(z["count"] == 0 for z in agg["zones"].values())
    assert agg["totals"]["total"] == 0
    assert agg["off_target"]["count"] == 0


def test_counts_and_outcome_breakdown():
    recs = [_r("Low Centre", "Goal"), _r("Low Centre", "Saved"),
            _r("Low Centre", "Blocked")]
    agg = aggregate_goal_mouth(recs)
    lc = agg["zones"]["low_centre"]
    assert lc["count"] == 3
    assert lc["outcomes"] == {"Goal": 1, "Saved": 1, "Blocked": 1}


def test_margins_present_only_when_data():
    agg = aggregate_goal_mouth([_r("CloseLeft", "Missed")])
    assert "close_left" in agg["zones"]
    assert "close_high" not in agg["zones"]          # no empty margin
    assert agg["totals"]["near_miss"] == 1


def test_null_to_off_target_unknown_to_other():
    agg = aggregate_goal_mouth([_r(None, "Missed"), _r("Top Bins", "Saved")])
    assert agg["off_target"]["count"] == 1
    assert agg["other"]["count"] == 1


def test_woodwork_counts_post_outcomes():
    agg = aggregate_goal_mouth([_r("Low Left", "Post"), _r(None, "Post")])
    assert agg["totals"]["woodwork"] == 2


def test_reconciliation_invariant():
    recs = [_r("Low Centre", "Goal"), _r("CloseLeft", "Missed"),
            _r(None, "Missed"), _r("Top Bins", "Saved"), _r("High Right", "Saved")]
    t = aggregate_goal_mouth(recs)["totals"]
    assert t["on_target"] + t["near_miss"] + t["off_target"] + t["other"] == t["total"]


def test_group_only_filters_knockout():
    recs = [_r("Low Centre", stage="group"), _r("Low Centre", stage="knockout")]
    assert aggregate_goal_mouth(recs, group_only=False)["totals"]["total"] == 2
    assert aggregate_goal_mouth(recs, group_only=True)["totals"]["total"] == 1


def test_shooters_sorted_by_minute():
    recs = [_r("Low Centre", time="45+1", player="B"),
            _r("Low Centre", time="45'", player="A"),
            _r("Low Centre", time="46'", player="C")]
    names = [s["player"] for s in aggregate_goal_mouth(recs)["zones"]["low_centre"]["shooters"]]
    assert names == ["A", "B", "C"]
