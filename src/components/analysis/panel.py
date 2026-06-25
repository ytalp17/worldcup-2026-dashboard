from __future__ import annotations

import dash_mantine_components as dmc
from dash import dcc, html
from dash_iconify import DashIconify

from src.components.analysis import views
from src.data.analysis.accessors import RACE_METRICS

_GRAPH_CONFIG = {
    "displaylogo": False,
    "displayModeBar": True,
    "modeBarButtonsToRemove": ["select2d", "lasso2d", "autoScale2d",
                               "zoomIn2d", "zoomOut2d", "toggleSpikelines"],
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


def build_analysis_panel() -> dmc.Box:
    return dmc.Box(
        [
            dcc.Store(id="analysis-view-index", data=0),
            dcc.Store(id="analysis-race-frame", data=0),
            dcc.Interval(id="analysis-race-interval", interval=900, disabled=True),
            dmc.Group(
                [dmc.Title(id="analysis-title", order=5),
                 _race_controls()],
                justify="space-between", align="center",
                className="analysis-header"),
            dmc.Text(id="analysis-caption", size="xs", c="dimmed",
                     className="analysis-caption"),
            html.Div(
                [_arrow("analysis-prev", "mdi:chevron-left", "Previous chart"),
                 dcc.Graph(id="analysis-graph", config=_GRAPH_CONFIG,
                           className="analysis-graph",
                           style={"height": "100%", "width": "100%"}),
                 _arrow("analysis-next", "mdi:chevron-right", "Next chart")],
                className="analysis-stage"),
            dmc.Text(id="analysis-caveat", size="xs", c="dimmed",
                     className="analysis-caveat"),
            dmc.Group(dots(0, len(views.VIEWS)), id="analysis-dots",
                      justify="center", gap="xs", className="analysis-dots"),
        ],
        id="analysis-panel", className="analysis-panel")
