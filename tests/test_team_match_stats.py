from __future__ import annotations

from src.data.live.team_match_stats import (
    STAT_KEYS,
    TeamMatchStat,
    parse_team_match_stats,
)

STATS = {
    "Mexico": {
        "Expected Goals": 1.8, "Expected Assists": 1.2, "Possession": 0.6,
        "Shots on target": 4, "Shots off target": 7, "Blocked shots": 5,
        "Total passes": 520, "Successful passes": 467, "Yellow cards": 1,
        "Red cards": 1, "Unknown Stat": 99,
    },
    "South Africa": {
        "Expected Goals": 0.4, "Possession": 0.4, "Shots on target": 1,
    },
}


def test_parses_one_row_per_team_with_all_keys():
    rows = parse_team_match_stats(7, STATS)
    assert {r.team for r in rows} == {"Mexico", "South Africa"}
    mex = next(r for r in rows if r.team == "Mexico")
    assert set(mex.stats) == set(STAT_KEYS)        # every key present
    assert isinstance(rows[0], TeamMatchStat)
    assert all(r.match_id == 7 for r in rows)


def test_maps_displaynames_and_defaults_missing_to_zero():
    rows = parse_team_match_stats(7, STATS)
    mex = next(r for r in rows if r.team == "Mexico").stats
    assert mex["xg"] == 1.8
    assert mex["xa"] == 1.2
    assert mex["possession"] == 0.6
    assert mex["shots_on"] == 4
    assert mex["passes_succ"] == 467
    assert mex["yellow"] == 1 and mex["red"] == 1
    rsa = next(r for r in rows if r.team == "South Africa").stats
    assert rsa["xa"] == 0.0          # missing -> 0
    assert rsa["corners"] == 0.0     # missing -> 0


def test_ignores_unknown_displaynames():
    rows = parse_team_match_stats(7, STATS)
    mex = next(r for r in rows if r.team == "Mexico").stats
    assert "Unknown Stat" not in mex
    assert 99 not in mex.values()


def test_handles_empty_input():
    assert parse_team_match_stats(7, {}) == []
    assert parse_team_match_stats(7, None) == []
