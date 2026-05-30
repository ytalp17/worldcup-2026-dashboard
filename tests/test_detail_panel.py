import dash_mantine_components as dmc

from src.components.detail_panel import PLACEHOLDER_TEXT, stadium_detail
from src.data.venues import Venue


def _venue(has_image: bool) -> Venue:
    return Venue(
        city="Dallas",
        country="USA",
        lat=32.7473,
        lon=-97.0945,
        official_name="AT&T Stadium",
        location="Arlington, Texas, USA",
        capacity=94000,
        opened=2009,
        info="Dallas Stadium is a jaw-dropping example of stadium architecture.",
        image_filename="Dallas_Stadium.jpg",
        has_image=has_image,
    )


def _walk(node):
    """Yield every component and string in a Dash component tree."""
    yield node
    children = getattr(node, "children", None)
    if isinstance(children, (list, tuple)):
        for c in children:
            yield from _walk(c)
    elif children is not None:
        yield from _walk(children)


def _all_text(node) -> str:
    return " ".join(n for n in _walk(node) if isinstance(n, str))


def _images(node):
    return [n for n in _walk(node) if isinstance(n, dmc.Image)]


def test_detail_with_image_renders_image_with_correct_src():
    content = dmc.Box(stadium_detail(_venue(has_image=True)))
    imgs = _images(content)
    assert len(imgs) == 1
    assert imgs[0].src == "/assets/stadiums/Dallas_Stadium.jpg"


def test_detail_without_image_shows_placeholder_not_image():
    content = dmc.Box(stadium_detail(_venue(has_image=False)))
    assert _images(content) == []
    assert PLACEHOLDER_TEXT in _all_text(content)


def test_detail_shows_key_stats_and_info():
    content = dmc.Box(stadium_detail(_venue(has_image=True)))
    text = _all_text(content)
    assert "94,000" in text          # capacity, formatted
    assert "2009" in text            # year opened
    assert "Arlington, Texas, USA" in text  # location
    assert "jaw-dropping" in text    # info blurb
