from __future__ import annotations

import dash_mantine_components as dmc

from src.data.flows import TeamFlow, format_distance, rank_by_distance


def _leaderboard_section(title: str, flows: list[TeamFlow]) -> dmc.Card:
    rows = [
        dmc.Group(
            [
                dmc.Box(
                    w=10,
                    h=10,
                    style={
                        "background": f.color,
                        "borderRadius": "50%",
                        "flex": "0 0 auto",
                    },
                ),
                dmc.Text(f"{f.team} — {format_distance(f.distance_km)}", size="xs"),
            ],
            gap="xs",
            align="center",
        )
        for f in flows
    ]
    return dmc.Card(
        children=dmc.Stack(
            [dmc.Text(title, size="sm", fw=600), *rows],
            gap=4,
        ),
        withBorder=True,
        radius="md",
        shadow="sm",
        padding="sm",
    )


def _leaderboard(team_flows: dict[str, TeamFlow]) -> dmc.Stack:
    longest, shortest = rank_by_distance(team_flows, n=5)
    return dmc.Stack(
        [
            _leaderboard_section("Longest journeys", longest),
            _leaderboard_section("Shortest journeys", shortest),
        ],
        gap="md",
        mt="lg",
    )


def build_filter_drawer(
    options: list[dict], team_flows: dict | None = None
) -> dmc.Drawer:
    children = [
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
    ]
    if team_flows:
        children.append(dmc.Divider(my="md"))
        children.append(_leaderboard(team_flows))
    return dmc.Drawer(
        id="filter-drawer",
        title="Flow lines by team",
        position="right",
        size="md",
        padding="md",
        opened=False,
        withCloseButton=True,
        withOverlay=False,
        lockScroll=False,
        zIndex=2500,
        # Frosted-glass panel: translucent + blurred so the map shows through
        # while the leaderboard/legend text stays legible (see assets/styles.css).
        classNames={
            "content": "filter-drawer-frosted",
            "header": "filter-drawer-frosted-header",
        },
        children=children,
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
                    dmc.Text(
                        f"{team} — {format_distance(flow.distance_km)}", size="sm"
                    ),
                ],
                gap="xs",
                align="center",
            )
        )
    return rows
