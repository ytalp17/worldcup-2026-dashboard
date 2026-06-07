import dash_mantine_components as dmc

from src.components.formation_pitch import build_formation_panel, pitch_src
from src.data.lineups import StartingEleven


def _asset(path):
    return "/assets/" + path


LIN = StartingEleven(
    "Argentina", "argentina", "433", "Lionel Scaloni",
    (("Messi", 10), ("Álvarez", 9)),
)


def _walk(node):
    yield node
    children = getattr(node, "children", None)
    if isinstance(children, (list, tuple)):
        for c in children:
            yield from _walk(c)
    elif children is not None:
        yield from _walk(children)


def test_pitch_src_theme():
    assert pitch_src("argentina", _asset, True).endswith("pitches/argentina-dark.png")
    assert pitch_src("argentina", _asset, False).endswith("pitches/argentina-light.png")


def test_panel_has_header_image_and_formation():
    panel = build_formation_panel(LIN, _asset, dark=True)
    assert isinstance(panel, dmc.Box)
    img = next(n for n in _walk(panel) if isinstance(n, dmc.Image))
    assert img.id == "formation-img"
    assert img.src.endswith("pitches/argentina-dark.png")
    title = next(n for n in _walk(panel)
                 if getattr(n, "id", None) == "formation-title")
    assert "4-3-3" in title.children
    assert "Argentina" in title.children


def test_panel_light_theme_uses_light_image():
    panel = build_formation_panel(LIN, _asset, dark=False)
    img = next(n for n in _walk(panel) if isinstance(n, dmc.Image))
    assert img.src.endswith("pitches/argentina-light.png")


def test_panel_none_placeholder_has_no_image_src():
    panel = build_formation_panel(None, _asset)
    imgs = [n for n in _walk(panel) if isinstance(n, dmc.Image) and n.src]
    assert not imgs
    # The header still renders (with a dash placeholder) so the card has a title.
    title = next(n for n in _walk(panel)
                 if getattr(n, "id", None) == "formation-title")
    assert title is not None
