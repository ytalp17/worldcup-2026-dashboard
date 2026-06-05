import dash_mantine_components as dmc

from src.components.team_carousel import (
    advance,
    build_team_carousel,
    carousel_view,
    center_team,
    display_name,
    team_order,
    window,
)


def test_team_order_is_alphabetical_caseinsensitive():
    flows = {"brazil": object(), "Argentina": object(), "Canada": object()}
    assert team_order(flows) == ["Argentina", "brazil", "Canada"]


def test_advance_wraps_forward_and_backward():
    assert advance(47, +1, 48) == 0  # 48 = number of WC2026 teams
    assert advance(0, -1, 48) == 47
    assert advance(10, +1, 48) == 11


def test_window_returns_five_with_wrap():
    teams = ["A", "B", "C", "D", "E"]
    # (prev2, prev1, center, next1, next2)
    assert window(teams, 2) == ("A", "B", "C", "D", "E")
    assert window(teams, 0) == ("D", "E", "A", "B", "C")
    assert window(teams, 4) == ("C", "D", "E", "A", "B")


def test_center_team_wraps():
    teams = ["A", "B", "C"]
    assert center_team(teams, 0) == "A"
    assert center_team(teams, 3) == "A"
    assert center_team(teams, 5) == "C"


def _asset(path):  # mimic app.get_asset_url
    return "/assets/" + path


def _walk(node):
    yield node
    children = getattr(node, "children", None)
    if isinstance(children, (list, tuple)):
        for c in children:
            yield from _walk(c)
    elif children is not None:
        yield from _walk(children)


def test_carousel_view_returns_five_srcs_and_center_name():
    teams = ["Argentina", "Brazil", "Canada", "Denmark", "Ecuador"]
    view = carousel_view(teams, 2, _asset)
    assert view["center_name"] == "Canada"
    assert view["center_src"] == "/assets/country_logos/Canada.svg"
    assert view["prev1_src"] == "/assets/country_logos/Brazil.svg"
    assert view["next1_src"] == "/assets/country_logos/Denmark.svg"
    assert view["prev2_src"] == "/assets/country_logos/Argentina.svg"
    assert view["next2_src"] == "/assets/country_logos/Ecuador.svg"


def test_carousel_view_center_name_uses_ampersand_to_save_space():
    teams = ["Australia", "Bosnia and Herzegovina", "Brazil"]
    view = carousel_view(teams, 1, _asset)
    # Display label uses "&"; the logo src still uses the real team name.
    assert view["center_name"] == "Bosnia & Herzegovina"
    assert view["center_src"] == "/assets/country_logos/Bosnia and Herzegovina.svg"


def test_carousel_view_wraps_at_index_zero():
    teams = ["Argentina", "Brazil", "Canada", "Denmark", "Ecuador"]
    view = carousel_view(teams, 0, _asset)
    assert view["center_name"] == "Argentina"
    assert view["prev1_src"] == "/assets/country_logos/Ecuador.svg"
    assert view["prev2_src"] == "/assets/country_logos/Denmark.svg"
    assert view["next1_src"] == "/assets/country_logos/Brazil.svg"
    assert view["next2_src"] == "/assets/country_logos/Canada.svg"


def test_build_team_carousel_has_expected_ids_and_arrows():
    teams = ["Argentina", "Brazil", "Canada"]
    root = build_team_carousel(teams, _asset, index=0)
    ids = {getattr(n, "id", None) for n in _walk(root)}
    for expected in {
        "team-carousel",
        "carousel-prev",
        "carousel-next",
        "carousel-logo-prev2",
        "carousel-logo-prev",
        "carousel-logo-next",
        "carousel-logo-next2",
        "carousel-logo-center",
        "carousel-img-prev2",
        "carousel-img-prev",
        "carousel-img-center",
        "carousel-img-next",
        "carousel-img-next2",
        "carousel-name",
    }:
        assert expected in ids


def test_build_team_carousel_center_image_uses_center_class():
    teams = ["Argentina", "Brazil", "Canada"]
    root = build_team_carousel(teams, _asset, index=0)
    center_img = next(
        n for n in _walk(root)
        if isinstance(n, dmc.Image) and getattr(n, "id", None) == "carousel-img-center"
    )
    assert "carousel-logo--center" in (center_img.className or "")


def test_display_name_applies_overrides_then_ampersand():
    assert display_name("Korea Republic") == "South Korea"
    assert display_name("Bosnia and Herzegovina") == "Bosnia & Herzegovina"
    assert display_name("Brazil") == "Brazil"
