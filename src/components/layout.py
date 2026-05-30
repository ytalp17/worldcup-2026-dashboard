from __future__ import annotations

import dash_mantine_components as dmc
from dash import html
from dash_iconify import DashIconify

from src.components.filter_panel import build_filter_drawer
from src.components.map_view import build_map
from src.data.venues import Venue

DEFAULT_COLOR_SCHEME = "dark"

# Leaflet map panes and controls use z-indexes up to ~1000; the drawer must
# render above them so it is actually visible over the map.
DRAWER_Z_INDEX = 2000

LOGO_BLACK = "/assets/logos/fifa_logo_black.cc.svg"
LOGO_WHITE = "/assets/logos/fifa_logo_white.cc.svg"
LOGO_HEIGHT = 34


def _brand() -> dmc.Group:
    return dmc.Group(
        [
            # Contrast-aware: black logo in light mode, white logo in dark mode.
            dmc.Image(src=LOGO_BLACK, h=LOGO_HEIGHT, w="auto", alt="FIFA", darkHidden=True),
            dmc.Image(src=LOGO_WHITE, h=LOGO_HEIGHT, w="auto", alt="FIFA", lightHidden=True),
            dmc.Title("FIFA World Cup 2026", order=3),
        ],
        gap="sm",
        align="center",
        wrap="nowrap",
    )

theme_toggle = dmc.Switch(
    id="color-scheme-toggle",
    offLabel=DashIconify(icon="radix-icons:sun", width=15),
    onLabel=DashIconify(icon="radix-icons:moon", width=15),
    checked=True,
    persistence=True,
    color="gray",
)


def build_layout(
    venues: list[Venue],
    team_options: list | None = None,
    team_flows: dict | None = None,
    match_calendar=None,
) -> dmc.MantineProvider:
    # Three equal-flex zones so the calendar sits at the true centre of the
    # header regardless of the brand / toggle widths: left and right grow
    # equally and push the centre to the middle.
    left = dmc.Box(_brand(), style={"flex": "1 1 0", "display": "flex", "justifyContent": "flex-start"})
    center = dmc.Box(
        match_calendar,
        style={"flex": "0 0 auto", "display": "flex", "justifyContent": "center"},
    )
    right = dmc.Box(theme_toggle, style={"flex": "1 1 0", "display": "flex", "justifyContent": "flex-end"})
    header = dmc.AppShellHeader(
        dmc.Group(
            [left, center, right],
            justify="space-between",
            align="center",
            h="100%",
            px="md",
            wrap="nowrap",
            gap="sm",
        )
    )

    main = dmc.AppShellMain(
        html.Div(build_map(venues), id="map-container")
    )

    shell = dmc.AppShell(
        [header, main],
        header={"height": 60},
        padding=0,
        id="appshell",
    )

    # Stadium detail drawer; its title/children/opened are filled by the
    # marker-click callback in app.py.
    drawer = dmc.Drawer(
        id="stadium-drawer",
        position="left",
        size="md",
        padding="md",
        opened=False,
        withCloseButton=True,
        zIndex=DRAWER_Z_INDEX,
    )

    filter_drawer = build_filter_drawer(team_options or [], team_flows or {})

    return dmc.MantineProvider(
        [shell, drawer, filter_drawer],
        id="mantine-provider",
        defaultColorScheme=DEFAULT_COLOR_SCHEME,
    )
