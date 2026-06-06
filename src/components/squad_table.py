from __future__ import annotations

import dash_ag_grid as dag
import dash_mantine_components as dmc

from src.data.squads import Squad

POSITION_CODES = {
    "Goalkeeper": "GK",
    "Centre-Back": "CB",
    "Left-Back": "LB",
    "Right-Back": "RB",
    "Defensive Midfield": "DM",
    "Central Midfield": "CM",
    "Attacking Midfield": "AM",
    "Left Midfield": "LM",
    "Right Midfield": "RM",
    "Left Winger": "LW",
    "Right Winger": "RW",
    "Centre-Forward": "CF",
    "Second Striker": "SS",
}


def position_code(position: str) -> str:
    """Short code for a position; falls back to initials of words."""
    if position in POSITION_CODES:
        return POSITION_CODES[position]
    parts = position.replace("-", " ").split()
    return "".join(p[0] for p in parts).upper() or "?"


# `#` and `Player` are pinned left so identity stays visible while the stat
# columns scroll horizontally. No columnSize: fixed widths + a narrower card
# give native horizontal scroll for the 12 columns.
COL_DEFS = [
    {"headerName": "#", "field": "number", "width": 48, "pinned": "left",
     "sortable": True, "cellClass": "squad-grid__num"},
    {"headerName": "Player", "field": "name", "width": 150, "pinned": "left",
     "sortable": True},
    {"headerName": "Pos", "field": "pos", "width": 56, "sortable": True},
    {"headerName": "DOB", "field": "dob", "width": 96, "sortable": True},
    {"headerName": "Age", "field": "age", "width": 56, "sortable": True},
    {"headerName": "Club", "field": "club", "width": 150, "sortable": True},
    {"headerName": "Ht", "field": "height", "width": 70, "sortable": True},
    {"headerName": "Foot", "field": "foot", "width": 64, "sortable": True},
    {"headerName": "Caps", "field": "caps", "width": 56, "sortable": True},
    {"headerName": "Gls", "field": "goals", "width": 56, "sortable": True},
    {"headerName": "Debut", "field": "debut", "width": 96, "sortable": True},
    {"headerName": "Value", "field": "value", "width": 84, "sortable": True},
]

_GRID_OPTIONS = {
    "suppressCellFocus": True,
    "rowHeight": 36,
    "headerHeight": 36,
}


def squad_rows(squad: Squad) -> list[dict]:
    rows = []
    for p in squad.players:
        rows.append({
            "number": p.number,
            "name": p.name,
            "pos": position_code(p.position),
            "dob": p.dob,
            "age": p.age,
            "club": p.club,
            "height": f"{p.height_m} m" if p.height_m else "",
            "foot": p.foot.title() if p.foot else "",
            "caps": p.caps,
            "goals": p.goals,
            "debut": p.debut,
            "value": p.market_value,
        })
    return rows


def build_squad_panel(squad: Squad | None) -> dmc.Box:
    name = squad.name if squad else "—"
    rows = squad_rows(squad) if squad else []

    # Card header bar: bold "Squad" label left, live team name right, divider below.
    header = dmc.Group(
        [
            dmc.Text("Squad", fw=700, size="sm"),
            dmc.Text(name, id="squad-table-title", size="sm", c="dimmed"),
        ],
        justify="space-between",
        align="center",
        wrap="nowrap",
        className="bento-card__header",
    )

    grid = dag.AgGrid(
        id="squad-grid",
        columnDefs=COL_DEFS,
        rowData=rows,
        className="ag-theme-quartz-dark squad-grid",
        dashGridOptions=_GRID_OPTIONS,
        style={"width": "100%", "height": "100%"},
    )

    body = dmc.Box(grid, className="squad-panel__body")
    return dmc.Box([header, body], className="squad-panel")
