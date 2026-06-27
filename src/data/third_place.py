"""Rank the 12 group third-placed teams; the best 8 advance to the Round of 32.

World Cup 2026 has 12 groups of 4. The top two of every group qualify directly,
and the best 8 of the 12 third-placed teams join them in the Round of 32. This
module isolates the *third-place* ranking (the qualification module decides the
per-group status); both share the same tiebreaker — points -> goal difference ->
goals for (see :func:`src.data.qualification.rank_key`).

Pure and offline: it operates on the plain ``{group_name: [row dicts]}`` shape
the live snapshot exposes (and that :func:`groups_to_standings` produces from the
static groups), so it is fully unit-testable without the API.
"""
from __future__ import annotations

from collections.abc import Callable

from src.data.groups import Group
from src.data.qualification import rank_key

THIRD_PLACE_SLOTS = 8


def groups_to_standings(groups: dict[str, Group]) -> dict[str, list[dict]]:
    """Convert the static :class:`Group` map into the standings dict shape
    :func:`third_place_ranking` consumes (so a pre-tournament view has rows)."""
    return {
        name: [
            {"team": s.team, "played": s.played, "goal_diff": s.goal_diff,
             "goals_for": getattr(s, "goals_for", 0), "points": s.points}
            for s in group.standings
        ]
        for name, group in groups.items()
    }


def third_place_ranking(
    standings: dict | None,
    resolve_team: Callable[[str], str] = lambda t: t,
) -> list[dict]:
    """Ranked list of the third-placed teams, best first.

    Each entry: ``{"rank", "team", "raw", "group", "played", "goal_diff",
    "goals_for", "points", "advance"}``. ``team`` is run through ``resolve_team``
    (raw live name -> official name) while ``raw`` keeps the original for keying.
    ``advance`` is True for the best :data:`THIRD_PLACE_SLOTS` — but only once any
    matches have been played, so a pre-tournament (all-zero) table shows no
    misleading green marks.
    """
    if not standings:
        return []

    thirds: list[dict] = []
    for group, rows in standings.items():
        ranked = sorted(rows or [], key=rank_key, reverse=True)
        if len(ranked) < 3:
            continue
        thirds.append({"group": group, "row": ranked[2]})

    thirds.sort(key=lambda t: rank_key(t["row"]), reverse=True)
    any_played = any(t["row"].get("played", 0) for t in thirds)

    out: list[dict] = []
    for i, t in enumerate(thirds):
        row = t["row"]
        raw = row.get("team", "")
        out.append({
            "rank": i + 1,
            "team": resolve_team(raw),
            "raw": raw,
            "group": t["group"],
            "played": row.get("played", 0),
            "goal_diff": row.get("goal_diff", 0),
            "goals_for": row.get("goals_for", 0),
            "points": row.get("points", 0),
            "advance": any_played and i < THIRD_PLACE_SLOTS,
        })
    return out
