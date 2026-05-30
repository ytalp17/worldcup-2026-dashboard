from __future__ import annotations

import dash_leaflet as dl

from src.data.host_cities import HostCity

OSM_URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
OSM_ATTRIBUTION = "© OpenStreetMap contributors"

# SW and NE corners of a box covering USA, Mexico, and Canada.
NA_BOUNDS = [[14.0, -168.0], [72.0, -52.0]]

NA_CENTER = [40.0, -100.0]
NA_ZOOM = 3
NA_MIN_ZOOM = 3


def _marker(city: HostCity) -> dl.Marker:
    label = f"{city.city} — {city.stadium} ({city.capacity:,})"
    return dl.Marker(
        position=[city.lat, city.lon],
        children=[dl.Tooltip(label)],
    )


def build_map(cities: list[HostCity]) -> dl.Map:
    return dl.Map(
        children=[
            dl.TileLayer(url=OSM_URL, attribution=OSM_ATTRIBUTION),
            *[_marker(c) for c in cities],
        ],
        center=NA_CENTER,
        zoom=NA_ZOOM,
        minZoom=NA_MIN_ZOOM,
        maxBounds=NA_BOUNDS,
        style={"height": "100%", "width": "100%"},
    )
