from __future__ import annotations

import dash_mantine_components as dmc
from dash import dcc, html
from dash_iconify import DashIconify

from src.components.analysis import views
from src.data.analysis.accessors import RACE_METRICS

# No modebar / graph preferences: hide the Plotly toolbar entirely so the
# tile shows only the chart. The graph stays responsive to its container.
_GRAPH_CONFIG = {
    "displayModeBar": False,
    "responsive": True,
}


def dots(active: int, total: int):
    pips = [html.Span(className="analysis-dot" + (" is-active" if i == active else ""))
            for i in range(total)]
    return [html.Div(pips, className="analysis-dots-row"),
            dmc.Text(f"{active + 1} / {total}", size="xs", c="dimmed")]


def empty_state(group_name: str) -> dmc.Stack:
    return dmc.Stack(
        [DashIconify(icon="mdi:chart-box-outline", width=42),
         dmc.Text(f"No completed matches yet for {group_name}", c="dimmed")],
        align="center", justify="center", className="analysis-empty")


def _arrow(id_, icon, label):
    return dmc.ActionIcon(DashIconify(icon=icon, width=22), id=id_,
                          variant="subtle", size="lg", radius="xl",
                          **{"aria-label": label})


def _race_controls():
    return dmc.Group(
        [dmc.Select(id="analysis-race-metric",
                    data=[{"value": v, "label": l} for v, l in RACE_METRICS.items()],
                    value="points", size="xs", w=170, allowDeselect=False),
         dmc.Button("Replay", id="analysis-race-replay", size="xs",
                    variant="light", leftSection=DashIconify(icon="mdi:replay"))],
        id="analysis-race-controls", gap="xs", style={"display": "none"})


def _expand_button():
    # size "xs" keeps the icon no taller than the sm header text, so the header
    # height matches the other bento cards exactly (md/sm inflated it).
    return dmc.ActionIcon(
        DashIconify(icon="mdi:arrow-expand-all", width=14),
        id="analysis-expand", variant="subtle", size="xs", radius="xl",
        **{"aria-label": "Expand chart"})


def info_content(view: dict, caveat: str | None = None) -> dmc.Stack:
    """Rich explanatory block shown inside the header info hover-card: the chart
    title, its one-line caption, a longer 'how to read it' note, and any caveat
    (a `caveat` argument overrides the view's default — used for the goals-
    conceded race, where lower is better)."""
    cav = view.get("caveat", "") if caveat is None else caveat
    parts = [
        dmc.Text(view["title"], fw=700, size="sm"),
        dmc.Text(view["caption"], size="xs", c="dimmed"),
    ]
    if view.get("info"):
        parts.append(dmc.Text(view["info"], size="xs"))
    if cav:
        parts.append(dmc.Group(
            [DashIconify(icon="mdi:alert-outline", width=15),
             dmc.Text(cav, size="xs")],
            gap=6, align="flex-start", wrap="nowrap",
            className="analysis-info-caveat"))
    return dmc.Stack(parts, gap=8)


def _info_hovercard():
    # Small "i" in the header; on hover a card explains the current chart. The
    # dropdown body is filled per-view by the render callback. `bottom-end`
    # anchors to the icon's right edge so the card never overflows off-screen.
    return dmc.HoverCard(
        withArrow=True, shadow="md", position="bottom-end", width=270,
        openDelay=120, closeDelay=80,
        children=[
            dmc.HoverCardTarget(
                dmc.ActionIcon(
                    DashIconify(icon="mdi:information-outline", width=14),
                    id="analysis-info", variant="subtle", size="xs", radius="xl",
                    **{"aria-label": "About this chart"})),
            dmc.HoverCardDropdown(
                html.Div(info_content(views.VIEWS[0]), id="analysis-info-content"),
                className="analysis-info-dropdown"),
        ])


def _expanded_modal():
    """A large centered modal mirroring the current chart for a roomier view.
    Carries its own carousel arrows + position dots, wired to the same view
    index, so the user can browse the rest of the charts while expanded."""
    return dmc.Modal(
        id="analysis-modal", title="", size="92%", centered=True,
        children=[
            html.Div(
                [_arrow("analysis-modal-prev", "mdi:chevron-left", "Previous chart"),
                 dcc.Graph(id="analysis-modal-graph", config=_GRAPH_CONFIG,
                           style={"height": "74vh", "width": "100%"}),
                 _arrow("analysis-modal-next", "mdi:chevron-right", "Next chart")],
                className="analysis-modal-stage"),
            dmc.Group(dots(0, len(views.VIEWS)), id="analysis-modal-dots",
                      justify="center", gap="xs", className="analysis-dots"),
        ])


def build_analysis_panel() -> dmc.Box:
    return dmc.Box(
        [
            dcc.Store(id="analysis-view-index", data=0),
            dcc.Store(id="analysis-race-frame", data=0),
            dcc.Interval(id="analysis-race-interval", interval=900, disabled=True),
            _expanded_modal(),
            # Same header idiom as every other bento card: bold label left,
            # dimmed context (the view title) right, under the shared divider.
            dmc.Group(
                [
                    dmc.Text("Group Analysis", fw=700, size="sm"),
                    dmc.Group(
                        # The per-view chart title now lives in the info hover-card
                        # (and the expanded-modal title), so the header stays clean.
                        [_race_controls(), _info_hovercard(), _expand_button()],
                        gap="xs", align="center", wrap="nowrap"),
                ],
                justify="space-between", align="center", wrap="nowrap",
                className="bento-card__header analysis-header"),
            # No caption/caveat text rows: that copy now lives behind the header
            # info icon, leaving the whole body to the figure.
            html.Div(
                [_arrow("analysis-prev", "mdi:chevron-left", "Previous chart"),
                 dcc.Graph(id="analysis-graph", config=_GRAPH_CONFIG,
                           className="analysis-graph",
                           style={"height": "100%", "width": "100%"}),
                 _arrow("analysis-next", "mdi:chevron-right", "Next chart")],
                className="analysis-stage"),
            dmc.Group(dots(0, len(views.VIEWS)), id="analysis-dots",
                      justify="center", gap="xs", className="analysis-dots"),
        ],
        id="analysis-panel", className="analysis-panel")
