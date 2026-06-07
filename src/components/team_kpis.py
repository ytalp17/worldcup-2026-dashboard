from __future__ import annotations

import dash_mantine_components as dmc
from dash_iconify import DashIconify

from src.data.team_stats import TeamStats

PLACEHOLDER = "—"


def stat_card(icon, label, value=None, sub=None, ring=None) -> dmc.Box:
    """A small KPI card: icon + label on top, a big value (or a ring) below,
    and an optional dimmed sub-label."""
    head = dmc.Group(
        [
            DashIconify(icon=icon, width=14, className="stat-card__icon"),
            dmc.Text(label, size="xs", c="dimmed"),
        ],
        gap=5,
        wrap="nowrap",
        align="center",
    )
    body = ring if ring is not None else dmc.Text(
        value, className="stat-card__value", fw=700)
    children = [head, body]
    if sub:
        children.append(dmc.Text(sub, size="xs", c="dimmed",
                                 className="stat-card__sub"))
    return dmc.Box(children, className="stat-card")


def _foot_ring(stats: TeamStats) -> dmc.RingProgress:
    right = stats.foot_right_pct or 0
    label = (f"R {stats.foot_right_pct}%"
             if stats.foot_right_pct is not None else PLACEHOLDER)
    return dmc.RingProgress(
        size=48,
        thickness=5,
        roundCaps=True,
        sections=[{"value": right, "color": "teal"}],
        label=dmc.Text(label, ta="center", size="10px", fw=700),
    )


def kpi_cards(stats: TeamStats) -> list[dmc.Box]:
    """The seven KPI cards for a team. Avg age/height/value/foot are computed;
    FIFA rank, Abroad and Manager are placeholders until data is added."""
    age = f"{stats.avg_age:.1f}" if stats.avg_age is not None else PLACEHOLDER
    height = (f"{stats.avg_height:.2f}"
              if stats.avg_height is not None else PLACEHOLDER)
    rank = f"#{stats.fifa_rank}" if stats.fifa_rank is not None else PLACEHOLDER
    abroad = (f"{stats.abroad} of {stats.squad_size}"
              if stats.abroad is not None else PLACEHOLDER)
    foot_sub = (f"L {stats.foot_left_pct}%"
                if stats.foot_left_pct is not None else None)

    return [
        stat_card("tabler:calendar", "Avg age", age, sub="years"),
        stat_card("tabler:ruler-2", "Avg height", height, sub="metres"),
        stat_card("tabler:trophy", "FIFA rank", rank, sub="world"),
        stat_card("tabler:coin", "Value", stats.value_display, sub="total"),
        stat_card("tabler:plane", "Abroad", abroad,
                  sub=f"of {stats.squad_size}" if stats.squad_size else None),
        stat_card("tabler:shoe", "Foot", sub=foot_sub, ring=_foot_ring(stats)),
        stat_card("tabler:user-star", "Manager", stats.manager or PLACEHOLDER,
                  sub="head coach"),
    ]


def build_kpi_strip(stats: TeamStats) -> dmc.Box:
    return dmc.Box(kpi_cards(stats), id="kpi-strip", className="kpi-strip")
