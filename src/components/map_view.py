from __future__ import annotations

import dash_leaflet as dl

from src.data.venues import Venue

OSM_URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
OSM_ATTRIBUTION = "© OpenStreetMap contributors"

# SW and NE corners of a box covering USA, Mexico, and Canada.
NA_BOUNDS = [[14.0, -168.0], [72.0, -52.0]]

NA_CENTER = [40.0, -100.0]
NA_ZOOM = 3
NA_MIN_ZOOM = 3

# Pattern-matching id type for venue markers; the app callback listens to all
# markers of this type and opens the detail drawer for the clicked one.
MARKER_TYPE = "venue-marker"


def _marker(venue: Venue) -> dl.Marker:
    return dl.Marker(
        id={"type": MARKER_TYPE, "index": venue.city},
        position=[venue.lat, venue.lon],
        children=[dl.Tooltip(f"{venue.city} — {venue.official_name}")],
    )


def build_map(venues: list[Venue]) -> dl.Map:
    return dl.Map(
        children=[
            dl.TileLayer(url=OSM_URL, attribution=OSM_ATTRIBUTION),
            *[_marker(v) for v in venues],
        ],
        center=NA_CENTER,
        zoom=NA_ZOOM,
        minZoom=NA_MIN_ZOOM,
        maxBounds=NA_BOUNDS,
        style={"height": "100%", "width": "100%"},
    )
