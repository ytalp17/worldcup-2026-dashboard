"""Head-to-head lineup pitch for the match-detail modal.

The live API hands lineups grouped into formation lines (GK -> forwards) via
``parse_lineups``' ``rows`` field, so placement needs no position-guessing: the
rows *are* the lines. Home takes the left half (attacking right), away the
right half (attacking left); the two forward lines meet at the centre.

Rendered with DMC + absolutely-positioned nodes (no matplotlib): instant,
responsive, and theme-reactive via CSS — the modal body is built once and can't
see the colour scheme, so a baked image would get stuck on one theme.
"""
from __future__ import annotations

import dash_mantine_components as dmc

# Pitch coordinate band (0-100). Players sit between these vertical bounds; the
# x-bands keep each half's keeper at the touchline and the forwards near centre.
_PITCH_TOP, _PITCH_BOT = 12.0, 88.0
# GK -> forwards. Keepers sit a little off the goal line (not at x=0/100) so
# their name label clears the pitch edge; forwards stop short of the halfway
# line so the two attacking lines' labels don't collide at the centre seam.
_HOME_X = (8.0, 43.0)
_AWAY_X = (92.0, 57.0)


def surname(name: str | None) -> str:
    """Last whitespace token of a player's name ('Christian Pulišić' -> 'Pulišić')."""
    return (name or "").strip().split()[-1] if (name or "").strip() else ""


def _line_x(side: str, i: int, n_rows: int) -> float:
    lo, hi = _HOME_X if side == "home" else _AWAY_X
    if n_rows <= 1:
        return (lo + hi) / 2
    return lo + (hi - lo) * i / (n_rows - 1)


def _node_y(j: int, n: int) -> float:
    # Spread a line of n players symmetrically about the centre, but cap the
    # spread so small lines (a double pivot, a front two) stay central instead
    # of stretching to the touchlines, while a back four spans the full width —
    # the way broadcast formation graphics look.
    if n <= 1:
        return 50.0
    half = min((_PITCH_BOT - _PITCH_TOP) / 2, (n - 1) * 13.0)
    return 50.0 - half + (2 * half) * j / (n - 1)


def pitch_nodes(rows: list, side: str) -> list[tuple[dict, float, float]]:
    """Place each player as ``(player, x, y)`` for one team's ``rows``.

    Rows are formation lines in order (GK first). ``side`` is "home" (keeper
    left) or "away" (keeper right, mirrored)."""
    out: list[tuple[dict, float, float]] = []
    n_rows = len(rows)
    for i, row in enumerate(rows):
        x = _line_x(side, i, n_rows)
        n = len(row)
        for j, player in enumerate(row):
            out.append((player, x, _node_y(j, n)))
    return out


def _player_node(player: dict, x: float, y: float, side: str) -> dmc.Box:
    # Every player (keepers included) takes their team colour. Colours live in
    # CSS so they can use gradients and react to the dark/light theme.
    return dmc.Box(
        [
            dmc.Box(
                str(player.get("number", "")),
                className=f"lu-node__badge lu-node__badge--{side}",
            ),
            dmc.Text(surname(player.get("name")), className="lu-node__name"),
        ],
        className="lu-node",
        style={"left": f"{x}%", "top": f"{y}%"},
    )


def build_lineup_pitch(lineups: dict) -> dmc.Box | None:
    """A single pitch with both teams facing each other, or ``None`` when no
    lineup rows are available (caller shows a fallback message)."""
    home_rows = (lineups.get("home") or {}).get("rows") or []
    away_rows = (lineups.get("away") or {}).get("rows") or []
    if not home_rows and not away_rows:
        return None

    nodes = [
        _player_node(p, x, y, "home")
        for p, x, y in pitch_nodes(home_rows, "home")
    ] + [
        _player_node(p, x, y, "away")
        for p, x, y in pitch_nodes(away_rows, "away")
    ]
    return dmc.Box(nodes, className="lu-pitch")
