from __future__ import annotations

from src.data.analysis.matchday import canonical
from src.data.live.team_match_stats import STAT_KEYS

# Metrics aggregated by mean (per-match rate) rather than sum.
RATE_KEYS = {"possession"}


def team_match_goals(stats_by_match: dict, players_by_match: dict) -> dict:
    """{match_id: {canonical_team: goals_scored_that_match}}.

    Goals come from summing each team's players' goals (own goals are excluded
    by player_stats parsing — documented limitation). Every team that has a
    team-stats row in a match is represented (default 0) so opponents resolve."""
    out: dict[int, dict[str, int]] = {}
    for mid, rows in (stats_by_match or {}).items():
        out[mid] = {canonical(r.team): 0 for r in rows}
    for mid, prows in (players_by_match or {}).items():
        bucket = out.setdefault(mid, {})
        for p in prows:
            bucket[canonical(p.team)] = bucket.get(canonical(p.team), 0) + p.goals
    return out


def _opponent(team_canon: str, teams: tuple) -> str | None:
    others = [t for t in teams if t != team_canon]
    return others[0] if others else None


def build_record(team_official: str, team_canon: str, chrono_mids: list,
                 stats_by_match: dict, players_by_match: dict, meta: dict) -> dict:
    """One cumulative aggregate record for a team across its FINISHED matches.

    chrono_mids must already be this team's FINISHED match_ids in order.
    """
    rec = {k: 0.0 for k in STAT_KEYS}
    rec.update(team=team_official, group=None, matches_played=0,
               goals=0, goals_conceded=0, assists=0, points=0)
    poss: list[float] = []
    goals_by_match = team_match_goals(stats_by_match, players_by_match)

    for mid in chrono_mids:
        rows = stats_by_match.get(mid, [])
        mine = next((r for r in rows if canonical(r.team) == team_canon), None)
        if mine is None:
            continue
        rec["matches_played"] += 1
        for k in STAT_KEYS:
            if k in RATE_KEYS:
                poss.append(mine.stats.get(k, 0.0))
            else:
                rec[k] += mine.stats.get(k, 0.0)
        # group label from meta (first seen)
        if rec["group"] is None:
            rec["group"] = meta.get(mid, {}).get("group")
        # assists from this team's players
        for p in players_by_match.get(mid, []):
            if canonical(p.team) == team_canon:
                rec["assists"] += p.assists
        # result from per-match goals
        gm = goals_by_match.get(mid, {})
        gf = gm.get(team_canon, 0)
        opp = _opponent(team_canon, meta.get(mid, {}).get("teams", ()))
        ga = gm.get(opp, 0) if opp else 0
        rec["goals"] += gf
        rec["goals_conceded"] += ga
        rec["points"] += 3 if gf > ga else (1 if gf == ga else 0)

    rec["possession"] = round(sum(poss) / len(poss), 4) if poss else 0.0
    return rec
