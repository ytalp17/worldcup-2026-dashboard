from __future__ import annotations

import dash_leaflet as dl

from src.data.flows import TeamFlow, format_distance


def render_flow(flow: TeamFlow) -> list:
    # One colour drives the line, arrowheads, and node dots so a team's flow is
    # always rendered in a single consistent colour.
    color = flow.color
    positions = [[s.lat, s.lon] for s in flow.stops]
    arrow = {
        "offset": "6%",
        "repeat": "18%",
        "endOffset": "0",
        "arrowHead": {
            "pixelSize": 12,
            "headAngle": 40,
            # Filled triangle in the team colour; setting both stroke (color) and
            # fill (fillColor) means the arrow can never fall back to Leaflet's
            # default blue, so it always matches the line.
            "polygon": True,
            "pathOptions": {
                "color": color,
                "fillColor": color,
                "fillOpacity": 1.0,
                "weight": 1,
            },
        },
    }
    comps: list = [
        # Colour is set via pathOptions (not the top-level `color` prop) so the
        # line re-styles when the flow is re-rendered for a different team — the
        # top-level prop only applies at creation, leaving the colour stale when
        # navigating the carousel.
        dl.Polyline(
            positions=positions,
            pathOptions={"color": color, "weight": 3},
            children=[dl.Tooltip(f"{flow.team}: {format_distance(flow.distance_km)}")],
        ),
        dl.PolylineDecorator(positions=positions, patterns=[arrow]),
    ]
    for s in flow.stops:
        comps.append(
            dl.CircleMarker(
                center=[s.lat, s.lon],
                radius=5,
                pathOptions={
                    "color": color,
                    "fillColor": color,
                    "fillOpacity": 1.0,
                    "weight": 1,
                },
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
