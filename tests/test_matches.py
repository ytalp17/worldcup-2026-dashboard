from datetime import date, datetime, time
from pathlib import Path

import pytest

from src.data.matches import Match, MatchRepository, is_placeholder, matches_by_stadium

CSV_PATH = Path(__file__).parent.parent / "assets" / "data" / "wc2026_matches.csv"


def _load():
    return MatchRepository(CSV_PATH).load()


def test_loads_all_matches():
    assert len(_load()) == 104


def test_match_types_and_known_row():
    matches = _load()
    m1 = next(m for m in matches if m.number == 1)
    assert isinstance(m1, Match)
    assert m1.home == "Mexico"
    assert m1.away == "South Africa"
    assert m1.group == "Group A"
    assert m1.stage == "Group Stage"
    assert m1.stadium == "Mexico City Stadium"
    assert m1.date == date(2026, 6, 11)
    assert m1.local_time == time(13, 0)
    assert m1.kickoff_utc == datetime.fromisoformat("2026-06-11T19:00:00+00:00")


def test_missing_column_raises(tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text(
        "match_number,home_team,away_team,group,stage,stadium\n"
        "1,A,B,Group A,Group Stage,X\n"
    )
    with pytest.raises(ValueError):
        MatchRepository(bad).load()


def test_bad_date_raises(tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text(
        "match_number,home_team,away_team,group,stage,stadium,match_date,local_time,kickoff_utc\n"
        "1,A,B,Group A,Group Stage,X,not-a-date,13:00,2026-06-11T19:00:00+00:00\n"
    )
    with pytest.raises(ValueError):
        MatchRepository(bad).load()


def test_is_placeholder_detects_tbd_teams():
    for tbd in [
        "Winner Match 74",
        "Runner-up Match 101",
        "Group A winners",
        "Group B runners-up",
        "Group A/B/C/D/F third place",
    ]:
        assert is_placeholder(tbd) is True


def test_is_placeholder_false_for_real_teams():
    for team in ["Mexico", "South Africa", "Korea Republic", "Bosnia and Herzegovina"]:
        assert is_placeholder(team) is False


def test_matches_by_stadium_groups_and_sorts():
    grouped = matches_by_stadium(_load())
    assert "Dallas Stadium" in grouped
    dallas = grouped["Dallas Stadium"]
    assert len(dallas) == 9
    # Sorted by (date, number) ascending.
    keys = [(m.date, m.number) for m in dallas]
    assert keys == sorted(keys)
    # Every match in a bucket really belongs to that stadium.
    assert all(m.stadium == "Dallas Stadium" for m in dallas)
