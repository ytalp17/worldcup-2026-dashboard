# tests/fixtures/analysis/sample.py
"""A self-contained Group A: 4 teams, 3 matchdays (full round-robin), written to
temp stores so the accessor seam and every chart can be exercised offline."""
from __future__ import annotations

from datetime import date, datetime, time

from src.data.live import player_store, team_stats_store
from src.data.live.player_stats import PlayerMatchStat
from src.data.live.team_match_stats import STAT_KEYS, TeamMatchStat
from src.data.matches import Match

SAMPLE_GROUP = "Group A"
SAMPLE_TEAMS = ["Mexico", "Canada", "USA", "Wales"]

# match_id -> (home, away, date, home_goals, away_goals)
_FIXTURES = [
    (101, "Mexico", "Canada", date(2026, 6, 11), 2, 1),
    (102, "USA", "Wales", date(2026, 6, 12), 1, 1),
    (103, "Mexico", "USA", date(2026, 6, 17), 1, 0),
    (104, "Canada", "Wales", date(2026, 6, 18), 0, 3),
    (105, "Mexico", "Wales", date(2026, 6, 23), 2, 2),
    (106, "Canada", "USA", date(2026, 6, 24), 1, 2),
]

SAMPLE_MATCHES = [
    Match(number=i + 1, home=h, away=a, group=SAMPLE_GROUP, stage="Group Stage",
          stadium="X", date=d, local_time=time(13, 0),
          kickoff_utc=datetime(d.year, d.month, d.day, 19, 0))
    for i, (_mid, h, a, d, _hg, _ag) in enumerate(_FIXTURES)
]


def _ts(mid, team, **ov):
    s = {k: 0.0 for k in STAT_KEYS}
    # give every match plausible non-zero volume so charts render
    s.update(xg=1.4, xa=1.0, big_chances=2, possession=0.5, shots_on=4,
             shots_off=5, shots_blocked=2, shots_in_box=7, corners=5,
             passes_total=450, passes_succ=380, key_passes=8,
             passes_final_third=60, long_passes=40, crosses=15, crosses_succ=5,
             dribbles=12, dribbles_succ=7, tackles=18, tackles_succ=12,
             interceptions=9, clearances=20, aerials=22, aerials_won=11,
             gk_saves=3, fouls=11, offsides=2, yellow=2, red=0)
    s.update(ov)
    return TeamMatchStat(match_id=mid, team=team, stats=s)


def write_sample(stats_path, players_path) -> None:
    for mid, h, a, d, hg, ag in _FIXTURES:
        team_stats_store.upsert(stats_path, mid, "finished",
                                [_ts(mid, h, possession=0.55),
                                 _ts(mid, a, possession=0.45)])
        rows = []
        for _ in range(hg):
            rows.append(PlayerMatchStat(mid, h, "H scorer", None, 1, 0, 0, 0))
        for _ in range(ag):
            rows.append(PlayerMatchStat(mid, a, "A scorer", None, 1, 0, 0, 0))
        # one assist per side for variety
        rows.append(PlayerMatchStat(mid, h, "H assist", None, 0, 1, 0, 0))
        player_store.upsert(players_path, mid, "finished", rows)
