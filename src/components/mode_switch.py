from __future__ import annotations

import dash_mantine_components as dmc
from dash_iconify import DashIconify

MODE_SWITCH_ID = "mode-toggle"

# Unchecked = Time (calendar); checked = Team (carousel).
mode_switch = dmc.Switch(
    id=MODE_SWITCH_ID,
    offLabel=DashIconify(icon="radix-icons:calendar", width=15),
    onLabel=DashIconify(icon="mdi:account-group", width=15),
    checked=False,
    persistence=True,
    color="gray",
)
