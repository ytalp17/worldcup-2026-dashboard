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
    assert m.center == [36.0, -95.0]
    assert m.zoom == 5
    # minZoom equals the initial zoom, so the user can zoom in but not out.
    assert m.minZoom == 5


def test_map_is_not_draggable():
    m = build_map(VENUES)
    # Static position: no panning via drag, box-zoom drag, or keyboard arrows.
    assert m.dragging is False
    assert m.boxZoom is False
    assert m.keyboard is False


def test_map_hides_zoom_control():
    assert build_map(VENUES).zoomControl is False


def test_map_has_flow_layer_and_filter_pin():
    from src.components.map_view import FILTER_PIN
    m = build_map(VENUES)
    children = m.children if isinstance(m.children, list) else [m.children]
    layer_ids = [getattr(c, "id", None) for c in children]
    assert "flow-layer" in layer_ids
    assert "filter-pin-layer" in layer_ids
    pins = [
        c for c in _walk(m)
        if isinstance(c, dl.DivMarker) and getattr(c, "id", None) == "filter-pin"
    ]
    assert len(pins) == 1
    assert pins[0].position == FILTER_PIN


def test_filter_pin_lives_inside_filter_pin_layer():
    m = build_map(VENUES)
    children = m.children if isinstance(m.children, list) else [m.children]
    layer = next(
        c for c in children
        if isinstance(c, dl.LayerGroup) and getattr(c, "id", None) == "filter-pin-layer"
    )
    pin_ids = [getattr(n, "id", None) for n in _walk(layer)]
    assert "filter-pin" in pin_ids


def test_filter_pin_uses_a_plane_icon():
    m = build_map(VENUES)
    pin = next(
        c for c in _walk(m)
        if isinstance(c, dl.DivMarker) and getattr(c, "id", None) == "filter-pin"
    )
    html = pin.iconOptions["html"]
    assert 'data-icon="plane"' in html
    assert "22 3 2 3 10 12.46" not in html


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
