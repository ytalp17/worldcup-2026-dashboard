# tests/test_analysis_accessors.py
from __future__ import annotations

import app as appmod
from src.data.analysis import accessors
from tests.fixtures.analysis import sample


def _configure(tmp_path):
    stats = tmp_path / "team.csv"
    players = tmp_path / "players.csv"
    sample.write_sample(stats, players)
    groups = {sample.SAMPLE_GROUP: appmod.GROUPS  # placeholder; replaced below
              }
    from src.data.groups import build_groups
    groups = build_groups(sample.SAMPLE_MATCHES)
    accessors.configure(team_stats_path=stats, player_store_path=players,
                        groups=groups, matches=sample.SAMPLE_MATCHES,
                        official_resolver=lambda n: n)
    return groups


def test_group_aggregates_returns_four_team_records(tmp_path):
    _configure(tmp_path)
    recs = accessors.get_group_aggregates(sample.SAMPLE_GROUP)
    assert [r["team"] for r in recs] == sample.SAMPLE_TEAMS
    mex = next(r for r in recs if r["team"] == "Mexico")
    assert mex["matches_played"] == 3
    assert mex["goals"] == 5            # 2 + 1 + 2
    assert mex["goals_conceded"] == 3   # 1 + 0 + 2
    assert mex["points"] == 7           # win, win, draw


def test_unknown_group_returns_empty(tmp_path):
    _configure(tmp_path)
    assert accessors.get_group_aggregates("Group Z") == []


def test_matchday_history_is_cumulative_per_matchday(tmp_path):
    _configure(tmp_path)
    hist = accessors.get_matchday_history(sample.SAMPLE_GROUP, "points")
    # Mexico: win(3) -> win(6) -> draw(7)
    assert hist["Mexico"] == [3, 6, 7]
    goals = accessors.get_matchday_history(sample.SAMPLE_GROUP, "goals")
    assert goals["Mexico"] == [2, 3, 5]


def test_matchday_history_unknown_metric_raises(tmp_path):
    _configure(tmp_path)
    try:
        accessors.get_matchday_history(sample.SAMPLE_GROUP, "nonsense")
        assert False, "expected ValueError"
    except ValueError:
        pass
