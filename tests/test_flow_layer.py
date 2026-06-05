from datetime import date

import dash_leaflet as dl

from src.components.flow_layer import flows_for, render_flow
from src.data.flows import FlowStop, TeamFlow


def _flow():
    stops = (
        FlowStop(40.8, -74.0, "New York New Jersey Stadium", date(2026, 6, 13), 7),
        FlowStop(39.9, -75.1, "Philadelphia Stadium", date(2026, 6, 19), 40),
        FlowStop(25.9, -80.2, "Miami Stadium", date(2026, 6, 24), 60),
    )
    return TeamFlow("Brazil", "South America", "#22c55e", stops, 1839.7)


def test_render_flow_has_polyline_decorator_and_dots():
    comps = render_flow(_flow())
    polylines = [c for c in comps if isinstance(c, dl.Polyline)]
    decorators = [c for c in comps if isinstance(c, dl.PolylineDecorator)]
    dots = [c for c in comps if isinstance(c, dl.CircleMarker)]
    assert len(polylines) == 1
    assert polylines[0].pathOptions["color"] == "#22c55e"
    assert polylines[0].positions == [[40.8, -74.0], [39.9, -75.1], [25.9, -80.2]]
    assert len(decorators) == 1
    assert len(dots) == 3


def test_arrow_color_matches_line_color_per_team():
    flow = _flow()
    comps = render_flow(flow)
    line = next(c for c in comps if isinstance(c, dl.Polyline))
    decorator = next(c for c in comps if isinstance(c, dl.PolylineDecorator))
    arrow_opts = decorator.patterns[0]["arrowHead"]["pathOptions"]
    # The arrowhead must be filled and stroked with the exact line/team color so
    # the arrow never falls back to Leaflet's default colour. The line carries
    # its colour in pathOptions so it re-styles when the team changes.
    assert line.pathOptions["color"] == flow.color
    assert arrow_opts["color"] == flow.color
    assert arrow_opts["fillColor"] == flow.color


def test_flows_for_empty_selection_is_empty():
    assert flows_for([], {"Brazil": _flow()}) == []
    assert flows_for(None, {"Brazil": _flow()}) == []


def test_flows_for_selected_team_includes_its_polyline():
    comps = flows_for(["Brazil"], {"Brazil": _flow()})
    assert any(
        isinstance(c, dl.Polyline) and c.pathOptions["color"] == "#22c55e"
        for c in comps
    )


def test_polyline_has_distance_tooltip():
    comps = render_flow(_flow())
    polyline = next(c for c in comps if isinstance(c, dl.Polyline))
    tooltips = [c for c in (polyline.children or []) if isinstance(c, dl.Tooltip)]
    assert len(tooltips) == 1
    assert "1,840 km / 1,143 mi" in tooltips[0].children
    assert "Brazil" in tooltips[0].children
