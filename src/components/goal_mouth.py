# src/components/goal_mouth.py
"""Goal-mouth map UI: pure figure/hover/color/drawer-body builders plus the
panel and left-drawer constructors. Plotly + dash-mantine-components only."""
from __future__ import annotations

import dash_ag_grid as dag
import dash_mantine_components as dmc
import plotly.graph_objects as go
from dash import dcc

from src.data.live.goal_mouth_zones import ON_TARGET, parse_shot_minute

# --- color enum (consistent everywhere; pair with text labels, never alone) ---
OUTCOME_COLORS = {
    "Goal": "#1D9E75", "Saved": "#378ADD", "Blocked": "#888780",
    "Post": "#D85A30", "Missed": "#EF9F27",
}

ZONE_LABEL = {
    "high_left": "High Left", "high_centre": "High Centre", "high_right": "High Right",
    "low_left": "Low Left", "low_centre": "Low Centre", "low_right": "Low Right",
    "close_high": "Close High", "close_left": "Close Left",
    "close_right": "Close Right", "close_right_high": "Close Right & High",
}

# Heatmap geometry: columns Left/Centre/Right -> x 0,1,2; rows Low/High -> y 0,1
# (y index 0 = Low, the bottom row). The frame encloses the 2x3 cells.
_COLS = ["left", "centre", "right"]
_ROWS = ["low", "high"]
_GX0, _GX1, _GY0, _GY1 = -0.5, 2.5, -0.5, 1.5          # frame extents (cell edges)
# Volume heatmap ramp (same in both themes; cells stay dark enough that the
# white numerals read on any value).
_VOLUME_SCALE = [[0.0, "#1f3a5f"], [1.0, "#1c63d6"]]


def zone_hover_text(zone_id: str, zinfo: dict) -> str:
    label = ZONE_LABEL.get(zone_id, zone_id)
    n = zinfo["count"]
    if n == 0:
        return f"<b>{label}</b><br>no shots"
    parts = ", ".join(f"{c} {o.lower()}"
                      for o, c in sorted(zinfo["outcomes"].items(),
                                         key=lambda kv: -kv[1]))
    return "<br>".join([f"<b>{label}</b> — {n} shots", parts,
                        f"<i>click to see all {n}</i>"])


def build_goal_mouth_figure(agg: dict, theme: str = "dark") -> go.Figure:
    """A clean heatmap goal: the 2x3 on-target grid is a Plotly heatmap shaded
    by shot volume with the count in each cell, framed by posts/crossbar + goal
    line, with an off-target tally and a colour-scale legend (colorbar)."""
    dark = theme != "light"
    fg = "#E9ECEF" if dark else "#1A1B1E"            # text/labels (stays readable)
    goal_fg = "#E9ECEF" if dark else "#ADB5BD"       # soft grey goal frame on light
    zones = agg["zones"]

    def cell(zid):
        return zones.get(zid, {"count": 0, "outcomes": {}, "shooters": []})

    ids = [[f"{r}_{c}" for c in _COLS] for r in _ROWS]      # ids[0] = Low row
    counts = [[cell(z)["count"] for z in row] for row in ids]
    text = [["" if not n else str(n) for n in row] for row in counts]
    hover = [[zone_hover_text(z, cell(z)) for z in row] for row in ids]

    cbar = dict(orientation="h", thickness=9, len=0.6, x=0.5, xanchor="center",
                y=-0.08, yanchor="top", outlinewidth=0,
                tickfont=dict(color=fg, size=10),
                title=dict(text="shots", font=dict(color=fg, size=10), side="top"))
    z = [[(n or None) for n in row] for row in counts]
    mx = max((n for row in counts for n in row), default=0)
    zmin, zmax = 0, max(mx, 1)
    showscale = mx > 0

    fig = go.Figure(go.Heatmap(
        z=z, x=[0, 1, 2], y=[0, 1], customdata=ids,
        text=text, texttemplate="%{text}", textfont=dict(color="#FFFFFF", size=16),
        hovertext=hover, hovertemplate="%{hovertext}<extra></extra>",
        hoverongaps=False, xgap=4, ygap=4,
        colorscale=_VOLUME_SCALE, zmin=zmin, zmax=zmax,
        showscale=showscale, colorbar=cbar,
    ))

    # Invisible hit-markers over the six cells -> reliable clicks -> drawer.
    fig.add_trace(go.Scatter(
        x=[0, 1, 2, 0, 1, 2], y=[0, 0, 0, 1, 1, 1],
        customdata=[z for row in ids for z in row], mode="markers",
        marker=dict(size=46, color="rgba(0,0,0,0)", line=dict(width=0)),
        hoverinfo="skip", showlegend=False, name="zone-hit",
    ))

    # Posts + crossbar frame and the goal line (soft grey on light theme).
    frame = dict(type="line", line=dict(color=goal_fg, width=5), layer="above")
    shapes = [
        {**frame, "x0": _GX0, "y0": _GY0, "x1": _GX0, "y1": _GY1},   # left post
        {**frame, "x0": _GX1, "y0": _GY0, "x1": _GX1, "y1": _GY1},   # right post
        {**frame, "x0": _GX0, "y0": _GY1, "x1": _GX1, "y1": _GY1},   # crossbar
        dict(type="line", x0=_GX0 - 0.5, y0=_GY0, x1=_GX1 + 0.5, y1=_GY0,
             line=dict(color=goal_fg, width=3), layer="above"),      # goal line
    ]

    # On/off-target counts now live in the card subtitle, so the figure carries
    # no annotation — and with the near-miss markers gone the axis ranges hug the
    # frame so the goal fills the card.
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=6, r=6, t=8, b=26), showlegend=False, autosize=True,
        shapes=shapes,
        hoverlabel=dict(bgcolor="#23262B" if dark else "#FFFFFF", font_color=fg),
        xaxis=dict(visible=False, range=[-1.05, 3.05], fixedrange=True),
        yaxis=dict(visible=False, range=[-1.0, 1.95], fixedrange=True),
    )
    return fig


_GRAPH_CONFIG = {"displayModeBar": False, "responsive": True}


def build_goal_mouth_panel() -> dmc.Box:
    """Shoot map card: header (title only) over a Plotly heatmap goal that fills
    the whole card (its colour-scale legend lives in-figure)."""
    header = dmc.Group(
        [
            dmc.Text("Shoot map", fw=700, size="sm"),
            # On/off-target tally (filled per team by the figure callback).
            dmc.Text("", id="goal-mouth-subtitle", size="xs", c="dimmed"),
        ],
        justify="space-between", align="center", wrap="nowrap",
        className="bento-card__header",
    )
    graph = dcc.Graph(id="goal-mouth-graph", figure=build_goal_mouth_figure(
        {"zones": {z: {"count": 0, "outcomes": {}, "shooters": []}
                   for z in ON_TARGET},
         "off_target": {"count": 0, "outcomes": {}},
         "other": {"count": 0, "outcomes": {}},
         "totals": {"on_target": 0, "near_miss": 0, "woodwork": 0,
                    "off_target": 0, "other": 0, "total": 0}}),
        config=_GRAPH_CONFIG, style={"width": "100%", "flex": "1 1 auto",
                                     "minHeight": 0})
    body = dmc.Box([graph], className="goal-mouth-panel__body")
    return dmc.Box([header, body], className="goal-mouth-panel")


def build_goal_mouth_drawer() -> dmc.Drawer:
    """App-level LEFT drawer holding the clicked zone's full shot list.

    No overlay (and no scroll lock): the goal-mouth box stays interactive while
    the drawer is open, so clicking another zone replaces the contents in a
    single click (per spec) and the only dismissals are re-clicking the same
    zone or the close control."""
    return dmc.Drawer(
        id="goal-mouth-drawer",
        position="left", size="md", padding="md", opened=False,
        withCloseButton=True, withOverlay=False, lockScroll=False, zIndex=2500,
        classNames={"content": "filter-drawer-frosted",
                    "header": "filter-drawer-frosted-header"},
    )


# Outcome column colours sourced from the shared enum (single source of truth),
# applied per cell via dash-ag-grid styleConditions.
_OUTCOME_CELL_STYLE = {
    "styleConditions": [
        {"condition": f"params.value == '{o}'",
         "style": {"color": c, "fontWeight": 600}}
        for o, c in OUTCOME_COLORS.items()
    ],
}
_SHOT_COLUMNS = [
    {"headerName": "Min", "field": "min", "width": 64, "sortable": True},
    {"headerName": "Player", "field": "player", "flex": 1, "minWidth": 110,
     "sortable": True},
    {"headerName": "vs", "field": "opponent", "flex": 1, "minWidth": 90,
     "sortable": True},
    {"headerName": "Outcome", "field": "outcome", "width": 104, "sortable": True,
     "cellStyle": _OUTCOME_CELL_STYLE},
]
_SHOT_GRID_OPTIONS = {
    "suppressCellFocus": True, "rowHeight": 34, "headerHeight": 34,
    "overlayNoRowsTemplate": "No shots in this zone",
}


def drawer_body(zone_id: str, agg: dict, dark: bool = True) -> list:
    """Self-contained left-drawer contents for one zone: a summary header over an
    AG grid of the zone's shots (minute · shooter · opponent "vs <team>" ·
    outcome), time-sorted. `dark` selects the AG theme to match the app."""
    z = agg["zones"].get(zone_id, {"count": 0, "outcomes": {}, "shooters": []})
    label = ZONE_LABEL.get(zone_id, zone_id)
    breakdown = ", ".join(f"{c} {o}" for o, c in
                          sorted(z["outcomes"].items(), key=lambda kv: -kv[1]))
    header = dmc.Stack([
        dmc.Text(label, fw=700, size="lg"),
        dmc.Text(f"{z['count']} shots — {breakdown}" if z["count"] else "No shots",
                 size="sm", c="dimmed"),
    ], gap=2)

    rows = [
        {"min": s["time"], "player": s["player"],
         "opponent": s.get("opponent", ""), "outcome": s["outcome"]}
        for s in sorted(z["shooters"], key=lambda s: parse_shot_minute(s["time"]))
    ]
    theme = "ag-theme-quartz-dark" if dark else "ag-theme-quartz"
    grid = dag.AgGrid(
        id="goal-mouth-shot-grid",
        columnDefs=_SHOT_COLUMNS,
        rowData=rows,
        className=f"{theme} goal-mouth-grid",
        dashGridOptions=_SHOT_GRID_OPTIONS,
        style={"height": "70vh", "width": "100%"},
    )
    return [dmc.Stack([header, grid], gap="sm")]
