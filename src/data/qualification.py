"""Derive group-stage qualification/elimination status from current standings.

The live standings feed carries no qualified/eliminated flag (only stats), so we
derive it from the World Cup 2026 format: 12 groups of 4, 32 teams advance —
the top 2 of every group plus the best 8 of the 12 third-placed teams; every
4th-placed team is eliminated.

Tie-breaking uses points -> goal difference -> goals for. FIFA's later
tie-breakers (head-to-head, fair play, drawing of lots) are not derivable from
standings alone, so this is a close approximation of the official ranking.

Pure and offline: operates on the plain standings dict the snapshot exposes
({group_name: [row dicts]}), so it is fully unit-testable without the API.
"""
from __future__ import annotations

QUALIFIED = "qualified"
ELIMINATED = "eliminated"
_THIRD_PLACE_SLOTS = 8


def rank_key(row: dict) -> tuple:
    """Descending sort key: points, then goal difference, then goals for."""
    return (row.get("points", 0), row.get("goal_diff", 0), row.get("goals_for", 0))


# Backwards-compatible private alias (historical callers).
_rank_key = rank_key


def qualification_status(standings: dict | None) -> dict[str, dict[str, str]]:
    """Map ``{group_name: {team: "qualified"|"eliminated"|""}}``.

    1st/2nd in each group qualify; 4th (last) is eliminated; the 8 best
    third-placed teams across all groups qualify, the rest are eliminated. With
    fewer than 8 third-placed teams present (partial data), all of them qualify.
    """
    if not standings:
        return {}

    result: dict[str, dict[str, str]] = {}
    thirds: list[tuple[tuple, str, str]] = []  # (rank_key, group, team)

    for group, rows in standings.items():
        ranked = sorted(rows or [], key=_rank_key, reverse=True)
        result[group] = {}
        last = len(ranked) - 1
        for i, row in enumerate(ranked):
            team = row.get("team", "")
            if i <= 1:
                result[group][team] = QUALIFIED
            elif i == 2:
                result[group][team] = ""  # decided by the best-thirds pass below
                thirds.append((_rank_key(row), group, team))
            elif i == last:
                result[group][team] = ELIMINATED
            else:
                result[group][team] = ELIMINATED

    thirds.sort(key=lambda t: t[0], reverse=True)
    for idx, (_key, group, team) in enumerate(thirds):
        result[group][team] = QUALIFIED if idx < _THIRD_PLACE_SLOTS else ELIMINATED

    return result
