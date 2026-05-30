from __future__ import annotations

import dash_mantine_components as dmc
from dash import html
from dash_iconify import DashIconify

from src.components.map_view import build_map
from src.data.venues import Venue

DEFAULT_COLOR_SCHEME = "dark"

theme_toggle = dmc.Switch(
    id="color-scheme-toggle",
    offLabel=DashIconify(icon="radix-icons:sun", width=15),
    onLabel=DashIconify(icon="radix-icons:moon", width=15),
    checked=True,
    persistence=True,
    color="gray",
)


def build_layout(venues: list[Venue]) -> dmc.MantineProvider:
    header = dmc.AppShellHeader(
        dmc.Group(
            [
                dmc.Title("FIFA World Cup 2026", order=3),
                theme_toggle,
            ],
            justify="space-between",
            align="center",
            h="100%",
            px="md",
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
        position="right",
        size="md",
        padding="md",
        opened=False,
        withCloseButton=True,
    )

    return dmc.MantineProvider(
        [shell, drawer],
        id="mantine-provider",
        defaultColorScheme=DEFAULT_COLOR_SCHEME,
    )
