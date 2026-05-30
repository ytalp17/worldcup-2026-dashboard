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


def _flows_for_leaderboard():
    def mk(team, km):
        return TeamFlow(team, "Europe", "#fff",
                        (FlowStop(0, 0, "S", date(2026, 6, 1), 1),), km)
    return {
        "Faraway": mk("Faraway", 9000.0),
        "Midway": mk("Midway", 3000.0),
        "Nearby": mk("Nearby", 100.0),
    }


def test_drawer_renders_longest_and_shortest_leaderboard():
    drawer = build_filter_drawer([], _flows_for_leaderboard())
    texts = [n.children for n in _walk(drawer) if isinstance(n, dmc.Text)]
    joined = " ".join(t for t in texts if isinstance(t, str))
    assert "Longest journeys" in joined
    assert "Shortest journeys" in joined
    assert "Faraway" in joined
    assert "Nearby" in joined
    assert "9,000 km" in joined


def test_leaderboard_sections_are_wrapped_in_cards():
    drawer = build_filter_drawer([], _flows_for_leaderboard())
    cards = [n for n in _walk(drawer) if isinstance(n, dmc.Card)]
    # One card per section: Longest journeys + Shortest journeys.
    assert len(cards) == 2
    for card in cards:
        assert card.withBorder is True
        # Each card still carries its section's content.
        card_texts = [n.children for n in _walk(card) if isinstance(n, dmc.Text)]
        assert any(isinstance(t, str) and "journeys" in t for t in card_texts)


def test_filter_drawer_content_is_frosted():
    drawer = build_filter_drawer([])
    # The content panel gets a frosted-glass class so the map shows through.
    assert drawer.classNames["content"] == "filter-drawer-frosted"
    assert drawer.classNames["header"] == "filter-drawer-frosted-header"


def test_build_filter_drawer_without_flows_still_builds():
    drawer = build_filter_drawer([])
    assert isinstance(drawer, dmc.Drawer)
