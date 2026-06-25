from __future__ import annotations

from datetime import date

from src.data.analysis import aggregate
from src.data.live.player_stats import PlayerMatchStat
from src.data.live.team_match_stats import STAT_KEYS, TeamMatchStat


def _ts(mid, team, **ov):
    s = {k: 0.0 for k in STAT_KEYS}
    s.update(ov)
    return TeamMatchStat(match_id=mid, team=team, stats=s)


def _ps(mid, team, player, goals=0, assists=0):
    return PlayerMatchStat(match_id=mid, team=team, player=player,
                           player_id=None, goals=goals, assists=assists,
                           yellow=0, red=0)


def _meta(mid, a, b):
    from src.data.analysis.matchday import canonical
    return {mid: {"teams": (canonical(a), canonical(b)), "date": date(2026, 6, 11),
                  "group": "Group A"}}


def test_team_match_goals_sums_player_goals_per_team():
    stats = {1: [_ts(1, "Mexico"), _ts(1, "Brazil")]}
    players = {1: [_ps(1, "Mexico", "A", goals=2), _ps(1, "Brazil", "B", goals=1)]}
    g = aggregate.team_match_goals(stats, players)
    from src.data.analysis.matchday import canonical
    assert g[1][canonical("Mexico")] == 2
    assert g[1][canonical("Brazil")] == 1


def test_build_record_sums_counts_means_possession_and_derives_result():
    from src.data.analysis.matchday import canonical
    stats = {
        1: [_ts(1, "Mexico", xg=1.5, shots_on=4, possession=0.60),
            _ts(1, "Brazil", xg=0.8, shots_on=2, possession=0.40)],
        2: [_ts(2, "Mexico", xg=2.5, shots_on=6, possession=0.50),
            _ts(2, "Spain", xg=1.0, shots_on=3, possession=0.50)],
    }
    players = {
        1: [_ps(1, "Mexico", "A", goals=2, assists=1), _ps(1, "Brazil", "B", goals=0)],
        2: [_ps(2, "Mexico", "A", goals=1), _ps(2, "Spain", "C", goals=1)],
    }
    meta = {}
    meta.update(_meta(1, "Mexico", "Brazil"))
    meta.update(_meta(2, "Mexico", "Spain"))
    rec = aggregate.build_record("Mexico", canonical("Mexico"), [1, 2],
                                 stats, players, meta)
    assert rec["matches_played"] == 2
    assert rec["xg"] == 4.0            # summed
    assert rec["shots_on"] == 10.0     # summed
    assert rec["possession"] == 0.55   # mean of 0.60 and 0.50
    assert rec["goals"] == 3           # 2 + 1
    assert rec["assists"] == 1
    assert rec["goals_conceded"] == 1  # 0 (vs Brazil) + 1 (vs Spain)
    assert rec["points"] == 4          # win vs Brazil (3 pts) + draw vs Spain (1 pt)
