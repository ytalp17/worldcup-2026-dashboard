from __future__ import annotations

import dash_leaflet as dl

from src.data.flows import TeamFlow


def render_flow(flow: TeamFlow) -> list:
    positions = [[s.lat, s.lon] for s in flow.stops]
    arrow = {
        "offset": "6%",
        "repeat": "18%",
        "endOffset": "0",
        "arrowHead": {
            "pixelSize": 11,
            "headAngle": 40,
            "polygon": False,
            "pathOptions": {"color": flow.color, "weight": 3},
        },
    }
    comps: list = [
        dl.Polyline(positions=positions, color=flow.color, weight=3),
        dl.PolylineDecorator(positions=positions, patterns=[arrow]),
    ]
    for s in flow.stops:
        comps.append(
            dl.CircleMarker(
                center=[s.lat, s.lon],
                radius=5,
                color=flow.color,
                fillColor=flow.color,
                fillOpacity=1.0,
                weight=1,
            )
        )
    return comps


def flows_for(selected, team_flows: dict) -> list:
    comps: list = []
    for team in selected or []:
        flow = team_flows.get(team)
        if flow is not None:
            comps.extend(render_flow(flow))
    return comps
