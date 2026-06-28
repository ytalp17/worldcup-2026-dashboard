# src/components/goal_mouth.py
"""Goal-mouth map UI: pure figure/hover/color/drawer-body builders plus the
panel and left-drawer constructors. Plotly + dash-mantine-components only."""
from __future__ import annotations

import dash_mantine_components as dmc
import plotly.graph_objects as go
from dash import dcc

from src.data.live.goal_mouth_zones import MARGINS, ON_TARGET, parse_shot_minute

# --- color enum (consistent everywhere; pair with text labels, never alone) ---
OUTCOME_COLORS = {
    "Goal": "#1D9E75", "Saved": "#378ADD", "Blocked": "#888780",
    "Post": "#D85A30", "Missed": "#EF9F27",
}
NEAR_MISS_COLOR = "#EF9F27"          # the Close* family
# Deterministic dominant-outcome tie-break order.
_DOMINANT_ORDER = ["Goal", "Saved", "Blocked", "Post", "Missed"]

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
# Near-miss marker positions just outside the frame (only the four that occur).
_NEAR_POS = {"close_left": (-1.05, 0.5), "close_right": (3.05, 0.5),
             "close_high": (1.0, 2.05), "close_right_high": (3.05, 2.05)}
# Volume heatmap ramp (same in both themes; cells stay dark enough that the
# white numerals read on any value).
_VOLUME_SCALE = [[0.0, "#1f3a5f"], [1.0, "#1c63d6"]]


def _dominant_outcome(outcomes: dict) -> str | None:
    if not outcomes:
        return None
    best = max(outcomes.values())
    for o in _DOMINANT_ORDER:                       # deterministic tie-break
        if outcomes.get(o, 0) == best:
            return o
    return next(iter(outcomes))


def zone_hover_text(zone_id: str, zinfo: dict) -> str:
    label = ZONE_LABEL.get(zone_id, zone_id)
    n = zinfo["count"]
    if n == 0:
        return f"<b>{label}</b><br>no shots"
    parts = ", ".join(f"{c} {o.lower()}"
                      for o, c in sorted(zinfo["outcomes"].items(),
                                         key=lambda kv: -kv[1]))
    lines = [f"<b>{label}</b> — {n} shots", parts]
    if zinfo.get("shooters"):
        top = zinfo["shooters"][0]
        lines.append(f"top: {top['player']}")
    if n > 6:
        lines.append(f"<i>click to see all {n}</i>")
    return "<br>".join(lines)


def build_goal_mouth_figure(agg: dict, mode: str = "volume",
                            theme: str = "dark") -> go.Figure:
    """A clean heatmap goal: the 2x3 on-target grid shaded by value with the
    shot count in each cell, a posts/crossbar frame, near-miss markers just
    outside, an off-target tally, and a colour-scale legend (colorbar)."""
    dark = theme != "light"
    fg = "#E9ECEF" if dark else "#1A1B1E"
    zones = agg["zones"]

    def cell(zid):
        return zones.get(zid, {"count": 0, "outcomes": {}, "shooters": []})

    ids = [[f"{r}_{c}" for c in _COLS] for r in _ROWS]      # ids[0] = Low row
    counts = [[cell(z)["count"] for z in row] for row in ids]
    text = [["" if not n else str(n) for n in row] for row in counts]
    hover = [[zone_hover_text(z, cell(z)) for z in row] for row in ids]

    cbar = dict(orientation="h", thickness=9, len=0.6, x=0.5, xanchor="center",
                y=-0.08, yanchor="top", outlinewidth=0,
                tickfont=dict(color=fg, size=10))

    if mode == "dominant":
        present = [o for o in _DOMINANT_ORDER
                   if any(_dominant_outcome(cell(z)["outcomes"]) == o
                          for row in ids for z in row)]
        index = {o: i for i, o in enumerate(present)}
        z = [[(index[_dominant_outcome(cell(zid)["outcomes"])]
               if cell(zid)["count"] else None) for zid in row] for row in ids]
        n = max(len(present), 1)
        colorscale = ([[0, "#888888"], [1, "#888888"]] if not present else
                      [pair for i, o in enumerate(present)
                       for pair in ([i / n, OUTCOME_COLORS[o]],
                                    [(i + 1) / n, OUTCOME_COLORS[o]])])
        zmin, zmax = -0.5, n - 0.5
        # Empty title (set explicitly so a volume->dominant react diff clears the
        # previous "shots" label); the category names are the legend.
        cbar.update(tickmode="array", tickvals=list(range(len(present))),
                    ticktext=present,
                    title=dict(text="", font=dict(color=fg, size=10), side="top"))
        showscale = bool(present)
    else:
        z = [[(n or None) for n in row] for row in counts]
        colorscale = _VOLUME_SCALE
        mx = max((n for row in counts for n in row), default=0)
        zmin, zmax = 0, max(mx, 1)
        cbar.update(tickmode="auto", tickvals=None, ticktext=None,
                    title=dict(text="shots", font=dict(color=fg, size=10), side="top"))
        showscale = mx > 0

    fig = go.Figure(go.Heatmap(
        z=z, x=[0, 1, 2], y=[0, 1], customdata=ids,
        text=text, texttemplate="%{text}", textfont=dict(color="#FFFFFF", size=16),
        hovertext=hover, hovertemplate="%{hovertext}<extra></extra>",
        hoverongaps=False, xgap=4, ygap=4,
        colorscale=colorscale, zmin=zmin, zmax=zmax,
        showscale=showscale, colorbar=cbar,
    ))

    # Invisible hit-markers over the six cells -> reliable clicks -> drawer.
    fig.add_trace(go.Scatter(
        x=[0, 1, 2, 0, 1, 2], y=[0, 0, 0, 1, 1, 1],
        customdata=[z for row in ids for z in row], mode="markers",
        marker=dict(size=46, color="rgba(0,0,0,0)", line=dict(width=0)),
        hoverinfo="skip", showlegend=False, name="zone-hit",
    ))

    # Near-miss markers just outside the frame (only where they occur), clickable.
    nx, ny, nt, ncd, nh = [], [], [], [], []
    for m in MARGINS:
        cm = cell(m)
        if cm["count"]:
            px, py = _NEAR_POS[m]
            nx.append(px); ny.append(py); nt.append(str(cm["count"]))
            ncd.append(m); nh.append(zone_hover_text(m, cm))
    if nx:
        fig.add_trace(go.Scatter(
            x=nx, y=ny, customdata=ncd, mode="markers+text", text=nt,
            textposition="middle center", textfont=dict(color="#FFFFFF", size=11),
            marker=dict(size=24, color=NEAR_MISS_COLOR, line=dict(color=fg, width=1)),
            hovertext=nh, hovertemplate="%{hovertext}<extra></extra>",
            showlegend=False, name="near-miss",
        ))

    # Posts + crossbar frame and the goal line.
    frame = dict(type="line", line=dict(color=fg, width=5), layer="above")
    shapes = [
        {**frame, "x0": _GX0, "y0": _GY0, "x1": _GX0, "y1": _GY1},   # left post
        {**frame, "x0": _GX1, "y0": _GY0, "x1": _GX1, "y1": _GY1},   # right post
        {**frame, "x0": _GX0, "y0": _GY1, "x1": _GX1, "y1": _GY1},   # crossbar
        dict(type="line", x0=_GX0 - 0.5, y0=_GY0, x1=_GX1 + 0.5, y1=_GY0,
             line=dict(color=fg, width=3), layer="above"),           # goal line
    ]

    annotations = []
    off = agg["off_target"]["count"]
    if off:
        annotations.append(dict(
            x=_GX0 - 0.55, y=_GY1 + 0.55, xanchor="left", yanchor="middle",
            showarrow=False, text=f"Off-target {off}", font=dict(color=fg, size=10)))

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=6, r=6, t=8, b=26), showlegend=False, autosize=True,
        shapes=shapes, annotations=annotations,
        hoverlabel=dict(bgcolor="#23262B" if dark else "#FFFFFF", font_color=fg),
        xaxis=dict(visible=False, range=[-1.45, 3.45], fixedrange=True),
        yaxis=dict(visible=False, range=[-1.05, 2.5], fixedrange=True),
    )
    return fig


_GRAPH_CONFIG = {"displayModeBar": False, "responsive": True}


def build_goal_mouth_panel() -> dmc.Box:
    """Shoot map card: header (title + fill-mode control) over a Plotly heatmap
    goal that fills the whole card (its colour-scale legend lives in-figure)."""
    header = dmc.Group(
        [
            dmc.Text("Shoot map", fw=700, size="sm"),
            dmc.SegmentedControl(id="goal-mouth-mode", value="Volume",
                                 data=["Volume", "Dominant"], size="xs"),
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


def drawer_body(zone_id: str, agg: dict) -> list:
    """Self-contained left-drawer contents for one zone: summary header + a
    scrollable, time-sorted shot list (minute · shooter · outcome)."""
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
        dmc.Group([
            dmc.Text(s["time"], size="sm", w=52, c="dimmed"),
            dmc.Text(s["player"], size="sm", style={"flex": 1, "minWidth": 0}),
            dmc.Text(s["outcome"], size="sm", fw=600,
                     c=OUTCOME_COLORS.get(s["outcome"], "gray")),
        ], gap="xs", wrap="nowrap")
        for s in sorted(z["shooters"], key=lambda s: parse_shot_minute(s["time"]))
    ]
    body = dmc.ScrollArea(dmc.Stack(rows, gap=4), style={"height": "70vh"})
    return [dmc.Stack([header, body], gap="sm")]
