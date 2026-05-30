from __future__ import annotations

import dash_leaflet as dl

from src.data.venues import Venue

# Themed base tiles (keyless CartoDB). The app swaps the TileLayer url between
# these via the theme clientside callback in app.py.
LIGHT_TILE = "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
DARK_TILE = "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
TILE_ATTRIBUTION = "© OpenStreetMap contributors © CARTO"

# SW and NE corners of a box snug to USA, Mexico, and Canada.
NA_BOUNDS = [[18.0, -145.0], [50.0, -50.0]]

NA_CENTER = [36.0, -95.0]
NA_ZOOM = 5
NA_MIN_ZOOM = 5

# Pattern-matching id type for venue markers; the app callback listens to all
# markers of this type and opens the detail drawer for the clicked one.
MARKER_TYPE = "venue-marker"

# Fixed control pin pushed to the far lower-left corner of the static view; it
# opens the filter drawer. Kept at the edge to leave room for more control pins.
FILTER_PIN = [19.5, -134.5]


def _filter_pin() -> dl.DivMarker:
    plane = (
        '<div class="filter-pin" data-icon="plane">'
        '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="2" stroke-linecap="round" '
        'stroke-linejoin="round"><path d="M17.8 19.2 16 11l3.5-3.5C21 6 21.5 4 21 3'
        'c-1-.5-3 0-4.5 1.5L13 8 4.8 6.2c-.5-.1-.9.1-1.1.5l-.3.5c-.2.5-.1 1 .3 1.3'
        'L9 12l-2 3H4l-1 1 3 2 2 3 1-1v-3l3-2 3.5 5.3c.3.4.8.5 1.3.3l.5-.2'
        'c.4-.3.6-.7.5-1.2z"/></svg>'
        "</div>"
    )
    return dl.DivMarker(
        id="filter-pin",
        position=FILTER_PIN,
        iconOptions={
            "html": plane,
            "className": "filter-pin-icon",
            "iconSize": [34, 34],
            "iconAnchor": [17, 17],
        },
        children=[dl.Tooltip("Team Travel Map")],
    )


MARKER_SIZE = 16  # px


def _marker(venue: Venue) -> dl.DivMarker:
    # Static, clickable base dot. The pulse for "active today" stadiums is drawn
    # by a separate overlay (see pulse_markers) because dash-leaflet does not
    # refresh a DivMarker's icon HTML when the same marker id is re-rendered.
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


def venue_markers(venues: list[Venue]) -> list[dl.DivMarker]:
    """The static, clickable base markers (one per venue)."""
    return [_marker(v) for v in venues]


def pulse_markers(venues: list[Venue], active_cities: set[str]) -> list[dl.DivMarker]:
    """Non-interactive pulsing rings over stadiums hosting a match on the
    selected day. Lives in its own layer that is rebuilt per date (empty →
    populated), which dash-leaflet renders reliably."""
    rings: list[dl.DivMarker] = []
    for v in venues:
        if v.city not in active_cities:
            continue
        rings.append(
            dl.DivMarker(
                id={"type": "venue-pulse", "index": v.city},
                position=[v.lat, v.lon],
                iconOptions={
                    "html": '<div class="venue-pulse-ring"></div>',
                    "className": "venue-pulse-icon",
                    "iconSize": [MARKER_SIZE, MARKER_SIZE],
                    "iconAnchor": [MARKER_SIZE / 2, MARKER_SIZE / 2],
                },
            )
        )
    return rings


def build_map(venues: list[Venue]) -> dl.Map:
    return dl.Map(
        children=[
            dl.TileLayer(id="base-tiles", url=DARK_TILE, attribution=TILE_ATTRIBUTION),
            dl.LayerGroup(id="venue-layer", children=venue_markers(venues)),
            dl.LayerGroup(id="pulse-layer"),
            dl.LayerGroup(id="flow-layer"),
            _filter_pin(),
        ],
        center=NA_CENTER,
        zoom=NA_ZOOM,
        minZoom=NA_MIN_ZOOM,
        maxBounds=NA_BOUNDS,
        maxBoundsViscosity=1.0,
        # Static position: zoomable but not pannable.
        dragging=False,
        boxZoom=False,
        keyboard=False,
        zoomControl=False,  # hide the +/- buttons (wheel/dbl-click still zoom in)
        style={"height": "100%", "width": "100%"},
    )
