from __future__ import annotations

import dash_mantine_components as dmc
from dash_iconify import DashIconify

from src.data.team_form import DRAW, LOSS, WIN
from src.data.team_stats import TeamStats

PLACEHOLDER = "—"
FORM_SLOTS = 5

# Result -> (dot modifier class, glyph). Colours live in CSS and reuse the exact
# qualification green / elimination red from the group table for coherence.
_FORM_DOT = {
    WIN: ("form-dot--w", "✓"),
    DRAW: ("form-dot--d", "–"),
    LOSS: ("form-dot--l", "✕"),
}


def _head(icon, label, tip=None):
    """Card header: icon + label. When ``tip`` is given, the header is wrapped in
    a multiline tooltip explaining the stat (matching the app's tooltip style)."""
    head = dmc.Group(
        [
            DashIconify(icon=icon, width=14, className="stat-card__icon"),
            dmc.Text(label, size="xs", c="dimmed"),
        ],
        gap=5,
        wrap="nowrap",
        align="center",
    )
    if tip:
        return dmc.Tooltip(head, label=tip, position="top", withArrow=True,
                           multiline=True, w=220)
    return head


def stat_card(icon, label, value=None, sub=None, ring=None, sub_node=None,
              body_node=None, tip=None, class_name=None) -> dmc.Box:
    """A small KPI card: icon + label on top, a big value (or a ring/custom body)
    below, and an optional dimmed sub-label. ``body_node``/``ring`` replace the
    text value; ``sub_node`` takes precedence over plain-text ``sub`` for richer
    footers. ``tip`` adds a header tooltip explaining the stat. ``class_name``
    appends a width modifier (e.g. ``stat-card--narrow``) to the base class."""
    if body_node is not None:
        body = body_node
    elif ring is not None:
        body = ring
    else:
        body = dmc.Text(value, className="stat-card__value", fw=700)
    children = [_head(icon, label, tip), body]
    if sub_node is not None:
        children.append(sub_node)
    elif sub:
        children.append(dmc.Text(sub, size="xs", c="dimmed",
                                 className="stat-card__sub"))
    cls = f"stat-card {class_name}" if class_name else "stat-card"
    return dmc.Box(children, className=cls)


def _form_dots(form, slots=FORM_SLOTS) -> dmc.Group:
    """A row of result dots: one per played match (oldest → newest), padded with
    hollow slots up to ``slots`` for matches not yet played."""
    dots = []
    for i in range(slots):
        result = form[i] if i < len(form) else None
        cls, glyph = _FORM_DOT.get(result, ("form-dot--empty", ""))
        dots.append(dmc.Box(glyph, className=f"form-dot {cls}"))
    return dmc.Group(dots, gap=5, wrap="nowrap", align="center",
                     className="stat-card__form")


def _form_card(form) -> dmc.Box:
    """Recent-form card: a row of W/D/L dots for this tournament's matches."""
    return stat_card(
        "tabler:activity-heartbeat", "Form", body_node=_form_dots(form),
        tip="Results in this tournament so far, oldest to most recent (right). "
            "Green = win, grey = draw, red = loss; hollow = not played yet.",
        class_name="stat-card--form",
    )


def _federation_card(stats: TeamStats) -> dmc.Box:
    """Federation card: label + confederation code on the left, the
    confederation logo anchored to the right end of the card."""
    code = stats.confederation or PLACEHOLDER
    left_children = [_head("tabler:shield", "Federation",
                          tip="The continental football federation the team "
                              "belongs to."),
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


def kpi_cards(stats: TeamStats, form=()) -> list[dmc.Box]:
    """The eight KPI cards for a team. Avg age/height/value/foot are computed;
    FIFA rank, Federation and Manager come from teams.csv; Form is the team's
    recent W/D/L in this tournament (``form`` is a list of "W"/"D"/"L", oldest
    first). The five computed/rank cards carry ``stat-card--narrow`` so the wider
    Form card gets its room without shrinking Federation or Manager."""
    age = f"{stats.avg_age:.1f}" if stats.avg_age is not None else PLACEHOLDER
    height = (f"{stats.avg_height:.2f}"
              if stats.avg_height is not None else PLACEHOLDER)
    rank = f"#{stats.fifa_rank}" if stats.fifa_rank is not None else PLACEHOLDER
    return [
        stat_card("tabler:coin", "Value", stats.value_display, sub="total",
                  tip="Estimated total market value of the squad.",
                  class_name="stat-card--narrow"),
        stat_card("tabler:calendar", "Avg age", age, sub="years",
                  tip="Average age of the squad.",
                  class_name="stat-card--narrow"),
        stat_card("tabler:ruler-2", "Avg height", height, sub="metres",
                  tip="Average height of the squad.",
                  class_name="stat-card--narrow"),
        stat_card("tabler:shoe", "Foot Preference", body_node=_foot_bar(stats),
                  sub_node=_foot_sub(stats),
                  tip="Share of the squad that is left- vs right-footed.",
                  class_name="stat-card--narrow"),
        stat_card("tabler:trophy", "FIFA rank", rank, sub="world",
                  tip="The team's current FIFA world ranking.",
                  class_name="stat-card--narrow"),
        _form_card(form),
        _federation_card(stats),
        stat_card("tabler:user-star", "Manager", stats.manager or PLACEHOLDER,
                  sub="head coach", sub_node=_manager_sub(stats),
                  tip="The team's current head coach."),
    ]


def build_kpi_strip(stats: TeamStats, form=()) -> dmc.Box:
    return dmc.Box(kpi_cards(stats, form), id="kpi-strip", className="kpi-strip")
