import dash_mantine_components as dmc
from dash import dcc

from src.components.layout import build_layout


def _walk(node):
    yield node
    children = getattr(node, "children", None)
    if isinstance(children, (list, tuple)):
        for c in children:
            yield from _walk(c)
    elif children is not None:
        yield from _walk(children)


def _layout():
    return build_layout(venues=[], goal_mouth_panel=dmc.Box(id="gm-stub"))


def test_goal_mouth_card_mounted():
    classes = [getattr(n, "className", "") for n in _walk(_layout())]
    assert any("bento-card--goalmouth" in (c or "") for c in classes)
    # the group table card is still present (narrowed, not removed)
    assert any("bento-card--table" in (c or "") for c in classes)


def test_goal_mouth_drawer_and_store_present():
    ids = {getattr(n, "id", None) for n in _walk(_layout())}
    assert "goal-mouth-drawer" in ids
    assert "goal-mouth-zone" in ids


def test_store_default_is_none():
    store = next(n for n in _walk(_layout())
                if isinstance(n, dcc.Store) and n.id == "goal-mouth-zone")
    assert store.data is None
