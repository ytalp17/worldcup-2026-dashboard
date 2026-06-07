from __future__ import annotations

from collections.abc import Callable

import dash_ag_grid as dag
import dash_mantine_components as dmc

from src.components.team_carousel import display_name
from src.data.flows import TeamFlow

# Continent -> short code shown in the Continent column.
CONTINENT_ABBR = {
    "North America": "NAM",
    "South America": "SAM",
    "Europe": "EUR",
    "Africa": "AFR",
    "Asia": "ASI",
    "Oceania": "OCE",
}


def continent_abbr(continent: str) -> str:
    return CONTINENT_ABBR.get(continent, (continent or "")[:3].upper())


# Travel-distance grid columns. Team uses the shared TeamCell renderer (flag +
# name); Distance is numeric (so it sorts correctly) but displays in the unit
# chosen by the #unit-toggle switch via formatDistance in dashAgGridFunctions.js.
_JOURNEY_COL_DEFS = [
    {"headerName": "Team", "field": "team", "cellRenderer": "TeamCell",
     "flex": 1, "minWidth": 110, "sortable": True},
    {"headerName": "Cont", "field": "continent", "width": 64, "minWidth": 56,
     "sortable": True},
    {"headerName": "Distance", "field": "distance_km",
     "valueFormatter": {"function": "formatDistance(params)"},
     "width": 120, "minWidth": 104, "sort": "desc", "sortable": True},
]

_JOURNEY_GRID_OPTIONS = {
    "suppressCellFocus": True,
    "rowHeight": 38,
    "headerHeight": 38,
    "pagination": True,
    "paginationPageSize": 12,
    # Minimal footer: no page-size dropdown (and CSS hides the text so only the
    # navigation arrows remain).
    "paginationPageSizeSelector": False,
    # The grid IS the selector: tick (or click) teams to drive the map flows.
    # enableSelectionWithoutKeys makes a plain click toggle a row (and keep the
    # others), so multi-select works without holding Ctrl/Cmd.
    "rowSelection": {
        "mode": "multiRow",
        "checkboxes": True,
        # Header checkbox = select-all / clear-all across every team.
        "headerCheckbox": True,
        "enableClickSelection": True,
        "enableSelectionWithoutKeys": True,
    },
    # Tint each selected team's row in its own flow colour (re-applied via a
    # clientside redrawRows on selection change).
    "getRowStyle": {"function": "journeyRowStyle(params)"},
}


def journey_rows(
    team_flows: dict[str, TeamFlow],
    asset_url: Callable[[str], str],
) -> list[dict]:
    """ag-grid rowData for every team, longest journey first."""
    rows: list[dict] = []
    for f in sorted(team_flows.values(), key=lambda x: x.distance_km, reverse=True):
        rows.append({
            "team": display_name(f.team),
            "team_raw": f.team,
            "flag": asset_url(f"country_logos/{f.team}.svg"),
            "continent": continent_abbr(f.continent),
            "distance_km": f.distance_km,
            "color": f.color,
        })
    return rows


def build_journey_grid(
    team_flows: dict[str, TeamFlow], asset_url: Callable[[str], str]
) -> dag.AgGrid:
    return dag.AgGrid(
        id="journey-grid",
        columnDefs=_JOURNEY_COL_DEFS,
        rowData=journey_rows(team_flows, asset_url),
        columnSize="responsiveSizeToFit",
        # Stable row ids keep selection intact across re-renders.
        getRowId="params.data.team_raw",
        # Dark theme by default; a clientside callback swaps quartz <-> quartz-dark.
        className="ag-theme-quartz-dark journey-grid",
        dashGridOptions=_JOURNEY_GRID_OPTIONS,
        style={"height": "560px", "width": "100%"},
    )


def build_filter_drawer(
    team_flows: dict | None = None,
    asset_url: Callable[[str], str] | None = None,
) -> dmc.Drawer:
    # The grid is the only control now: ticking/clicking team rows drives the map
    # flows directly (no separate dropdown). Each selected team's row is tinted in
    # its own flow colour; the header carries a km <-> mi unit switch.
    children: list = []
    if team_flows and asset_url:
        children.append(
            dmc.Group(
                [
                    dmc.Text("Select teams to map their travel", size="sm", fw=600),
                    dmc.Switch(
                        id="unit-toggle",
                        offLabel="km",
                        onLabel="mi",
                        checked=False,
                        size="md",
                        color="gray",
                        persistence=True,
                    ),
                ],
                justify="space-between",
                align="center",
                mb="xs",
                wrap="nowrap",
            )
        )
        children.append(build_journey_grid(team_flows, asset_url))
    return dmc.Drawer(
        id="filter-drawer",
        title="Team Travel Map",
        position="right",
        size="md",
        padding="md",
        opened=False,
        withCloseButton=True,
        withOverlay=False,
        lockScroll=False,
        zIndex=2500,
        # Frosted-glass panel: translucent + blurred so the map shows through
        # while the leaderboard/legend text stays legible (see assets/styles.css).
        classNames={
            "content": "filter-drawer-frosted",
            "header": "filter-drawer-frosted-header",
        },
        children=children,
    )
