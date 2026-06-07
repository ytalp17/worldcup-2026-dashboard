from __future__ import annotations

import dash_mantine_components as dmc
from dash_iconify import DashIconify


def build_leaders_card() -> dmc.Box:
    """Tournament leaders card. Placeholder until matches start (Jun 11):
    a Goals/Assists/Cards segmented control over an empty state."""
    header = dmc.Group(
        [
            dmc.Text("Leaders", fw=700, size="sm"),
            dmc.Text("tournament", size="sm", c="dimmed"),
        ],
        justify="space-between",
        align="center",
        wrap="nowrap",
        className="bento-card__header",
    )

    tabs = dmc.SegmentedControl(
        id="leaders-tabs",
        value="Goals",
        data=["Goals", "Assists", "Cards"],
        size="xs",
        fullWidth=True,
    )

    empty = dmc.Stack(
        [
            DashIconify(icon="tabler:clock-hour-4", width=22,
                        className="leaders-empty__icon"),
            dmc.Text("Fills in once matches start (Jun 11)",
                     size="sm", c="dimmed", ta="center"),
        ],
        align="center",
        justify="center",
        gap=8,
        className="leaders-empty",
    )

    body = dmc.Box([tabs, empty], className="leaders-panel__body")
    return dmc.Box([header, body], className="leaders-panel")
