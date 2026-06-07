from datetime import date

import dash_mantine_components as dmc

from src.components.filter_panel import build_filter_drawer
from src.data.flows import FlowStop, TeamFlow


def _walk(node):
    yield node
    children = getattr(node, "children", None)
    if isinstance(children, (list, tuple)):
        for c in children:
            yield from _walk(c)
    elif children is not None:
        yield from _walk(children)


def test_filter_drawer_is_right_and_non_blocking():
    drawer = build_filter_drawer()
    assert isinstance(drawer, dmc.Drawer)
    assert drawer.id == "filter-drawer"
    assert drawer.position == "right"
    assert drawer.withOverlay is False


def test_filter_drawer_has_no_multiselect_dropdown():
    # The dropdown is gone; the grid itself is the selector now.
    drawer = build_filter_drawer()
    assert not [n for n in _walk(drawer) if isinstance(n, dmc.MultiSelect)]


def _asset(path):
    return "/assets/" + path


def _flows_for_grid():
    def mk(team, km):
        return TeamFlow(team, "Europe", "#fff",
                        (FlowStop(0, 0, "S", date(2026, 6, 1), 1),), km)
    return {
        "Faraway": mk("Faraway", 9000.0),
        "Midway": mk("Midway", 3000.0),
        "Nearby": mk("Nearby", 100.0),
    }


def test_journey_rows_all_teams_sorted_by_distance_desc():
    from src.components.filter_panel import journey_rows
    rows = journey_rows(_flows_for_grid(), _asset)
    # Longest first (replaces the old "Longest journeys" card).
    assert [r["team"] for r in rows] == ["Faraway", "Midway", "Nearby"]
    assert rows[0]["distance_km"] == 9000.0
    assert rows[0]["flag"].endswith("country_logos/Faraway.svg")
    # Each row carries the team's flow colour (used to tint selected rows).
    assert rows[0]["color"] == "#fff"


def test_journey_rows_include_continent_abbreviation():
    from src.components.filter_panel import continent_abbr, journey_rows
    flows = {
        "Brazil": TeamFlow("Brazil", "South America", "#fff",
                           (FlowStop(0, 0, "S", date(2026, 6, 1), 1),), 5000.0),
        "France": TeamFlow("France", "Europe", "#fff",
                           (FlowStop(0, 0, "S", date(2026, 6, 1), 1),), 4000.0),
    }
    rows = {r["team_raw"]: r["continent"] for r in journey_rows(flows, _asset)}
    assert rows["Brazil"] == "SAM"
    assert rows["France"] == "EUR"
    assert continent_abbr("North America") == "NAM"
    assert continent_abbr("Oceania") == "OCE"


def test_drawer_has_journey_grid_with_pagination_and_selection():
    import dash_ag_grid as dag
    drawer = build_filter_drawer(_flows_for_grid(), _asset)
    grids = [n for n in _walk(drawer) if isinstance(n, dag.AgGrid)]
    assert len(grids) == 1
    grid = grids[0]
    assert grid.id == "journey-grid"
    assert grid.dashGridOptions["pagination"] is True
    assert grid.dashGridOptions["paginationPageSize"] == 12
    # Minimal footer: no page-size selector.
    assert grid.dashGridOptions["paginationPageSizeSelector"] is False
    assert len(grid.rowData) == 3
    # The grid is the selector: multi-row selection drives the map, with a
    # header checkbox for select-all / clear-all.
    assert grid.dashGridOptions["rowSelection"]["mode"] == "multiRow"
    assert grid.dashGridOptions["rowSelection"]["headerCheckbox"] is True
    # Selected rows are tinted per-team via a getRowStyle function.
    assert "getRowStyle" in grid.dashGridOptions
    # A Continent column is present.
    assert any(c["field"] == "continent" for c in grid.columnDefs)


def test_drawer_has_unit_switch_and_no_dropdown_or_legend():
    drawer = build_filter_drawer(_flows_for_grid(), _asset)
    ids = {getattr(n, "id", None) for n in _walk(drawer)}
    # A km/mi unit switch lives in the drawer ...
    assert "unit-toggle" in ids
    switch = next(n for n in _walk(drawer)
                  if isinstance(n, dmc.Switch) and n.id == "unit-toggle")
    assert switch.offLabel == "km"
    assert switch.onLabel == "mi"
    # ... and the old dropdown + selected-teams legend are gone.
    assert "team-filter" not in ids
    assert "filter-legend" not in ids


def test_journey_grid_all_columns_sortable():
    import dash_ag_grid as dag
    drawer = build_filter_drawer(_flows_for_grid(), _asset)
    grid = next(n for n in _walk(drawer) if isinstance(n, dag.AgGrid))
    assert all(c.get("sortable") for c in grid.columnDefs)


def test_drawer_without_asset_url_skips_grid():
    # Cannot build flag URLs without asset_url -> no grid (drawer still builds).
    import dash_ag_grid as dag
    drawer = build_filter_drawer(_flows_for_grid())
    assert not [n for n in _walk(drawer) if isinstance(n, dag.AgGrid)]


def test_filter_drawer_content_is_frosted():
    drawer = build_filter_drawer()
    # The content panel gets a frosted-glass class so the map shows through.
    assert drawer.classNames["content"] == "filter-drawer-frosted"
    assert drawer.classNames["header"] == "filter-drawer-frosted-header"


def test_build_filter_drawer_without_flows_still_builds():
    drawer = build_filter_drawer()
    assert isinstance(drawer, dmc.Drawer)
