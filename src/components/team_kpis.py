from __future__ import annotations

import dash_mantine_components as dmc
from dash_iconify import DashIconify

from src.data.team_stats import TeamStats

PLACEHOLDER = "—"


def _head(icon, label) -> dmc.Group:
    return dmc.Group(
        [
            DashIconify(icon=icon, width=14, className="stat-card__icon"),
            dmc.Text(label, size="xs", c="dimmed"),
        ],
        gap=5,
        wrap="nowrap",
        align="center",
    )


def stat_card(icon, label, value=None, sub=None, ring=None, sub_node=None,
              body_node=None) -> dmc.Box:
    """A small KPI card: icon + label on top, a big value (or a ring/custom body)
    below, and an optional dimmed sub-label. ``body_node``/``ring`` replace the
    text value; ``sub_node`` takes precedence over plain-text ``sub`` for richer
    footers."""
    if body_node is not None:
        body = body_node
    elif ring is not None:
        body = ring
    else:
        body = dmc.Text(value, className="stat-card__value", fw=700)
    children = [_head(icon, label), body]
    if sub_node is not None:
        children.append(sub_node)
    elif sub:
        children.append(dmc.Text(sub, size="xs", c="dimmed",
                                 className="stat-card__sub"))
    return dmc.Box(children, className="stat-card")


def _federation_card(stats: TeamStats) -> dmc.Box:
    """Federation card: label + confederation code on the left, the
    confederation logo anchored to the right end of the card."""
    code = stats.confederation or PLACEHOLDER
    left_children = [_head("tabler:shield", "Federation"),
                     dmc.Text(code, fw=700, className="stat-card__fedcode")]
    if stats.confederation_region:
        left_children.append(dmc.Text(stats.confederation_region, size="xs",
                                      c="dimmed", className="stat-card__sub"))
    left = dmc.Box(left_children, className="stat-card__fedtext")
    row = [left]
    if stats.confederation_logo:
        row.append(dmc.Image(src=stats.confederation_logo, fit="contain",
                             className="stat-card__fedlogo"))
    return dmc.Box(
        dmc.Group(row, justify="space-between", wrap="nowrap", align="center",
                  className="stat-card__fedrow"),
        className="stat-card",
    )


def _manager_sub(stats: TeamStats):
    """Footer for the manager card: nationality flag + country and age when
    known, else None (so stat_card falls back to the plain 'head coach' label)."""
    if not stats.manager_nationality and stats.manager_age is None:
        return None
    label = stats.manager_nationality or ""
    if stats.manager_age is not None:
        age = f"{stats.manager_age} yrs"
        label = f"{label} · {age}" if label else age
    parts = []
    if stats.manager_flag:
        parts.append(dmc.Image(src=stats.manager_flag, w=18, h=12, fit="contain",
                               className="stat-card__flag"))
    parts.append(dmc.Text(label, size="xs", c="dimmed",
                          className="stat-card__sub"))
    return dmc.Group(parts, gap=4, wrap="nowrap", align="center")


def _foot_bar(stats: TeamStats) -> dmc.Box:
    """A single split bar: left-foot share (orange) + right-foot share (teal)."""
    left = stats.foot_left_pct or 0
    right = stats.foot_right_pct or 0
    return dmc.Box(
        [
            dmc.Box(style={"width": f"{left}%",
                           "background": "var(--mantine-color-orange-5)"}),
            dmc.Box(style={"width": f"{right}%",
                           "background": "var(--mantine-color-teal-5)"}),
        ],
        className="stat-card__footbar",
    )


def _foot_sub(stats: TeamStats):
    """Left and right foot percentages on a single line, or None when unknown."""
    left, right = stats.foot_left_pct, stats.foot_right_pct
    if left is None and right is None:
        return None
    fmt = lambda v: f"{v}%" if v is not None else PLACEHOLDER
    return dmc.Group(
        [
            dmc.Text(f"L {fmt(left)}", size="xs", c="dimmed"),
            dmc.Text(f"R {fmt(right)}", size="xs", c="dimmed"),
        ],
        gap=10,
        wrap="nowrap",
        justify="space-between",
        className="stat-card__sub",
    )


def kpi_cards(stats: TeamStats) -> list[dmc.Box]:
    """The seven KPI cards for a team. Avg age/height/value/foot are computed;
    FIFA rank, Federation and Manager come from teams.csv."""
    age = f"{stats.avg_age:.1f}" if stats.avg_age is not None else PLACEHOLDER
    height = (f"{stats.avg_height:.2f}"
              if stats.avg_height is not None else PLACEHOLDER)
    rank = f"#{stats.fifa_rank}" if stats.fifa_rank is not None else PLACEHOLDER
    return [
        stat_card("tabler:calendar", "Avg age", age, sub="years"),
        stat_card("tabler:ruler-2", "Avg height", height, sub="metres"),
        stat_card("tabler:trophy", "FIFA rank", rank, sub="world"),
        stat_card("tabler:coin", "Value", stats.value_display, sub="total"),
        _federation_card(stats),
        stat_card("tabler:shoe", "Foot", body_node=_foot_bar(stats),
                  sub_node=_foot_sub(stats)),
        stat_card("tabler:user-star", "Manager", stats.manager or PLACEHOLDER,
                  sub="head coach", sub_node=_manager_sub(stats)),
    ]


def build_kpi_strip(stats: TeamStats) -> dmc.Box:
    return dmc.Box(kpi_cards(stats), id="kpi-strip", className="kpi-strip")
