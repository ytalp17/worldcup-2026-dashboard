from __future__ import annotations

from src.data.qualification import qualification_status


def _row(team, points, gd=0, gf=0):
    return {"team": team, "points": points, "goal_diff": gd, "goals_for": gf}


def _group(prefix, p1, p2, p3, p4):
    # four teams already in descending strength; values set so sort is stable
    return [_row(f"{prefix}1", p1, 9, 9), _row(f"{prefix}2", p2, 5, 5),
            _row(f"{prefix}3", p3, 1, 1), _row(f"{prefix}4", p4, -9, 0)]


def test_top_two_qualify_and_fourth_eliminated():
    standings = {"Group A": _group("A", 9, 6, 3, 0)}
    st = qualification_status(standings)["Group A"]
    assert st["A1"] == "qualified"
    assert st["A2"] == "qualified"
    assert st["A4"] == "eliminated"


def test_ranking_uses_points_then_gd_then_gf():
    # rows given out of order; ordering must be by points, then GD, then GF
    standings = {"Group A": [
        _row("low", 3, 0, 0),
        _row("topA", 6, 4, 10),
        _row("topB", 6, 4, 12),   # same pts+GD as topA, more GF -> ranks above
        _row("bottom", 0, -8, 1),
    ]}
    st = qualification_status(standings)["Group A"]
    assert st["topB"] == "qualified" and st["topA"] == "qualified"
    assert st["bottom"] == "eliminated"   # 4th
    # 'low' is 3rd here; single group -> its third qualifies (best-of fallback)
    assert st["low"] == "qualified"


def test_best_eight_third_placed_qualify_across_twelve_groups():
    # 12 groups; 3rd-placed points vary G..A descending via the prefix value
    standings = {}
    for i, letter in enumerate("ABCDEFGHIJKL"):
        third_pts = 12 - i   # A=12 (best 3rd) ... L=1 (worst 3rd)
        standings[f"Group {letter}"] = _group(letter, 30, 20, third_pts, 0)
    res = qualification_status(standings)
    thirds = {letter: res[f"Group {letter}"][f"{letter}3"]
              for letter in "ABCDEFGHIJKL"}
    # best 8 thirds (A..H) qualify; worst 4 (I..L) eliminated
    assert all(thirds[l] == "qualified" for l in "ABCDEFGH")
    assert all(thirds[l] == "eliminated" for l in "IJKL")


def test_partial_data_fewer_than_eight_thirds_all_qualify():
    # only 3 groups -> 3 third-placed teams, all within the best 8 -> qualify
    standings = {f"Group {l}": _group(l, 9, 6, 3, 0) for l in "ABC"}
    res = qualification_status(standings)
    for l in "ABC":
        assert res[f"Group {l}"][f"{l}3"] == "qualified"
        assert res[f"Group {l}"][f"{l}4"] == "eliminated"


def test_empty_standings_returns_empty():
    assert qualification_status({}) == {}
    assert qualification_status(None) == {}
