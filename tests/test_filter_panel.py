from datetime import date

import dash_mantine_components as dmc

from src.components.filter_panel import build_filter_drawer, legend
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
    drawer = build_filter_drawer(
        [{"group": "Europe", "items": [{"value": "France", "label": "France"}]}]
    )
    assert isinstance(drawer, dmc.Drawer)
    assert drawer.id == "filter-drawer"
    assert drawer.position == "right"
    assert drawer.withOverlay is False


def test_multiselect_dropdown_floats_above_the_drawer():
    # The dropdown is portaled and must out-stack the drawer (zIndex 2500),
    # otherwise the drawer paints over the options and clicks are intercepted.
    drawer = build_filter_drawer([])
    select = next(n for n in _walk(drawer) if isinstance(n, dmc.MultiSelect))
    assert select.comboboxProps["zIndex"] > drawer.zIndex


def test_filter_drawer_has_multiselect_with_grouped_data():
    options = [{"group": "Europe", "items": [{"value": "France", "label": "France"}]}]
    drawer = build_filter_drawer(options)
    selects = [n for n in _walk(drawer) if isinstance(n, dmc.MultiSelect)]
    assert len(selects) == 1
    assert selects[0].id == "team-filter"
    assert selects[0].data == options


def test_legend_lists_selected_teams_with_color():
    flow = TeamFlow(
        "Brazil", "South America", "#22c55e",
        (FlowStop(0, 0, "S", date(2026, 6, 1), 1),),
    )
    rows = legend(["Brazil"], {"Brazil": flow})
    texts = [n.children for n in _walk(dmc.Box(rows)) if isinstance(n, dmc.Text)]
    assert any(isinstance(t, str) and "Brazil" in t for t in texts)
    assert legend([], {"Brazil": flow}) == []


def test_legend_row_includes_formatted_distance():
    flow = TeamFlow(
        "Brazil", "South America", "#22c55e",
        (FlowStop(0, 0, "S", date(2026, 6, 1), 1),),
        1839.7,
    )
    rows = legend(["Brazil"], {"Brazil": flow})
    texts = [n.children for n in _walk(dmc.Box(rows)) if isinstance(n, dmc.Text)]
    joined = " ".join(t for t in texts if isinstance(t, str))
    assert "Brazil" in joined
    assert "1,840 km / 1,143 mi" in joined


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
    # Nothing selected by default.
    assert all(r["selected"] is False for r in rows)


def test_journey_rows_marks_selected_in_sync_with_dropdown():
    from src.components.filter_panel import journey_rows
    rows = journey_rows(_flows_for_grid(), _asset, selected=["Nearby"])
    by_team = {r["team_raw"]: r["selected"] for r in rows}
    assert by_team["Nearby"] is True
    assert by_team["Faraway"] is False
    assert by_team["Midway"] is False


def test_drawer_has_journey_grid_with_pagination_of_12():
    import dash_ag_grid as dag
    drawer = build_filter_drawer([], _flows_for_grid(), _asset)
    grids = [n for n in _walk(drawer) if isinstance(n, dag.AgGrid)]
    assert len(grids) == 1
    grid = grids[0]
    assert grid.id == "journey-grid"
    assert grid.dashGridOptions["pagination"] is True
    assert grid.dashGridOptions["paginationPageSize"] == 12
    assert len(grid.rowData) == 3
    # Selected rows are highlighted via a row-class rule synced to the dropdown.
    assert "journey-row--selected" in grid.dashGridOptions["rowClassRules"]


def test_journey_grid_all_columns_sortable():
    import dash_ag_grid as dag
    drawer = build_filter_drawer([], _flows_for_grid(), _asset)
    grid = next(n for n in _walk(drawer) if isinstance(n, dag.AgGrid))
    assert all(c.get("sortable") for c in grid.columnDefs)


def test_drawer_without_asset_url_skips_grid():
    # Cannot build flag URLs without asset_url -> no grid (drawer still builds).
    import dash_ag_grid as dag
    drawer = build_filter_drawer([], _flows_for_grid())
    assert not [n for n in _walk(drawer) if isinstance(n, dag.AgGrid)]


def test_filter_drawer_content_is_frosted():
    drawer = build_filter_drawer([])
    # The content panel gets a frosted-glass class so the map shows through.
    assert drawer.classNames["content"] == "filter-drawer-frosted"
    assert drawer.classNames["header"] == "filter-drawer-frosted-header"


def test_build_filter_drawer_without_flows_still_builds():
    drawer = build_filter_drawer([])
    assert isinstance(drawer, dmc.Drawer)
