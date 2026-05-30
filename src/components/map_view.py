from __future__ import annotations

import dash_leaflet as dl

from src.data.venues import Venue

# Themed base tiles (keyless CartoDB). The app swaps the TileLayer url between
# these via the theme clientside callback in app.py.
LIGHT_TILE = "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
DARK_TILE = "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
TILE_ATTRIBUTION = "© OpenStreetMap contributors © CARTO"

# SW and NE corners of a box snug to USA, Mexico, and Canada.
NA_BOUNDS = [[14.0, -145.0], [55.0, -50.0]]

NA_CENTER = [36.0, -95.0]
NA_ZOOM = 5
NA_MIN_ZOOM = 5

# Pattern-matching id type for venue markers; the app callback listens to all
# markers of this type and opens the detail drawer for the clicked one.
MARKER_TYPE = "venue-marker"


MARKER_SIZE = 16  # px


def _marker(venue: Venue) -> dl.DivMarker:
    return dl.DivMarker(
        id={"type": MARKER_TYPE, "index": venue.city},
        position=[venue.lat, venue.lon],
        iconOptions={
            "html": '<div class="venue-marker"></div>',
            "className": "venue-marker-icon",
            "iconSize": [MARKER_SIZE, MARKER_SIZE],
            "iconAnchor": [MARKER_SIZE / 2, MARKER_SIZE / 2],
        },
        children=[dl.Tooltip(f"{venue.city} — {venue.official_name}")],
    )


def build_map(venues: list[Venue]) -> dl.Map:
    return dl.Map(
        children=[
            dl.TileLayer(id="base-tiles", url=DARK_TILE, attribution=TILE_ATTRIBUTION),
            *[_marker(v) for v in venues],
        ],
        center=NA_CENTER,
        zoom=NA_ZOOM,
        minZoom=NA_MIN_ZOOM,
        maxBounds=NA_BOUNDS,
        maxBoundsViscosity=1.0,
        style={"height": "100%", "width": "100%"},
    )
