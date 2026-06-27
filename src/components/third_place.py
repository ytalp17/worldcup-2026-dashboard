"""Group Third-Place Ranking drawer.

A right-side frosted drawer (same chrome as the Team Travel Map / Knockout
drawers) holding an AG grid that ranks the 12 group third-placed teams by the
World Cup 2026 tiebreaker. The best 8 advance to the Round of 32 and are marked
green — a left-edge accent on the row plus an "R32" tag in the status column.

Ranking lives in :mod:`src.data.third_place`; this module is the presentation
layer (columns, rows, drawer chrome).
"""
from __future__ import annotations

from collections.abc import Callable

import dash_ag_grid as dag
import dash_mantine_components as dmc

from src.components.team_carousel import display_name
from src.data.third_place import third_place_ranking

THIRD_PLACE_GRID_ID = "third-place-grid"

# Narrow numeric column shared by Pld/GF/GD/Pts; widths are proportional hints for
# responsiveSizeToFit (the grid scales columns to fill the drawer width).
_NUM_COL = {"width": 36, "minWidth": 32, "sortable": True,
            "cellClass": "tp-grid__num"}

COL_DEFS = [
    {"headerName": "#", "field": "rank", "width": 34, "minWidth": 30,
     "sortable": True, "cellClass": "tp-grid__rank"},
    # Status tag: "R32" for the advancing eight, green via cellClassRules.
    {"headerName": "", "field": "tag", "width": 48, "minWidth": 44,
     "sortable": False, "cellClass": "tp-grid__tag",
     "cellClassRules": {"tp-cell--advance": "params.data.advance === true"}},
    {"headerName": "Team", "field": "team", "cellRenderer": "TeamCell",
     "width": 120, "minWidth": 90, "sortable": True},
    {"headerName": "Grp", "field": "group", "width": 40, "minWidth": 36,
     "sortable": True, "cellClass": "tp-grid__num"},
    {"headerName": "Pld", "field": "mp", **_NUM_COL},
    {"headerName": "GF", "field": "gf", **_NUM_COL},
    {"headerName": "GD", "field": "gd", **_NUM_COL},
    {"headerName": "Pts", "field": "pts", **_NUM_COL,
     "cellStyle": {"fontWeight": 700}},
]

# rowClassRules paints a green left-edge accent on each advancing row.
_GRID_OPTIONS = {
    "suppressCellFocus": True,
    "rowHeight": 40,
    "headerHeight": 36,
    "domLayout": "normal",
    "rowClassRules": {"tp-row--advance": "params.data.advance === true"},
}


def _group_letter(group_name: str) -> str:
    """'Group A' -> 'A'; anything else is returned unchanged."""
    return group_name[len("Group "):] if group_name.startswith("Group ") else group_name


def third_place_rows(
    standings: dict | None,
    asset_url: Callable[[str], str],
    resolve_team: Callable[[str], str] = lambda t: t,
) -> list[dict]:
    """ag-grid rowData for the ranked third-placed teams. ``flag`` uses the
    resolved (official) team name so it lines up with the static logo assets;
    ``advance``/``tag`` carry the top-8 Round-of-32 marker."""
    rows: list[dict] = []
    for r in third_place_ranking(standings, resolve_team):
        rows.append({
            "rank": r["rank"],
            "tag": "R32" if r["advance"] else "",
            "advance": r["advance"],
            "team": display_name(r["team"]),
            "flag": asset_url(f"country_logos/{r['team']}.svg"),
            "group": _group_letter(r["group"]),
            "mp": r["played"],
            "gf": r["goals_for"],
            "gd": r["goal_diff"],
            "pts": r["points"],
        })
    return rows


def build_third_place_drawer() -> dmc.Drawer:
    """Right-side frosted drawer with the third-place ranking grid. Rows are filled
    by an app callback off the live-standings snapshot (static seed on first load)."""
    header = dmc.Text(
        "Best 8 of 12 third-placed teams advance to the Round of 32",
        size="sm", c="dimmed", mb="xs")

    grid = dag.AgGrid(
        id=THIRD_PLACE_GRID_ID,
        columnDefs=COL_DEFS,
        rowData=[],
        columnSize="responsiveSizeToFit",
        className="ag-theme-quartz-dark tp-grid",
        dashGridOptions=_GRID_OPTIONS,
        style={"height": "calc(100vh - 140px)", "width": "100%"},
    )

    return dmc.Drawer(
        id="third-place-drawer",
        title="Third-Place Ranking",
        position="right",
        size="md",
        padding="md",
        opened=False,
        withCloseButton=True,
        withOverlay=False,
        lockScroll=False,
        zIndex=2500,
        classNames={
            "content": "filter-drawer-frosted",
            "header": "filter-drawer-frosted-header",
        },
        children=[header, grid],
    )
