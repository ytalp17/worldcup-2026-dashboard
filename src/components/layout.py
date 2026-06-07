from __future__ import annotations

import dash_mantine_components as dmc
from dash import dcc, html
from dash_iconify import DashIconify

from src.components.filter_panel import build_filter_drawer
from src.components.map_view import build_map
from src.components.mode_switch import mode_switch
from src.data.venues import Venue

DEFAULT_COLOR_SCHEME = "dark"

# Leaflet map panes and controls use z-indexes up to ~1000; the drawer must
# render above them so it is actually visible over the map.
DRAWER_Z_INDEX = 2000

LOGO_BLACK = "/assets/logos/fifa_logo_black.cc.svg"
LOGO_WHITE = "/assets/logos/fifa_logo_white.cc.svg"
LOGO_HEIGHT = 46


def _brand() -> dmc.Group:
    return dmc.Group(
        [
            # Contrast-aware: black logo in light mode, white logo in dark mode.
            dmc.Image(src=LOGO_BLACK, h=LOGO_HEIGHT, w="auto", alt="FIFA", darkHidden=True),
            dmc.Image(src=LOGO_WHITE, h=LOGO_HEIGHT, w="auto", alt="FIFA", lightHidden=True),
            dmc.Title("FIFA World Cup 2026", order=2),
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
    team_carousel=None,
    group_panel=None,
    squad_panel=None,
    asset_url=None,
) -> dmc.MantineProvider:
    # Three equal-flex zones so the centre widget sits at the true centre of the
    # header regardless of the brand / controls widths.
    left = dmc.Box(
        _brand(),
        style={"flex": "1 1 0", "display": "flex", "justifyContent": "flex-start"},
    )
    # Both centre widgets are always mounted; a callback toggles their display.
    calendar_wrapper = dmc.Box(match_calendar, id="calendar-wrapper")
    carousel_wrapper = dmc.Box(
        team_carousel, id="carousel-wrapper", style={"display": "none"}
    )
    center = dmc.Box(
        [calendar_wrapper, carousel_wrapper],
        style={"flex": "0 0 auto", "display": "flex", "justifyContent": "center"},
    )
    right = dmc.Box(
        dmc.Stack([mode_switch, theme_toggle], gap="xs", align="flex-end"),
        style={"flex": "1 1 0", "display": "flex", "justifyContent": "flex-end"},
    )
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

    # Team mode reveals a left-side standings panel; the map fills the rest.
    # Team mode lays the main area out as a bento grid of cards (map hero +
    # group table + empty placeholders to fill later); Time mode collapses the
    # grid so the map card fills the screen. A clientside callback adds the
    # `main-split--team` modifier in Team mode (CSS swaps the grid template).
    map_card = dmc.Box(
        html.Div(build_map(venues), id="map-container"),
        className="bento-card bento-card--map",
    )
    table_card = dmc.Box(group_panel, className="bento-card bento-card--table")
    squad_card = dmc.Box(squad_panel, className="bento-card bento-card--squad")
    # Four uniform (single-cell) empty cards the user fills with future
    # infographics, one by one — the squad card now fills the right strip.
    empty_cards = [
        dmc.Box(className="bento-card bento-card--empty", id=f"bento-e{i}")
        for i in range(1, 5)
    ]
    main = dmc.AppShellMain(
        dmc.Box(
            [map_card, table_card, squad_card, *empty_cards],
            id="main-split",
            className="main-split",
        )
    )

    shell = dmc.AppShell(
        [header, main],
        header={"height": 95},
        padding=0,
        id="appshell",
    )

    drawer = dmc.Drawer(
        id="stadium-drawer",
        position="left",
        size="md",
        padding="md",
        opened=False,
        withCloseButton=True,
        zIndex=DRAWER_Z_INDEX,
    )

    filter_drawer = build_filter_drawer(team_options or [], team_flows or {}, asset_url)

    return dmc.MantineProvider(
        [
            shell,
            drawer,
            filter_drawer,
            dcc.Store(id="carousel-index", data=0, storage_type="local"),
            dcc.Store(id="user-tz"),
            dcc.Interval(id="tz-probe", interval=100, max_intervals=1),  # one-shot: fire once just after load to read the browser timezone
        ],
        id="mantine-provider",
        defaultColorScheme=DEFAULT_COLOR_SCHEME,
    )
