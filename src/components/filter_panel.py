from __future__ import annotations

import dash_mantine_components as dmc

from src.data.flows import TeamFlow


def build_filter_drawer(options: list[dict]) -> dmc.Drawer:
    return dmc.Drawer(
        id="filter-drawer",
        title="Flow lines by team",
        position="left",
        size="md",
        padding="md",
        opened=False,
        withCloseButton=True,
        withOverlay=False,
        lockScroll=False,
        zIndex=2500,
        children=[
            dmc.MultiSelect(
                id="team-filter",
                data=options,
                searchable=True,
                clearable=True,
                placeholder="Select teams…",
                maxDropdownHeight=320,
                # Float the dropdown above the drawer (zIndex 2500); otherwise the
                # drawer paints over the options and intercepts clicks.
                comboboxProps={"zIndex": 3000},
            ),
            dmc.Stack(id="filter-legend", gap="xs", mt="md"),
        ],
    )


def legend(selected, team_flows: dict[str, TeamFlow]) -> list:
    rows: list = []
    for team in selected or []:
        flow = team_flows.get(team)
        if flow is None:
            continue
        rows.append(
            dmc.Group(
                [
                    dmc.Box(
                        w=12,
                        h=12,
                        style={
                            "background": flow.color,
                            "borderRadius": "50%",
                            "flex": "0 0 auto",
                        },
                    ),
                    dmc.Text(team, size="sm"),
                ],
                gap="xs",
                align="center",
            )
        )
    return rows
