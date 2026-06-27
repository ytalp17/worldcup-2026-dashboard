from __future__ import annotations

import dash_mantine_components as dmc
from dash import dcc, html
from dash_iconify import DashIconify

from src.components.analysis.panel import build_analysis_panel
from src.components.filter_panel import build_filter_drawer
from src.components.live_match_modal import build_modal
from src.components.live_strip import build_live_strip
from src.components.map_view import build_map, build_map_controls
from src.components.mode_switch import mode_switch
from src.components.tournament_stats import build_tournament_drawer
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
    formation_panel=None,
    kpi_strip=None,
    leaders_panel=None,
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

    # Team mode lays the main area out as a team dashboard: a full-width KPI
    # strip on top, then Leaders + group Table, the estimated-XI pitch and a
    # small host-cities map, with the Squad as the tall right column. Time mode
    # collapses everything except the map card, which fills the screen. A
    # clientside callback adds the `main-split--team` modifier in Team mode (CSS
    # swaps the grid template); the map keeps `bento-card--map` so the Time-mode
    # hide rule leaves it visible.
    map_card = dmc.Box(
        [
            html.Div(build_map(venues), id="map-container"),
            build_analysis_panel(),
        ],
        className="bento-card bento-card--map",
    )
    table_card = dmc.Box(group_panel, className="bento-card bento-card--table")
    squad_card = dmc.Box(squad_panel, className="bento-card bento-card--squad")
    formation_card = dmc.Box(formation_panel, className="bento-card bento-card--formation")
    leaders_card = dmc.Box(leaders_panel, className="bento-card bento-card--leaders")
    main = dmc.AppShellMain(
        dmc.Box(
            [kpi_strip, leaders_card, table_card, formation_card, map_card, squad_card],
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

    filter_drawer = build_filter_drawer(team_flows or {}, asset_url)

    return dmc.MantineProvider(
        [
            shell,
            drawer,
            filter_drawer,
            build_tournament_drawer(),
            build_map_controls(),
            build_live_strip(),
            build_modal(),
            dcc.Store(id="carousel-index", data=0, storage_type="local"),
            dcc.Store(id="user-tz"),
            dcc.Store(id="unit-store"),  # journey-grid distance unit (km/mi)
            dcc.Store(id="journey-redraw"),  # ping target for the selection redraw
            dcc.Store(id="live-store", data={"ok": False, "any_live": False, "matches": [], "standings": {}}),
            dcc.Interval(id="tz-probe", interval=100, max_intervals=1),  # one-shot: fire once just after load to read the browser timezone
        ],
        id="mantine-provider",
        defaultColorScheme=DEFAULT_COLOR_SCHEME,
    )
