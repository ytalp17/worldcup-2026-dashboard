from __future__ import annotations

from collections.abc import Callable

import dash_ag_grid as dag
import dash_mantine_components as dmc

from src.components.team_carousel import display_name
from src.data.groups import Group

# Narrow numeric column shared by MP/W/D/L/GD/Pts. Widths are proportional hints
# for responsiveSizeToFit (below): the grid scales every column to fill the card
# width exactly — no horizontal scroll — while minWidth keeps single-digit values
# readable.
_NUM_COL = {
    "width": 30,
    "minWidth": 26,
    "sortable": True,
    "cellClass": "group-grid__num",
}

COL_DEFS = [
    {"headerName": "#", "field": "rank", "width": 30, "minWidth": 26,
     "sortable": True, "cellClass": "group-grid__rank"},
    {"headerName": "Team", "field": "team", "cellRenderer": "TeamCell",
     "width": 96, "minWidth": 58, "sortable": True},
    {"headerName": "MP", "field": "mp", **_NUM_COL},
    {"headerName": "W", "field": "w", **_NUM_COL},
    {"headerName": "D", "field": "d", **_NUM_COL},
    {"headerName": "L", "field": "l", **_NUM_COL},
    {"headerName": "GD", "field": "gd", **_NUM_COL},
    {"headerName": "P", "field": "pts", **_NUM_COL,
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


def live_group_rows(
    group_name: str,
    live_standings: dict | None,
    asset_url: Callable[[str], str],
    resolve_team: Callable[[str], str] = lambda t: t,
) -> list[dict] | None:
    """ag-grid rowData built from the LIVE standings snapshot for one group, or
    None if that group is absent/empty (caller then falls back to static rows).
    Row order is the API's (already position-ordered). `resolve_team` maps the
    raw live team name to its official name so the flag filename and display name
    line up with the static assets (the live feed spells some names differently)."""
    table = (live_standings or {}).get(group_name)
    if not table:
        return None
    rows = []
    for rank, s in enumerate(table, start=1):
        team = resolve_team(s["team"])
        rows.append({
            "rank": rank,
            "team": display_name(team),
            "flag": asset_url(f"country_logos/{team}.svg"),
            "mp": s["played"],
            "w": s["won"],
            "d": s["drawn"],
            "l": s["lost"],
            "gd": s["goal_diff"],
            "pts": s["points"],
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
        # Fit all eight columns to the card width exactly (no horizontal scroll);
        # re-fits on resize. minWidths (in COL_DEFS) stop the numeric columns from
        # collapsing to an ellipsis.
        columnSize="responsiveSizeToFit",
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
