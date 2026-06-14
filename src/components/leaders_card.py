from __future__ import annotations

import dash_ag_grid as dag
import dash_mantine_components as dmc

# Segmented-control label -> the stat key returned by LiveDataService.team_leaders.
_STAT_KEYS = {"Goals": "goals", "Assists": "assists",
              "Cards": "cards", "Rating": "rating"}

_GRID_OPTIONS = {
    "suppressCellFocus": True,
    "rowHeight": 34,
    "headerHeight": 34,
    "overlayNoRowsTemplate": "No player data yet",
}


def _stat_key(tab: str) -> str:
    return _STAT_KEYS.get(tab, "goals")


def leaders_columns(tab: str) -> list[dict]:
    """Column defs for the active tab. The stat column's header is the tab name;
    its field is always `value` so the grid need not be rebuilt on tab change."""
    return [
        {"headerName": "#", "field": "rank", "width": 52, "sortable": False,
         "cellClass": "leaders-grid__rank"},
        {"headerName": "Player", "field": "player", "flex": 1,
         "minWidth": 120, "sortable": True},
        {"headerName": tab, "field": "value", "width": 84, "sortable": True,
         "type": "rightAligned"},
        {"headerName": "Apps", "field": "apps", "width": 70, "sortable": True,
         "type": "rightAligned"},
    ]


def leaders_row_data(leaders: dict | None, tab: str) -> list[dict]:
    """Rows for the active tab, with a 1-based rank. Empty list when no data."""
    rows = (leaders or {}).get(_stat_key(tab), [])
    return [{"rank": i + 1, "player": r["player"], "value": r["value"],
             "apps": r["apps"]} for i, r in enumerate(rows)]


def build_leaders_card() -> dmc.Box:
    """Player-leaders card: a Goals/Assists/Cards/Rating control over an AG grid
    of the selected team's players, ranked by the active stat."""
    header = dmc.Group(
        [
            dmc.Text("Leaders", fw=700, size="sm"),
            dmc.Text("", id="leaders-table-title", size="sm", c="dimmed"),
        ],
        justify="space-between",
        align="center",
        wrap="nowrap",
        className="bento-card__header",
    )

    tabs = dmc.SegmentedControl(
        id="leaders-tabs",
        value="Goals",
        data=["Goals", "Assists", "Cards", "Rating"],
        size="xs",
        fullWidth=True,
    )

    grid = dag.AgGrid(
        id="leaders-grid",
        columnDefs=leaders_columns("Goals"),
        rowData=[],
        className="ag-theme-quartz-dark leaders-grid",
        dashGridOptions=_GRID_OPTIONS,
        style={"width": "100%", "height": "100%"},
    )

    body = dmc.Box([tabs, grid], className="leaders-panel__body")
    return dmc.Box([header, body], className="leaders-panel")
