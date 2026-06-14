from __future__ import annotations

import dash_mantine_components as dmc
from dash_iconify import DashIconify

from src.data.team_stats import TeamStats

PLACEHOLDER = "—"


def stat_card(icon, label, value=None, sub=None, ring=None, sub_node=None,
              body_node=None) -> dmc.Box:
    """A small KPI card: icon + label on top, a big value (or a ring/logo) below,
    and an optional dimmed sub-label. ``body_node`` (e.g. a logo) and ``ring``
    replace the text value; ``sub_node`` takes precedence over plain-text ``sub``
    for richer footers (e.g. a flag + country)."""
    head = dmc.Group(
        [
            DashIconify(icon=icon, width=14, className="stat-card__icon"),
            dmc.Text(label, size="xs", c="dimmed"),
        ],
        gap=5,
        wrap="nowrap",
        align="center",
    )
    if body_node is not None:
        body = body_node
    elif ring is not None:
        body = ring
    else:
        body = dmc.Text(value, className="stat-card__value", fw=700)
    children = [head, body]
    if sub_node is not None:
        children.append(sub_node)
    elif sub:
        children.append(dmc.Text(sub, size="xs", c="dimmed",
                                 className="stat-card__sub"))
    return dmc.Box(children, className="stat-card")


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


def _federation_body(stats: TeamStats):
    """Confederation logo for the Federation card, or None to fall back to the
    confederation code as plain text."""
    if not stats.confederation_logo:
        return None
    return dmc.Image(src=stats.confederation_logo, h=30, fit="contain",
                     className="stat-card__logo")


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
    FIFA rank, Federation and Manager come from teams.csv."""
    age = f"{stats.avg_age:.1f}" if stats.avg_age is not None else PLACEHOLDER
    height = (f"{stats.avg_height:.2f}"
              if stats.avg_height is not None else PLACEHOLDER)
    rank = f"#{stats.fifa_rank}" if stats.fifa_rank is not None else PLACEHOLDER
    foot_sub = (f"L {stats.foot_left_pct}%"
                if stats.foot_left_pct is not None else None)
    fed_logo = _federation_body(stats)

    return [
        stat_card("tabler:calendar", "Avg age", age, sub="years"),
        stat_card("tabler:ruler-2", "Avg height", height, sub="metres"),
        stat_card("tabler:trophy", "FIFA rank", rank, sub="world"),
        stat_card("tabler:coin", "Value", stats.value_display, sub="total"),
        stat_card("tabler:shield", "Federation",
                  value=None if fed_logo else (stats.confederation or PLACEHOLDER),
                  sub=stats.confederation, body_node=fed_logo),
        stat_card("tabler:shoe", "Foot", sub=foot_sub, ring=_foot_ring(stats)),
        stat_card("tabler:user-star", "Manager", stats.manager or PLACEHOLDER,
                  sub="head coach", sub_node=_manager_sub(stats)),
    ]


def build_kpi_strip(stats: TeamStats) -> dmc.Box:
    return dmc.Box(kpi_cards(stats), id="kpi-strip", className="kpi-strip")
