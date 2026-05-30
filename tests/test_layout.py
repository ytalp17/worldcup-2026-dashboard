import dash_leaflet as dl
import dash_mantine_components as dmc

from src.components.layout import DRAWER_Z_INDEX, build_layout
from src.data.venues import Venue


def _venue(city):
    return Venue(
        city=city,
        country="USA",
        lat=10.0,
        lon=10.0,
        official_name=f"{city} Field",
        location="Loc",
        capacity=1,
        opened=2000,
        info="info",
        image_filename=f"{city}.jpg",
        has_image=True,
    )


VENUES = [_venue("Dallas"), _venue("Toronto")]


def _walk(node):
    yield node
    children = getattr(node, "children", None)
    if isinstance(children, (list, tuple)):
        for c in children:
            yield from _walk(c)
    elif children is not None:
        yield from _walk(children)


def test_build_layout_returns_mantine_provider():
    layout = build_layout(VENUES)
    assert isinstance(layout, dmc.MantineProvider)
    assert layout.id == "mantine-provider"


def test_layout_contains_stadium_drawer():
    drawers = [n for n in _walk(build_layout(VENUES)) if isinstance(n, dmc.Drawer)]
    assert len(drawers) == 1
    assert drawers[0].id == "stadium-drawer"


def test_drawer_opens_from_left_and_above_leaflet():
    drawer = next(n for n in _walk(build_layout(VENUES)) if isinstance(n, dmc.Drawer))
    assert drawer.position == "left"
    # Leaflet panes/controls go up to ~1000; the drawer must sit above them.
    assert DRAWER_Z_INDEX > 1000
    assert drawer.zIndex == DRAWER_Z_INDEX


def test_header_has_contrast_logos_before_title():
    layout = build_layout(VENUES)
    groups = [n for n in _walk(layout) if isinstance(n, dmc.Group)]
    brand = next(
        g for g in groups
        if isinstance(g.children, (list, tuple))
        and any(isinstance(c, dmc.Title) for c in g.children)
    )
    children = list(brand.children)
    imgs = [c for c in children if isinstance(c, dmc.Image)]
    title_idx = next(i for i, c in enumerate(children) if isinstance(c, dmc.Title))

    assert len(imgs) == 2
    # Both logos sit before the title.
    assert all(children.index(im) < title_idx for im in imgs)

    black = next(im for im in imgs if "fifa_logo_black" in im.src)
    white = next(im for im in imgs if "fifa_logo_white" in im.src)
    # Black shows in light mode (hidden in dark); white shows in dark mode.
    assert black.darkHidden is True
    assert white.lightHidden is True


def test_layout_contains_map_with_marker_per_venue():
    maps = [n for n in _walk(build_layout(VENUES)) if isinstance(n, dl.Map)]
    assert len(maps) == 1
    markers = [c for c in maps[0].children if isinstance(c, dl.Marker)]
    assert len(markers) == len(VENUES)
