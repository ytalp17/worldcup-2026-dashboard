import dash_leaflet as dl

from src.components.map_view import build_map, MARKER_TYPE, NA_BOUNDS, OSM_URL
from src.data.venues import Venue


def _venue(city, official_name, lat, lon):
    return Venue(
        city=city,
        country="USA",
        lat=lat,
        lon=lon,
        official_name=official_name,
        location="Somewhere",
        capacity=50000,
        opened=2000,
        info="info",
        image_filename=f"{city}.jpg",
        has_image=True,
    )


VENUES = [
    _venue("Mexico City", "Estadio Azteca", 19.3029, -99.1505),
    _venue("Toronto", "BMO Field", 43.6333, -79.4186),
    _venue("Dallas", "AT&T Stadium", 32.7473, -97.0945),
]


def _children(m):
    return m.children if isinstance(m.children, list) else [m.children]


def _markers(m):
    return [c for c in _children(m) if isinstance(c, dl.Marker)]


def test_build_map_returns_dl_map():
    assert isinstance(build_map(VENUES), dl.Map)


def test_map_has_one_marker_per_venue():
    assert len(_markers(build_map(VENUES))) == len(VENUES)


def test_map_has_osm_tile_layer():
    tile_layers = [c for c in _children(build_map(VENUES)) if isinstance(c, dl.TileLayer)]
    assert len(tile_layers) == 1
    assert tile_layers[0].url == OSM_URL


def test_map_bounds_locked_to_north_america():
    assert build_map(VENUES).maxBounds == NA_BOUNDS


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
