from __future__ import annotations

import dash_mantine_components as dmc
from dash import html
from dash_iconify import DashIconify

from src.components.map_view import build_map
from src.data.host_cities import HostCity

DEFAULT_COLOR_SCHEME = "dark"

theme_toggle = dmc.Switch(
    id="color-scheme-toggle",
    offLabel=DashIconify(icon="radix-icons:sun", width=15),
    onLabel=DashIconify(icon="radix-icons:moon", width=15),
    checked=True,
    persistence=True,
    color="gray",
)


def build_layout(cities: list[HostCity]) -> dmc.MantineProvider:
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
        html.Div(build_map(cities), id="map-container")
    )

    shell = dmc.AppShell(
        [header, main],
        header={"height": 60},
        padding=0,
        id="appshell",
    )

    return dmc.MantineProvider(
        shell,
        id="mantine-provider",
        defaultColorScheme=DEFAULT_COLOR_SCHEME,
    )
