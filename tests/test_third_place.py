"""Ranking of the 12 group third-placed teams; top 8 advance to the Round of 32."""
from __future__ import annotations

from src.data.groups import Group, GroupStanding
from src.data.third_place import groups_to_standings, third_place_ranking


def _row(team, points, gd=0, gf=0, played=3):
    return {"team": team, "points": points, "goal_diff": gd,
            "goals_for": gf, "played": played}


def _group(letter, third_pts, gd=0, gf=0, played=3):
    """A 4-team group whose 3rd-placed team has the given tiebreak stats."""
    return [
        _row(f"{letter}1", 9),
        _row(f"{letter}2", 6),
        _row(f"{letter}3rd", third_pts, gd, gf, played),
        _row(f"{letter}4", 0),
    ]


def _standings(n_groups, **third_pts):
    # n_groups groups A..; each group's third gets points by index unless overridden.
    out = {}
    for i in range(n_groups):
        letter = chr(ord("A") + i)
        out[f"Group {letter}"] = _group(letter, third_pts.get(letter, n_groups - i))
    return out


def test_picks_third_placed_team_from_each_group():
    ranking = third_place_ranking(_standings(3))
    assert len(ranking) == 3
    assert {r["team"] for r in ranking} == {"A3rd", "B3rd", "C3rd"}
    assert all(r["group"].startswith("Group ") for r in ranking)


def test_ranked_by_points_then_gd_then_gf_descending():
    standings = {
        "Group A": _group("A", 3, gd=1, gf=2),
        "Group B": _group("B", 4),            # most points -> rank 1
        "Group C": _group("C", 3, gd=5, gf=9),  # ties A on points, better GD -> above A
    }
    ranking = third_place_ranking(standings)
    assert [r["team"] for r in ranking] == ["B3rd", "C3rd", "A3rd"]
    assert [r["rank"] for r in ranking] == [1, 2, 3]


def test_top_eight_of_twelve_advance():
    ranking = third_place_ranking(_standings(12))
    assert len(ranking) == 12
    advancing = [r["team"] for r in ranking if r["advance"]]
    assert len(advancing) == 8
    # The 8 highest-ranked thirds advance; ranks 9-12 do not.
    assert all(r["advance"] for r in ranking[:8])
    assert not any(r["advance"] for r in ranking[8:])


def test_no_matches_played_marks_none_advancing():
    # Pre-tournament: every team on zero, nothing played -> no green marks.
    standings = {f"Group {chr(ord('A') + i)}":
                 [_row(f"{i}{j}", 0, played=0) for j in range(4)]
                 for i in range(12)}
    ranking = third_place_ranking(standings)
    assert len(ranking) == 12
    assert not any(r["advance"] for r in ranking)


def test_skips_groups_with_fewer_than_three_teams():
    standings = {"Group A": _group("A", 5),
                 "Group B": [_row("B1", 9), _row("B2", 3)]}  # only 2 teams
    ranking = third_place_ranking(standings)
    assert [r["team"] for r in ranking] == ["A3rd"]


def test_resolve_team_applied_to_display_team_only():
    ranking = third_place_ranking({"Group A": _group("A", 5)},
                                  resolve_team=lambda t: f"Official {t}")
    assert ranking[0]["team"] == "Official A3rd"
    assert ranking[0]["raw"] == "A3rd"          # raw name preserved for status keys


def test_empty_returns_empty():
    assert third_place_ranking(None) == []
    assert third_place_ranking({}) == []


def test_groups_to_standings_shape():
    groups = {
        "Group A": Group("Group A", (
            GroupStanding("Spain", played=3, goal_diff=4, points=9),
            GroupStanding("Italy", played=3, goal_diff=1, points=6),
            GroupStanding("Wales", played=3, goal_diff=-1, points=3),
            GroupStanding("Togo", played=3, goal_diff=-4, points=0),
        )),
    }
    table = groups_to_standings(groups)
    assert set(table) == {"Group A"}
    spain = table["Group A"][0]
    assert spain["team"] == "Spain"
    assert spain["points"] == 9
    assert spain["goal_diff"] == 4
    assert "goals_for" in spain and "played" in spain
