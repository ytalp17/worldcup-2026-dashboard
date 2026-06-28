import dash_leaflet as dl

from src.components.map_view import (
    build_map,
    DARK_TILE,
    LIGHT_TILE,
    MARKER_TYPE,
    NA_BOUNDS,
)
from src.data.venues import Venue


def _venue(city, official_name, lat, lon):
    return Venue(
        city=city,
        country="USA",
        lat=lat,
        lon=lon,
        official_name=official_name,
        stadium_name=f"{city} Stadium",
        location="Somewhere",
        capacity=50000,
        opened=2000,
        info="info",
        image_filename=f"{city}.jpg",
        has_image=True,
        timezone="America/Chicago",
        tz_label="Central Time",
    )


VENUES = [
    _venue("Mexico City", "Estadio Azteca", 19.3029, -99.1505),
    _venue("Toronto", "BMO Field", 43.6333, -79.4186),
    _venue("Dallas", "AT&T Stadium", 32.7473, -97.0945),
]


def _children(m):
    return m.children if isinstance(m.children, list) else [m.children]


def _walk(node):
    yield node
    children = getattr(node, "children", None)
    if isinstance(children, (list, tuple)):
        for c in children:
            yield from _walk(c)
    elif children is not None:
        yield from _walk(children)


def _markers(m):
    # Venue markers carry a pattern-matching dict id and now live inside the
    # "venue-layer" LayerGroup; the filter pin uses a plain string id.
    return [
        c for c in _walk(m)
        if isinstance(c, dl.DivMarker) and isinstance(getattr(c, "id", None), dict)
    ]


def test_build_map_returns_dl_map():
    assert isinstance(build_map(VENUES), dl.Map)


def test_pulse_markers_only_for_active_cities():
    from src.components.map_view import pulse_markers

    rings = pulse_markers(VENUES, active_cities={"Mexico City"})
    assert len(rings) == 1
    assert rings[0].id == {"type": "venue-pulse", "index": "Mexico City"}
    assert "venue-pulse-ring" in rings[0].iconOptions["html"]


def test_pulse_markers_empty_when_no_active_cities():
    from src.components.map_view import pulse_markers

    assert pulse_markers(VENUES, active_cities=set()) == []


def test_map_has_static_base_markers_and_pulse_layer():
    m = build_map(VENUES)
    venue_layer = next(
        c for c in _children(m)
        if isinstance(c, dl.LayerGroup) and getattr(c, "id", None) == "venue-layer"
    )
    assert len(venue_layer.children) == len(VENUES)
    # The pulse overlay layer exists (filled per selected date by a callback).
    pulse_layer = [
        c for c in _children(m)
        if isinstance(c, dl.LayerGroup) and getattr(c, "id", None) == "pulse-layer"
    ]
    assert len(pulse_layer) == 1


def test_map_has_one_marker_per_venue():
    assert len(_markers(build_map(VENUES))) == len(VENUES)


def test_map_has_themed_base_tile_layer():
    tile_layers = [c for c in _children(build_map(VENUES)) if isinstance(c, dl.TileLayer)]
    assert len(tile_layers) == 1
    tl = tile_layers[0]
    assert tl.id == "base-tiles"
    # Defaults to the dark tiles (the app starts in dark mode).
    assert tl.url == DARK_TILE
    assert DARK_TILE != LIGHT_TILE


def test_map_bounds_locked_to_north_america():
    assert build_map(VENUES).maxBounds == NA_BOUNDS


def test_map_bounds_are_a_hard_wall():
    assert build_map(VENUES).maxBoundsViscosity == 1.0


def test_map_fixed_initial_view_no_zoom_out():
    m = build_map(VENUES)
    assert m.center == [32.5, -94.86]
    assert m.zoom == 5
    # Zoom is locked: minZoom == maxZoom == the initial zoom.
    assert m.minZoom == 5
    assert m.maxZoom == 5


def test_map_zoom_is_fully_locked():
    m = build_map(VENUES)
    # No zooming at all: wheel, double-click, and pinch are disabled, and the
    # min/max zoom collapse onto the initial zoom.
    assert m.scrollWheelZoom is False
    assert m.doubleClickZoom is False
    assert m.touchZoom is False
    assert m.minZoom == m.maxZoom == m.zoom


def test_map_is_pannable_but_zoom_locked():
    m = build_map(VENUES)
    # Pannable via drag (constrained to maxBounds), but no zoom gestures:
    # box-zoom (shift-drag) and keyboard (which also binds +/- zoom) stay off.
    assert m.dragging is True
    assert m.boxZoom is False
    assert m.keyboard is False


def test_map_hides_zoom_control():
    assert build_map(VENUES).zoomControl is False


def test_map_has_flow_layer_and_no_pin_layers():
    # The control pins moved out of the map into a fixed overlay; the map keeps
    # the flow layer but no longer carries any pin layers.
    m = build_map(VENUES)
    children = m.children if isinstance(m.children, list) else [m.children]
    layer_ids = [getattr(c, "id", None) for c in children]
    assert "flow-layer" in layer_ids
    assert "filter-pin-layer" not in layer_ids
    assert "tournament-pin-layer" not in layer_ids


def test_markers_positioned_at_venue_coordinates():
    positions = {tuple(mk.position) for mk in _markers(build_map(VENUES))}
    assert (19.3029, -99.1505) in positions


def test_each_marker_has_pattern_matching_id():
    ids = [mk.id for mk in _markers(build_map(VENUES))]
    assert {"type": MARKER_TYPE, "index": "Dallas"} in ids
    assert all(mid["type"] == MARKER_TYPE for mid in ids)
    assert {mid["index"] for mid in ids} == {"Mexico City", "Toronto", "Dallas"}


def test_marker_tooltip_shows_city_and_official_name():
    markers = _markers(build_map(VENUES))
    dallas = next(mk for mk in markers if mk.id["index"] == "Dallas")
    tooltip = next(c for c in dallas.children if isinstance(c, dl.Tooltip))
    assert "Dallas" in tooltip.children
    assert "AT&T Stadium" in tooltip.children


def test_marker_uses_custom_pulse_dot_markup():
    marker = _markers(build_map(VENUES))[0]
    opts = marker.iconOptions
    assert "venue-marker" in opts["html"]
    # Custom className avoids Leaflet's default white box around div icons.
    assert opts["className"] == "venue-marker-icon"


def test_live_match_for_venue_returns_live_match():
    from src.components.map_view import live_match_for_venue
    live = {"matches": [
        {"venue": "Dallas Stadium", "is_live": True, "home": "Brazil",
         "away": "Mexico", "home_score": 2, "away_score": 1, "match_id": 42},
    ]}
    m = live_match_for_venue("Dallas Stadium", live)
    assert m is not None and m["match_id"] == 42


def test_live_match_for_venue_none_when_not_live_or_absent():
    from src.components.map_view import live_match_for_venue
    not_live = {"matches": [{"venue": "Dallas Stadium", "is_live": False, "match_id": 1}]}
    assert live_match_for_venue("Dallas Stadium", not_live) is None
    assert live_match_for_venue("Dallas Stadium", {"matches": []}) is None
    assert live_match_for_venue("Dallas Stadium", None) is None


def test_live_score_markers_one_per_live_venue():
    from src.components.map_view import live_score_markers
    from types import SimpleNamespace
    venues = [
        SimpleNamespace(city="Dallas", lat=32.7, lon=-97.0, stadium_name="Dallas Stadium"),
        SimpleNamespace(city="Boston", lat=42.3, lon=-71.0, stadium_name="Boston Stadium"),
    ]
    live = {"matches": [
        {"venue": "Dallas Stadium", "is_live": True, "home": "Brazil",
         "away": "Mexico", "home_score": 2, "away_score": 1, "clock": 67,
         "match_id": 42},
    ]}
    markers = live_score_markers(venues, live)
    assert len(markers) == 1  # only the live Dallas venue
    blob = str(markers[0].to_plotly_json())
    assert "2-1" in blob                       # score
    assert "BRA" in blob and "MEX" in blob     # team abbreviations
    assert "67" in blob                        # live minute


def test_live_score_markers_empty_when_no_live():
    from src.components.map_view import live_score_markers
    assert live_score_markers([], {"matches": []}) == []


def test_map_controls_overlay_has_all_buttons():
    from src.components.map_view import build_map_controls

    overlay = build_map_controls()
    assert overlay.id == "map-controls-overlay"
    ids = {getattr(n, "id", None) for n in _walk(overlay)}
    # How-to-use (light bulb), Tournament Stats, Team Travel Map, Third-Place
    # Ranking and Knockout buttons.
    assert "tour-control" in ids
    assert "tournament-control" in ids
    assert "filter-control" in ids
    assert "third-place-control" in ids
    assert "knockout-control" in ids


def test_map_controls_button_order_top_to_bottom():
    from src.components.map_view import build_map_controls

    overlay = build_map_controls()
    button_ids = [
        nid for n in _walk(overlay)
        if (nid := getattr(n, "id", None))
        in ("tour-control", "tournament-control", "filter-control",
            "third-place-control", "knockout-control")
    ]
    # Stacked top-to-bottom; the How-to-use light bulb sits above everything.
    assert button_ids == ["tour-control", "tournament-control", "filter-control",
                          "third-place-control", "knockout-control"]


def test_map_controls_buttons_have_tooltip_labels():
    import dash_mantine_components as dmc
    from src.components.map_view import build_map_controls

    labels = {
        t.label for t in _walk(build_map_controls()) if isinstance(t, dmc.Tooltip)
    }
    assert {"How to use", "Tournament Stats", "Team Travel Map",
            "Third-Place Ranking", "Tournament Knockout"} <= labels


def test_map_controls_buttons_are_theme_aware():
    import dash_mantine_components as dmc
    from src.components.map_view import build_map_controls

    icons = [n for n in _walk(build_map_controls()) if isinstance(n, dmc.ActionIcon)]
    assert len(icons) == 5
    # "default" variant renders the icon in the theme text color (black in light,
    # white in dark), matching the live match-score items.
    assert all(b.variant == "default" for b in icons)


def test_map_controls_overlay_is_fixed_bottom_left():
    from src.components.map_view import build_map_controls

    style = build_map_controls().style
    assert style["position"] == "fixed"
    assert "bottom" in style and "left" in style
