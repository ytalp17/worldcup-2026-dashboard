from __future__ import annotations

import logging

from src.data.analysis import aggregate, matchday
from src.data.live import player_store, team_stats_store

logger = logging.getLogger(__name__)

RACE_METRICS = {
    "points": "Collected points",
    "goals": "Goals",
    "assists": "Assists",
    "cards": "Total cards",
    "conceded": "Goals conceded",
}

_CFG: dict = {
    "team_stats_path": None,
    "player_store_path": None,
    "groups": {},
    "matches": [],
    "official_resolver": lambda n: n,
}


def configure(*, team_stats_path, player_store_path, groups, matches,
              official_resolver) -> None:
    """Wire the seam to the live store paths and static data at app init."""
    _CFG.update(team_stats_path=team_stats_path,
                player_store_path=player_store_path, groups=groups,
                matches=matches, official_resolver=official_resolver)


def _load():
    stats = team_stats_store.load(_CFG["team_stats_path"])
    players = player_store.load(_CFG["player_store_path"])
    states = team_stats_store.stored_match_states(_CFG["team_stats_path"])
    meta = matchday.match_meta(stats, _CFG["matches"])
    finished = matchday.finished_ids(states)
    return stats, players, meta, finished


def _group_teams(group_id):
    group = _CFG["groups"].get(group_id)
    return [s.team for s in group.standings] if group else []


def get_group_aggregates(group_id: str) -> list[dict]:
    """Cumulative aggregate record per team in the group (official order)."""
    teams = _group_teams(group_id)
    if not teams:
        return []
    stats, players, meta, finished = _load()
    out = []
    for official in teams:
        canon = matchday.canonical(official)
        chrono = matchday.team_finished_matches(canon, finished, meta)
        rec = aggregate.build_record(official, canon, chrono, stats, players, meta)
        rec["group"] = group_id
        out.append(rec)
    return out


def _metric_after(metric, canon, mid, stats, players, goals_by_match, meta):
    """The team's contribution to `metric` from a single match."""
    if metric == "cards":
        rows = stats.get(mid, [])
        mine = next((r for r in rows if matchday.canonical(r.team) == canon), None)
        return int((mine.stats.get("yellow", 0) + mine.stats.get("red", 0))) if mine else 0
    gm = goals_by_match.get(mid, {})
    gf = gm.get(canon, 0)
    if metric == "goals":
        return gf
    if metric == "assists":
        return sum(p.assists for p in players.get(mid, [])
                   if matchday.canonical(p.team) == canon)
    opp = aggregate.opponent(canon, meta.get(mid, {}).get("teams", ()))
    ga = gm.get(opp, 0) if opp else 0
    if metric == "conceded":
        return ga
    if metric == "points":
        return 3 if gf > ga else (1 if gf == ga else 0)
    raise ValueError(f"unknown race metric: {metric}")


def get_matchday_history(group_id: str, metric: str) -> dict[str, list]:
    """Per-team cumulative series of `metric` after md1, md2, ... (chronological)."""
    if metric not in RACE_METRICS:
        raise ValueError(f"unknown race metric: {metric}")
    teams = _group_teams(group_id)
    if not teams:
        return {}
    stats, players, meta, finished = _load()
    goals_by_match = aggregate.team_match_goals(stats, players)
    out: dict[str, list] = {}
    for official in teams:
        canon = matchday.canonical(official)
        chrono = matchday.team_finished_matches(canon, finished, meta)
        series, running = [], 0
        for mid in chrono:
            running += _metric_after(metric, canon, mid, stats, players,
                                     goals_by_match, meta)
            series.append(running)
        out[official] = series
    return out
