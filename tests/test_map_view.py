import dash_leaflet as dl

from src.components.map_view import build_map, NA_BOUNDS, OSM_URL
from src.data.host_cities import HostCity

CITIES = [
    HostCity("Mexico City", "Mexico", "Estadio Azteca", 87523, 19.3029, -99.1505),
    HostCity("Toronto", "Canada", "BMO Field", 45000, 43.6333, -79.4186),
    HostCity("Dallas", "USA", "AT&T Stadium", 80000, 32.7473, -97.0945),
]


def _children(m):
    return m.children if isinstance(m.children, list) else [m.children]


def test_build_map_returns_dl_map():
    m = build_map(CITIES)
    assert isinstance(m, dl.Map)


def test_map_has_one_marker_per_city():
    m = build_map(CITIES)
    markers = [c for c in _children(build_map(CITIES)) if isinstance(c, dl.Marker)]
    assert len(markers) == len(CITIES)


def test_map_has_osm_tile_layer():
    m = build_map(CITIES)
    tile_layers = [c for c in _children(m) if isinstance(c, dl.TileLayer)]
    assert len(tile_layers) == 1
    assert tile_layers[0].url == OSM_URL


def test_map_bounds_locked_to_north_america():
    m = build_map(CITIES)
    assert m.maxBounds == NA_BOUNDS


def test_markers_positioned_at_city_coordinates():
    m = build_map(CITIES)
    markers = [c for c in _children(m) if isinstance(c, dl.Marker)]
    positions = {tuple(mk.position) for mk in markers}
    assert (19.3029, -99.1505) in positions
