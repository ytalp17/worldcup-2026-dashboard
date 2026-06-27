"""Position-aware placement of a starting XI onto formation slots.

The estimated-XI data (``estimated_starting_eleven.json``) lists players in an
arbitrary order that does not reliably split into a formation's lines, so a
blind ``zip(slots, xi)`` mis-assigns players (e.g. a central midfielder landing
on the wing). This module instead places each player on the slot that best
matches their *real* position (from ``squads.csv``), via optimal assignment.

Pure and dependency-light: callers pass slot coordinates as ``(x, y)`` tuples,
so neither mplsoccer nor the running Dash app needs this module — only the
build-time pitch generator does.
"""
from __future__ import annotations

from scipy.optimize import linear_sum_assignment

# Each raw squads.csv position -> a natural spot on an opta pitch, oriented to
# match mplsoccer's get_formation(): x is depth (12 = own goal/GK, 88 =
# striker); y is width (12 = right touchline, 88 = left touchline).
NATURAL_POSITIONS: dict[str, tuple[float, float]] = {
    "Goalkeeper": (12, 50),
    "Right-Back": (27, 14),
    "Centre-Back": (27, 50),
    "Left-Back": (27, 86),
    "Defensive Midfield": (44, 50),
    "Right Midfield": (58, 14),
    "Central Midfield": (58, 50),
    "Left Midfield": (58, 86),
    "Attacking Midfield": (72, 50),
    "Right Winger": (76, 12),
    "Left Winger": (76, 88),
    "Second Striker": (84, 50),
    "Centre-Forward": (88, 50),
}

# Neutral centre spot for unknown/missing positions: lets optimal assignment
# drop the player into whatever slot is left rather than skewing the layout.
_FALLBACK = (58, 50)


def natural_xy(position: str) -> tuple[float, float]:
    """Natural pitch spot for a raw squads.csv position string."""
    return NATURAL_POSITIONS.get((position or "").strip(), _FALLBACK)


def _solve(slots, players_xy):
    """Return slot index per player minimising total squared distance.

    ``players_xy[i]`` is the natural spot of player ``i``; the return value
    ``col[i]`` is the slot index that player ``i`` is assigned to.
    """
    cost = [
        [(px - sx) ** 2 + (py - sy) ** 2 for (sx, sy) in slots]
        for (px, py) in players_xy
    ]
    rows, cols = linear_sum_assignment(cost)
    # rows is sorted 0..n-1 for a square matrix, but don't assume it.
    slot_for_player = {int(r): int(c) for r, c in zip(rows, cols)}
    return slot_for_player


def assign_xi_to_slots(slots, xi, positions):
    """Reorder ``xi`` to align with ``slots`` by real position.

    Args:
        slots: list of ``(x, y)`` slot coordinates in mplsoccer get_formation()
            order; ``slots[0]`` is the goalkeeper slot.
        xi: list of ``(surname, shirt_number)`` for the 11 starters.
        positions: ``{shirt_number: raw_position}`` for the team.

    Returns:
        A list the same length as ``slots`` where item ``i`` is the
        ``(surname, number)`` placed on ``slots[i]`` — a bijection (every
        player placed once, every slot filled once).
    """
    if len(slots) != len(xi):
        raise ValueError(f"{len(xi)} players but {len(slots)} slots")

    result: list = [None] * len(slots)

    # Pin the goalkeeper to slot 0 when exactly one starter is a keeper; this
    # keeps the keeper in goal even on odd data and shrinks the optimisation.
    gk_idxs = [
        i for i, (_, num) in enumerate(xi)
        if (positions.get(num, "") or "").strip() == "Goalkeeper"
    ]
    pinned: dict[int, int] = {}  # player index -> slot index
    if len(gk_idxs) == 1:
        pinned[gk_idxs[0]] = 0

    free_players = [i for i in range(len(xi)) if i not in pinned]
    free_slots = [j for j in range(len(slots)) if j not in pinned.values()]

    players_xy = [natural_xy(positions.get(xi[i][1], "")) for i in free_players]
    sub_slots = [slots[j] for j in free_slots]
    solved = _solve(sub_slots, players_xy)

    for local_i, player_i in enumerate(free_players):
        slot_j = free_slots[solved[local_i]]
        result[slot_j] = xi[player_i]
    for player_i, slot_j in pinned.items():
        result[slot_j] = xi[player_i]

    return result
