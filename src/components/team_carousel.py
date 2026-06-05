from __future__ import annotations

from collections.abc import Callable

import dash_mantine_components as dmc
from dash_iconify import DashIconify

LOGO_DIR = "country_logos"


def team_order(team_flows: dict) -> list[str]:
    """All teams, alphabetical A→Z (case-insensitive on the raw team name)."""
    return sorted(team_flows.keys(), key=str.casefold)


def advance(index: int, delta: int, n: int) -> int:
    """Move the carousel index with wrap-around (endless loop)."""
    return (index + delta) % n


def window(teams: list[str], index: int) -> tuple[str, str, str, str, str]:
    """(prev2, prev1, center, next1, next2) team names with wrap-around.
    Requires len >= 1. Index need not be in range (wraps)."""
    n = len(teams)
    return (
        teams[(index - 2) % n],
        teams[(index - 1) % n],
        teams[index % n],
        teams[(index + 1) % n],
        teams[(index + 2) % n],
    )


def center_team(teams: list[str], index: int) -> str:
    """Selected (centre) team for an index; index need not be in range (wraps)."""
    return teams[index % len(teams)]


def _logo_path(team: str) -> str:
    return f"{LOGO_DIR}/{team}.svg"


# A few teams display under a shorter / more familiar name than their raw FIFA
# name. Overrides win; otherwise "and" → "&" to save width (e.g. Bosnia).
_DISPLAY_OVERRIDES = {"Korea Republic": "South Korea"}


def display_name(team: str) -> str:
    """Human-friendly label for a team, used by the carousel and the group table."""
    if team in _DISPLAY_OVERRIDES:
        return _DISPLAY_OVERRIDES[team]
    return team.replace(" and ", " & ")


def carousel_view(teams: list[str], index: int, asset_url: Callable[[str], str]) -> dict[str, str]:
    """Compute the five visible logo srcs + center name for a given index (wrap-safe)."""
    prev2_t, prev1_t, center_t, next1_t, next2_t = window(teams, index)
    return {
        "prev2_src": asset_url(_logo_path(prev2_t)),
        "prev1_src": asset_url(_logo_path(prev1_t)),
        "center_src": asset_url(_logo_path(center_t)),
        "next1_src": asset_url(_logo_path(next1_t)),
        "next2_src": asset_url(_logo_path(next2_t)),
        "center_name": display_name(center_t),
    }


# Graduated sizes (px) give the carousel depth: inner neighbours larger than the
# outer ones; the centre logo is sized in build_team_carousel.
_NEAR_SIZE = 44
_FAR_SIZE = 30


def _side_button(
    button_id: str, img_id: str, src: str, *, size: int, variant: str
) -> dmc.UnstyledButton:
    # variant is "near" (1 away) or "far" (2 away); CSS dims each tier differently.
    return dmc.UnstyledButton(
        id=button_id,
        className=f"carousel-logo carousel-logo--side carousel-logo--{variant}",
        children=dmc.Image(id=img_id, src=src, h=size, w=size, fit="contain"),
    )


def build_team_carousel(teams: list[str], asset_url: Callable[[str], str], index: int = 0) -> dmc.Box:
    """Fixed carousel shell. Navigation/render callbacks (app.py) update the
    image srcs and center name; the clickable ids never change."""
    view = carousel_view(teams, index, asset_url)
    return dmc.Box(
        id="team-carousel",
        className="team-carousel",
        children=[
            dmc.ActionIcon(
                DashIconify(icon="radix-icons:chevron-left", width=22),
                id="carousel-prev",
                variant="subtle",
                size="lg",
                radius="xl",
            ),
            _side_button(
                "carousel-logo-prev2", "carousel-img-prev2", view["prev2_src"],
                size=_FAR_SIZE, variant="far",
            ),
            _side_button(
                "carousel-logo-prev", "carousel-img-prev", view["prev1_src"],
                size=_NEAR_SIZE, variant="near",
            ),
            dmc.UnstyledButton(
                id="carousel-logo-center",
                className="carousel-logo carousel-logo--center-wrap",
                children=dmc.Stack(
                    [
                        dmc.Image(
                            id="carousel-img-center",
                            className="carousel-logo--center",
                            src=view["center_src"],
                            h=56,
                            w=56,
                            fit="contain",
                        ),
                        dmc.Text(
                            view["center_name"],
                            id="carousel-name",
                            className="carousel-name",
                            fw=600,
                            size="sm",
                        ),
                    ],
                    gap=6,
                    align="center",
                ),
            ),
            _side_button(
                "carousel-logo-next", "carousel-img-next", view["next1_src"],
                size=_NEAR_SIZE, variant="near",
            ),
            _side_button(
                "carousel-logo-next2", "carousel-img-next2", view["next2_src"],
                size=_FAR_SIZE, variant="far",
            ),
            dmc.ActionIcon(
                DashIconify(icon="radix-icons:chevron-right", width=22),
                id="carousel-next",
                variant="subtle",
                size="lg",
                radius="xl",
            ),
        ],
    )
