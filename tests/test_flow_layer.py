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
    return TeamFlow("Brazil", "South America", "#22c55e", stops)


def test_render_flow_has_polyline_decorator_and_dots():
    comps = render_flow(_flow())
    polylines = [c for c in comps if isinstance(c, dl.Polyline)]
    decorators = [c for c in comps if isinstance(c, dl.PolylineDecorator)]
    dots = [c for c in comps if isinstance(c, dl.CircleMarker)]
    assert len(polylines) == 1
    assert polylines[0].color == "#22c55e"
    assert polylines[0].positions == [[40.8, -74.0], [39.9, -75.1], [25.9, -80.2]]
    assert len(decorators) == 1
    assert len(dots) == 3


def test_flows_for_empty_selection_is_empty():
    assert flows_for([], {"Brazil": _flow()}) == []
    assert flows_for(None, {"Brazil": _flow()}) == []


def test_flows_for_selected_team_includes_its_polyline():
    comps = flows_for(["Brazil"], {"Brazil": _flow()})
    assert any(isinstance(c, dl.Polyline) and c.color == "#22c55e" for c in comps)
