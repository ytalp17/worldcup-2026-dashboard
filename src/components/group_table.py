from __future__ import annotations

from collections.abc import Callable

import dash_ag_grid as dag
import dash_mantine_components as dmc
from dash_iconify import DashIconify

from src.components.team_carousel import display_name
from src.data.groups import Group

# Narrow, right-aligned numeric column shared by MP/W/D/L/GD/Pts.
_NUM_COL = {
    "width": 46,
    "sortable": False,
    "cellClass": "ag-right-aligned-cell",
    "headerClass": "ag-right-aligned-header",
}

COL_DEFS = [
    {"headerName": "#", "field": "rank", "width": 42, "sortable": False,
     "cellClass": "group-grid__rank"},
    {"headerName": "Team", "field": "team", "cellRenderer": "TeamCell",
     "flex": 1, "minWidth": 130, "sortable": False},
    {"headerName": "MP", "field": "mp", **_NUM_COL},
    {"headerName": "W", "field": "w", **_NUM_COL},
    {"headerName": "D", "field": "d", **_NUM_COL},
    {"headerName": "L", "field": "l", **_NUM_COL},
    {"headerName": "GD", "field": "gd", **_NUM_COL},
    {"headerName": "Pts", "field": "pts", **_NUM_COL,
     "cellStyle": {"fontWeight": 700}},
]

# autoHeight: the grid grows to fit its (4) rows; the panel handles any overflow.
_GRID_OPTIONS = {
    "suppressCellFocus": True,
    "rowHeight": 40,
    "headerHeight": 36,
    "domLayout": "autoHeight",
}


def group_rows(group: Group, asset_url: Callable[[str], str]) -> list[dict]:
    """ag-grid rowData for a group. `team` is the display name; `flag` uses the
    raw team name (country_logos/<raw>.svg); all stats are zero for now."""
    rows: list[dict] = []
    for rank, s in enumerate(group.standings, start=1):
        rows.append({
            "rank": rank,
            "team": display_name(s.team),
            "flag": asset_url(f"country_logos/{s.team}.svg"),
            "mp": s.played,
            "w": s.won,
            "d": s.drawn,
            "l": s.lost,
            "gd": s.goal_diff,
            "pts": s.points,
        })
    return rows


def build_group_panel(group: Group | None, asset_url: Callable[[str], str]) -> dmc.Box:
    """The panel body: header (Table / World Cup / group name + chevron), the
    ag-grid, and an empty flex spacer reserved for future infographics."""
    name = group.name if group else "—"
    rows = group_rows(group, asset_url) if group else []

    header = dmc.Group(
        [
            dmc.Stack(
                [
                    dmc.Text("Table", fw=700, size="lg"),
                    dmc.Text("World Cup", size="xs", c="dimmed"),
                    dmc.Text(name, id="group-table-title", size="xs", c="dimmed"),
                ],
                gap=2,
            ),
            DashIconify(icon="radix-icons:chevron-right", width=20),
        ],
        justify="space-between",
        align="flex-start",
        wrap="nowrap",
        className="group-panel__header",
    )

    grid = dag.AgGrid(
        id="group-grid",
        columnDefs=COL_DEFS,
        rowData=rows,
        columnSize="responsiveSizeToFit",
        # Dark theme by default; a clientside callback swaps quartz <-> quartz-dark to follow the app color scheme.
        className="ag-theme-quartz-dark group-grid",
        dashGridOptions=_GRID_OPTIONS,
        style={"width": "100%"},
    )

    return dmc.Box(
        [header, grid, dmc.Box(id="group-extra", style={"flex": "1 1 auto"})],
        className="group-panel__body",
    )
