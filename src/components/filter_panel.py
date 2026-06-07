from __future__ import annotations

from collections.abc import Callable

import dash_ag_grid as dag
import dash_mantine_components as dmc

from src.components.team_carousel import display_name
from src.data.flows import TeamFlow, format_distance

# Travel-distance grid columns. Team uses the shared TeamCell renderer (flag +
# name); Distance is numeric (so it sorts correctly) but displays the friendly
# "km / mi" string via the formatDistanceKm function in dashAgGridFunctions.js.
_JOURNEY_COL_DEFS = [
    {"headerName": "Team", "field": "team", "cellRenderer": "TeamCell",
     "flex": 1, "minWidth": 120, "sortable": True},
    {"headerName": "Distance", "field": "distance_km",
     "valueFormatter": {"function": "formatDistanceKm(params)"},
     "width": 150, "minWidth": 120, "sort": "desc", "sortable": True},
]

_JOURNEY_GRID_OPTIONS = {
    "suppressCellFocus": True,
    "rowHeight": 38,
    "headerHeight": 38,
    "pagination": True,
    "paginationPageSize": 12,
    # Colour the rows whose team is selected in the #team-filter dropdown; a
    # callback keeps each row's `selected` flag in sync with the selection.
    "rowClassRules": {"journey-row--selected": "params.data.selected"},
}


def journey_rows(
    team_flows: dict[str, TeamFlow],
    asset_url: Callable[[str], str],
    selected: list[str] | None = None,
) -> list[dict]:
    """ag-grid rowData for every team, longest journey first. `selected` (the
    dropdown value) marks rows for live highlighting."""
    selected_set = set(selected or [])
    rows: list[dict] = []
    for f in sorted(team_flows.values(), key=lambda x: x.distance_km, reverse=True):
        rows.append({
            "team": display_name(f.team),
            "team_raw": f.team,
            "flag": asset_url(f"country_logos/{f.team}.svg"),
            "distance_km": f.distance_km,
            "selected": f.team in selected_set,
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
        # Dark theme by default; a clientside callback swaps quartz <-> quartz-dark.
        className="ag-theme-quartz-dark journey-grid",
        dashGridOptions=_JOURNEY_GRID_OPTIONS,
        style={"height": "560px", "width": "100%"},
    )


def build_filter_drawer(
    options: list[dict],
    team_flows: dict | None = None,
    asset_url: Callable[[str], str] | None = None,
) -> dmc.Drawer:
    children = [
        dmc.MultiSelect(
            id="team-filter",
            data=options,
            searchable=True,
            clearable=True,
            placeholder="Select teams…",
            maxDropdownHeight=320,
            # Float the dropdown above the drawer (zIndex 2500); otherwise the
            # drawer paints over the options and intercepts clicks.
            comboboxProps={"zIndex": 3000},
        ),
        dmc.Stack(id="filter-legend", gap="xs", mt="md"),
    ]
    # All-teams travel-distance grid (replaces the old longest/shortest cards):
    # paginated, sortable, with selected rows highlighted in sync with the dropdown.
    if team_flows and asset_url:
        children.append(dmc.Divider(my="md"))
        children.append(dmc.Text("Travel distances", size="sm", fw=600, mb="xs"))
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


def legend(selected, team_flows: dict[str, TeamFlow]) -> list:
    rows: list = []
    for team in selected or []:
        flow = team_flows.get(team)
        if flow is None:
            continue
        rows.append(
            dmc.Group(
                [
                    dmc.Box(
                        w=12,
                        h=12,
                        style={
                            "background": flow.color,
                            "borderRadius": "50%",
                            "flex": "0 0 auto",
                        },
                    ),
                    dmc.Text(
                        f"{team} — {format_distance(flow.distance_km)}", size="sm"
                    ),
                ],
                gap="xs",
                align="center",
            )
        )
    return rows
