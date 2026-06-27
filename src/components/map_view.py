from __future__ import annotations

import dash_leaflet as dl
import dash_mantine_components as dmc
from dash import html
from dash_iconify import DashIconify

from src.components.live_strip import abbr
from src.data.venues import Venue

# Themed base tiles (keyless CartoDB). The app swaps the TileLayer url between
# these via the theme clientside callback in app.py.
LIGHT_TILE = "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
DARK_TILE = "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
TILE_ATTRIBUTION = "© OpenStreetMap contributors © CARTO"

# SW and NE corners of the box around USA, Mexico, and Canada.
NA_BOUNDS = [[12.00, -130.12], [53.00, -59.59]]

NA_CENTER = [32.50, -94.86]
NA_ZOOM = 5
NA_MIN_ZOOM = 5

# Pattern-matching id type for venue markers; the app callback listens to all
# markers of this type and opens the detail drawer for the clicked one.
MARKER_TYPE = "venue-marker"

# Fixed map controls live in a bottom-left overlay (see build_map_controls),
# not on the map itself. Each is an icon button that opens its drawer; a
# callback hides the whole overlay in Team mode.
_MAP_CONTROLS_STYLE = {
    "position": "fixed",
    "bottom": "16px",
    "left": "16px",
    "zIndex": 1500,
    "pointerEvents": "auto",
}


def map_controls_style(visible: bool = True) -> dict:
    """Style for the bottom-left controls overlay; hidden (display:none) off the
    calendar/Time view. Base positioning is always preserved."""
    style = dict(_MAP_CONTROLS_STYLE)
    if not visible:
        style["display"] = "none"
    return style


def _control_button(button_id: str, icon: str, label: str) -> dmc.Tooltip:
    return dmc.Tooltip(
        label=label,
        position="right",
        withArrow=True,
        children=dmc.ActionIcon(
            DashIconify(icon=icon, width=22),
            id=button_id,
            n_clicks=0,
            # "default" variant tracks the theme: bordered, with the icon in the
            # standard text color (dark in light mode, light in dark mode) — the
            # same color the live match-score items use.
            variant="default",
            size="xl",
            radius="xl",
        ),
    )


def build_map_controls() -> html.Div:
    """Fixed bottom-left overlay of icon buttons that open the Tournament Stats
    and Team Travel Map drawers. The outer 'map-controls-overlay' div is toggled
    to hide it off the calendar/Time view (Team mode)."""
    return html.Div(
        dmc.Stack(
            [
                _control_button("tournament-control", "tabler:trophy", "Tournament Stats"),
                _control_button("filter-control", "tabler:plane-tilt", "Team Travel Map"),
                _control_button("third-place-control", "fluent-emoji-high-contrast:3rd-place-medal", "Third-Place Ranking"),
                _control_button("knockout-control", "tabler:tournament", "Tournament Knockout"),
            ],
            gap="sm",
        ),
        id="map-controls-overlay",
        style=map_controls_style(visible=True),
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
                # Non-interactive so the click falls through to the base marker
                # underneath (which opens the stadium drawer).
                interactive=False,
                iconOptions={
                    "html": '<div class="venue-pulse-ring"></div>',
                    "className": "venue-pulse-icon",
                    "iconSize": [MARKER_SIZE, MARKER_SIZE],
                    "iconAnchor": [MARKER_SIZE / 2, MARKER_SIZE / 2],
                },
            )
        )
    return rings


def live_match_for_venue(stadium_name: str, live: dict | None) -> dict | None:
    """The in-play match at this stadium (by generic name), or None. Pure lookup."""
    for m in (live or {}).get("matches", []):
        if m.get("is_live") and m.get("venue") == stadium_name:
            return m
    return None


def _live_badge_html(match: dict) -> str:
    home_s, away_s = match.get("home_score"), match.get("away_score")
    score = f"{home_s}-{away_s}" if home_s is not None else "vs"
    pair = f"{abbr(match.get('home', ''))} {score} {abbr(match.get('away', ''))}"
    clock = match.get("clock")
    minute = f"&nbsp;{clock}'" if clock is not None else ""
    # Layout is inline; the colours live in the .live-badge CSS class so the
    # theme can recolour it (red in light mode, dark blue in dark mode).
    return (
        '<div class="live-badge" style="display:flex;align-items:center;gap:3px;'
        'font:700 10px/1 sans-serif;'
        'padding:2px 6px;border-radius:7px;white-space:nowrap;'
        'box-shadow:0 1px 3px rgba(0,0,0,.4);">'
        f'<span style="font-size:8px;">●</span>{pair}{minute}</div>'
    )


def live_score_markers(venues, live: dict | None) -> list:
    """Non-interactive LIVE score badges over stadiums hosting an in-play match.
    Rebuilt as its own layer (empty -> populated) like pulse_markers."""
    markers = []
    for v in venues:
        match = live_match_for_venue(v.stadium_name, live)
        if not match:
            continue
        markers.append(
            dl.DivMarker(
                id={"type": "live-badge", "index": v.city},
                position=[v.lat, v.lon],
                interactive=False,
                iconOptions={
                    "html": _live_badge_html(match),
                    "className": "venue-live-badge-icon",
                    # Offset the badge up-right of the dot so both are visible.
                    "iconSize": [104, 16],
                    "iconAnchor": [-6, 24],
                },
            )
        )
    return markers


def build_map(venues: list[Venue]) -> dl.Map:
    return dl.Map(
        children=[
            dl.TileLayer(id="base-tiles", url=DARK_TILE, attribution=TILE_ATTRIBUTION),
            dl.LayerGroup(id="venue-layer", children=venue_markers(venues)),
            dl.LayerGroup(id="pulse-layer"),
            dl.LayerGroup(id="live-layer"),
            dl.LayerGroup(id="flow-layer"),
        ],
        center=NA_CENTER,
        zoom=NA_ZOOM,
        minZoom=NA_MIN_ZOOM,
        maxZoom=NA_ZOOM,  # min == max == initial: zoom is fully locked
        maxBounds=NA_BOUNDS,
        maxBoundsViscosity=1.0,
        # Pannable within the bounds, but zoom is fully locked.
        dragging=True,
        boxZoom=False,           # shift-drag box-zoom is a zoom gesture: off
        keyboard=False,          # arrow keys also bind +/- zoom: off
        zoomControl=False,       # hide the +/- buttons
        scrollWheelZoom=False,   # no wheel zoom
        doubleClickZoom=False,   # no double-click zoom
        touchZoom=False,         # no pinch zoom on touch devices
        style={"height": "100%", "width": "100%"},
    )
