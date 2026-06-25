from __future__ import annotations

from datetime import date, datetime, time

from src.data.analysis import matchday
from src.data.live.team_match_stats import STAT_KEYS, TeamMatchStat
from src.data.matches import Match


def _stat(mid, team):
    return TeamMatchStat(match_id=mid, team=team, stats={k: 0.0 for k in STAT_KEYS})


def _match(number, home, away, d):
    return Match(number=number, home=home, away=away, group="Group A",
                 stage="Group Stage", stadium="X", date=d,
                 local_time=time(13, 0),
                 kickoff_utc=datetime(2026, 6, d.day, 19, 0))


def test_finished_ids_filters_to_finished_only():
    states = {1: "finished", 2: "live", 3: "finished", 4: "scheduled"}
    assert matchday.finished_ids(states) == {1, 3}


def test_match_meta_pairs_rows_to_fixture_group_and_date():
    stats_by_match = {
        10: [_stat(10, "Mexico"), _stat(10, "South Africa")],
        11: [_stat(11, "Mexico"), _stat(11, "Czechia")],
    }
    fixtures = [
        _match(1, "Mexico", "South Africa", date(2026, 6, 11)),
        _match(2, "Mexico", "Czechia", date(2026, 6, 17)),
    ]
    meta = matchday.match_meta(stats_by_match, fixtures)
    assert meta[10]["group"] == "Group A"
    assert meta[10]["date"] == date(2026, 6, 11)
    assert set(meta[10]["teams"]) == {matchday.canonical("Mexico"),
                                      matchday.canonical("South Africa")}


def test_team_finished_matches_is_chronological():
    stats_by_match = {
        10: [_stat(10, "Mexico"), _stat(10, "South Africa")],
        11: [_stat(11, "Mexico"), _stat(11, "Czechia")],
    }
    fixtures = [
        _match(2, "Mexico", "Czechia", date(2026, 6, 17)),     # later date
        _match(1, "Mexico", "South Africa", date(2026, 6, 11)),
    ]
    meta = matchday.match_meta(stats_by_match, fixtures)
    order = matchday.team_finished_matches(matchday.canonical("Mexico"),
                                           {10, 11}, meta)
    assert order == [10, 11]  # md1 = the 11 June match, md2 = the 17 June match
