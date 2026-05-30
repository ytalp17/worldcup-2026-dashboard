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


def test_filter_drawer_is_left_and_non_blocking():
    drawer = build_filter_drawer(
        [{"group": "Europe", "items": [{"value": "France", "label": "France"}]}]
    )
    assert isinstance(drawer, dmc.Drawer)
    assert drawer.id == "filter-drawer"
    assert drawer.position == "left"
    assert drawer.withOverlay is False


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
    assert "Brazil" in texts
    assert legend([], {"Brazil": flow}) == []
