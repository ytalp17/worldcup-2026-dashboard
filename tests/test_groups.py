from datetime import date, datetime, time

from src.data.groups import Group, GroupStanding, build_groups, group_for_team
from src.data.matches import Match


def _m(number, home, away, group, stage="Group Stage"):
    return Match(
        number=number,
        home=home,
        away=away,
        group=group,
        stage=stage,
        stadium="X Stadium",
        date=date(2026, 6, 11),
        local_time=time(13, 0),
        kickoff_utc=datetime.fromisoformat("2026-06-11T19:00:00+00:00"),
    )


def test_group_standing_defaults_are_zero():
    s = GroupStanding(team="Mexico")
    assert (s.played, s.won, s.drawn, s.lost, s.goal_diff, s.points) == (0, 0, 0, 0, 0, 0)


def test_build_groups_orders_by_first_appearance():
    matches = [
        _m(2, "Korea Republic", "Czechia", "Group A"),   # out of order on purpose
        _m(1, "Mexico", "South Africa", "Group A"),
        _m(25, "Czechia", "South Africa", "Group A"),
    ]
    groups = build_groups(matches)
    assert [s.team for s in groups["Group A"].standings] == [
        "Mexico", "South Africa", "Korea Republic", "Czechia"
    ]


def test_build_groups_counts_and_zeroes():
    matches = [
        _m(1, "A", "B", "Group A"),
        _m(2, "C", "D", "Group A"),
        _m(3, "E", "F", "Group B"),
    ]
    groups = build_groups(matches)
    assert set(groups) == {"Group A", "Group B"}
    assert len(groups["Group A"].standings) == 4
    assert all(s.points == 0 and s.played == 0 for s in groups["Group A"].standings)
    assert isinstance(groups["Group A"], Group)


def test_build_groups_ignores_knockout_rows():
    matches = [
        _m(1, "A", "B", "Group A"),
        _m(73, "Winner 1", "Winner 2", "", stage="Round of 32"),
    ]
    groups = build_groups(matches)
    assert set(groups) == {"Group A"}


def test_group_for_team_finds_and_misses():
    groups = build_groups([
        _m(1, "Mexico", "South Africa", "Group A"),
        _m(2, "Canada", "Qatar", "Group B"),
    ])
    assert group_for_team(groups, "Canada").name == "Group B"
    assert group_for_team(groups, "Nowhere") is None
