from __future__ import annotations

from collections.abc import Callable

import dash_ag_grid as dag
import dash_mantine_components as dmc

from src.components.team_carousel import display_name
from src.data.groups import Group

# Narrow, left-aligned numeric column shared by MP/W/D/L/GD/Pts. Kept tight so
# all six fit alongside the flexible Team column in the ~1/3-width panel without
# responsiveSizeToFit squeezing them to an ellipsis.
_NUM_COL = {
    "width": 38,
    "sortable": False,
    "cellClass": "group-grid__num",
}

COL_DEFS = [
    {"headerName": "#", "field": "rank", "width": 34, "sortable": False,
     "cellClass": "group-grid__rank"},
    {"headerName": "Team", "field": "team", "cellRenderer": "TeamCell",
     "flex": 1, "minWidth": 90, "sortable": False},
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

    # Card header bar: bold "Table" label left, live group name right, divider below.
    header = dmc.Group(
        [
            dmc.Text("Table", fw=700, size="sm"),
            dmc.Text(name, id="group-table-title", size="sm", c="dimmed"),
        ],
        justify="space-between",
        align="center",
        wrap="nowrap",
        className="bento-card__header",
    )

    grid = dag.AgGrid(
        id="group-grid",
        columnDefs=COL_DEFS,
        rowData=rows,
        # No columnSize: the numeric columns keep their fixed widths and the Team
        # column (flex:1) absorbs the slack and re-flows on resize. sizeToFit was
        # avoided because it treats `width` as a ratio and shrinks the numeric
        # columns to an ellipsis in the narrow panel.
        # Dark theme by default; a clientside callback swaps quartz <-> quartz-dark to follow the app color scheme.
        className="ag-theme-quartz-dark group-grid",
        dashGridOptions=_GRID_OPTIONS,
        style={"width": "100%"},
    )

    body = dmc.Box(
        [grid, dmc.Box(id="group-extra", style={"flex": "1 1 auto"})],
        className="group-panel__body",
    )
    return dmc.Box([header, body], className="group-panel")
