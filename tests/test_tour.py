import dash_mantine_components as dmc
from dash import dcc

from src.components.tour import TOUR_STEPS, build_tour


def _walk(node):
    yield node
    children = getattr(node, "children", None)
    if isinstance(children, (list, tuple)):
        for c in children:
            yield from _walk(c)
    elif children is not None:
        yield from _walk(children)


def _ids(node):
    return {getattr(n, "id", None) for n in _walk(node)}


# --- step data ---------------------------------------------------------------

def test_full_tour_has_many_steps():
    # "Full feature tour" — cover the map, calendar, all four controls, both
    # switches and the team-mode dashboards.
    assert len(TOUR_STEPS) >= 10


def test_every_step_has_required_shape():
    for s in TOUR_STEPS:
        assert s["id"] and isinstance(s["id"], str)
        assert s["title"] and isinstance(s["title"], str)
        assert s["body"] and isinstance(s["body"], str)
        # target is a CSS selector or None (None => centered, no spotlight).
        assert s["target"] is None or (isinstance(s["target"], str) and s["target"])
        assert s["mode"] in ("time", "team", None)


def test_step_ids_are_unique():
    ids = [s["id"] for s in TOUR_STEPS]
    assert len(ids) == len(set(ids))


def test_tour_covers_the_key_surfaces():
    targets = {s["target"] for s in TOUR_STEPS}
    for sel in (
        "#map-container",
        "#calendar-wrapper",
        "#tournament-control",
        "#filter-control",
        "#third-place-control",
        "#knockout-control",
        "#color-scheme-toggle",
        "#mode-toggle",
        "#analysis-panel",
        "#goal-mouth-graph",
    ):
        assert sel in targets, f"tour should spotlight {sel}"


def test_team_mode_steps_exist():
    modes = {s["mode"] for s in TOUR_STEPS}
    assert "team" in modes and "time" in modes


def test_control_steps_run_in_time_mode():
    # The bottom-left controls only exist in Time mode, so their steps must
    # request Time mode (else the spotlight would land on a hidden element).
    by_target = {s["target"]: s for s in TOUR_STEPS}
    for sel in ("#tournament-control", "#filter-control",
                "#third-place-control", "#knockout-control"):
        assert by_target[sel]["mode"] == "time"


def test_team_dashboard_steps_run_in_team_mode():
    by_target = {s["target"]: s for s in TOUR_STEPS}
    for sel in ("#analysis-panel", "#goal-mouth-graph"):
        assert by_target[sel]["mode"] == "team"


# --- mounted components ------------------------------------------------------

def test_build_tour_exposes_required_ids():
    root = build_tour()
    ids = _ids(root)
    for needed in (
        "tour-overlay", "tour-spotlight", "tour-card",
        "tour-card-title", "tour-card-body", "tour-card-progress",
        "tour-back", "tour-next", "tour-skip", "tour-steps",
    ):
        assert needed in ids, f"missing {needed}"


def test_build_tour_ships_steps_in_a_store():
    root = build_tour()
    store = next(n for n in _walk(root)
                if isinstance(n, dcc.Store) and getattr(n, "id", None) == "tour-steps")
    assert store.data == TOUR_STEPS


def test_tour_card_uses_dmc_buttons():
    root = build_tour()
    button_ids = {b.id for b in _walk(root) if isinstance(b, dmc.Button)}
    assert {"tour-back", "tour-next", "tour-skip"} <= button_ids


def test_overlay_hidden_by_default():
    root = build_tour()
    overlay = next(n for n in _walk(root)
                   if getattr(n, "id", None) == "tour-overlay")
    assert overlay.style.get("display") == "none"
