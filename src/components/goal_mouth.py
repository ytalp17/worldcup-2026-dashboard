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
VOLUME_HUE = "#534AB7"               # neutral single hue for volume mode
# Deterministic dominant-outcome tie-break order.
_DOMINANT_ORDER = ["Goal", "Saved", "Blocked", "Post", "Missed"]

ZONE_LABEL = {
    "high_left": "High Left", "high_centre": "High Centre", "high_right": "High Right",
    "low_left": "Low Left", "low_centre": "Low Centre", "low_right": "Low Right",
    "close_high": "Close High", "close_left": "Close Left",
    "close_right": "Close Right", "close_right_high": "Close Right & High",
}

# Rectangle geometry: (x0, y0, x1, y1). Inside the posts x∈[0,3], y∈[0,2];
# rows High (top, y 1-2) / Low (bottom, y 0-1); cols Left/Centre/Right.
ZONE_BOX = {
    "high_left": (0, 1, 1, 2), "high_centre": (1, 1, 2, 2), "high_right": (2, 1, 3, 2),
    "low_left": (0, 0, 1, 1), "low_centre": (1, 0, 2, 1), "low_right": (2, 0, 3, 1),
    "close_high": (0, 2, 3, 2.6), "close_left": (-0.6, 0, 0, 2),
    "close_right": (3, 0, 3.6, 2), "close_right_high": (3, 2, 3.6, 2.6),
}

# Cell centres — used for the invisible hit-marker overlay (see
# build_goal_mouth_figure) so every zone has a real clickable data point.
ZONE_CENTER = {z: ((x0 + x1) / 2, (y0 + y1) / 2)
               for z, (x0, y0, x1, y1) in ZONE_BOX.items()}


def _rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{round(alpha, 3)})"


def _diagonal_lines(box, color, step=0.3, width=1):
    """Parallel slope-1 ('/') line shapes clipped to an axis-aligned box — the
    one-way diagonal netting for the near-miss outer band (vs the square mesh
    inside the goal)."""
    x0, y0, x1, y1 = box
    shapes = []
    b = y0 - x1                       # first '/' line touching the bottom-right
    while b <= y1 - x0 + 1e-9:        # last line touching the top-left
        xa, xb = max(x0, y0 - b), min(x1, y1 - b)
        if xb > xa:
            shapes.append(dict(type="line", x0=xa, y0=xa + b, x1=xb, y1=xb + b,
                               line=dict(color=color, width=width), layer="above"))
        b += step
    return shapes


def goal_mouth_readout(agg: dict) -> str:
    """Compact one-line totals readout shown beside the figure (kept out of the
    figure so the goal can use the card's full space)."""
    t = agg["totals"]
    return (f"On target {t['on_target']} · Near miss {t['near_miss']} · "
            f"Woodwork {t['woodwork']} · Off target {t['off_target']} · "
            f"Total {t['total']}")


def _dominant_outcome(outcomes: dict) -> str | None:
    if not outcomes:
        return None
    best = max(outcomes.values())
    for o in _DOMINANT_ORDER:                       # deterministic tie-break
        if outcomes.get(o, 0) == best:
            return o
    return next(iter(outcomes))


def cell_fill_colors(agg: dict, mode: str, theme: str = "dark") -> dict[str, str]:
    """region id -> rgba fill. Volume: single hue, opacity by count (margins use
    the near-miss hue). Dominant: grid cells colored by top outcome, margins
    always the near-miss color."""
    zones = agg["zones"]
    max_count = max((z["count"] for z in zones.values()), default=0) or 1
    out: dict[str, str] = {}
    for zid, z in zones.items():
        is_margin = zid not in ON_TARGET
        if z["count"] == 0:
            out[zid] = _rgba(NEAR_MISS_COLOR if is_margin else VOLUME_HUE, 0.05)
            continue
        if mode == "dominant" and not is_margin:
            out[zid] = _rgba(OUTCOME_COLORS.get(_dominant_outcome(z["outcomes"]),
                                                VOLUME_HUE), 0.85)
        else:
            hue = NEAR_MISS_COLOR if is_margin else VOLUME_HUE
            out[zid] = _rgba(hue, 0.15 + 0.85 * (z["count"] / max_count))
    return out


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
    """A goal: filled, hoverable, clickable rectangles per zone (grid + present
    margins) under a net mesh, diagonal outer-band netting, and a posts/crossbar
    frame. The totals readout lives beside the figure, not inside it."""
    dark = theme != "light"
    fills = cell_fill_colors(agg, mode, theme)
    fg = "#E9ECEF" if dark else "#1A1B1E"
    net = "rgba(255,255,255,0.11)" if dark else "rgba(0,0,0,0.07)"
    divider = "rgba(255,255,255,0.26)" if dark else "rgba(0,0,0,0.18)"

    fig = go.Figure()
    # Draw grid cells always; margins only when present in agg["zones"].
    # Cell outlines are off — the net mesh + dividers + frame (shapes below) give
    # the goal its structure; near-miss margins get a faint dotted amber edge.
    order = [z for z in ON_TARGET] + [z for z in agg["zones"] if z not in ON_TARGET]
    for zid in order:
        x0, y0, x1, y1 = ZONE_BOX[zid]
        is_margin = zid not in ON_TARGET
        edge = (dict(color=_rgba(NEAR_MISS_COLOR, 0.55), width=1, dash="dot")
                if is_margin else dict(width=0))
        fig.add_trace(go.Scatter(
            x=[x0, x1, x1, x0, x0], y=[y0, y0, y1, y1, y0],
            fill="toself", fillcolor=fills[zid], mode="lines",
            line=edge, hoveron="fills",
            hovertemplate=zone_hover_text(zid, agg["zones"][zid]) + "<extra></extra>",
            customdata=[zid] * 5, showlegend=False, name=ZONE_LABEL.get(zid, zid),
        ))

    # Invisible hit-marker overlay: one transparent marker at each zone's centre,
    # carrying the zone id as customdata. Clicking a fill interior can report a
    # point with customdata=None in Plotly; a real marker point guarantees the
    # click lands on a zone id, making the click->drawer interaction reliable.
    fig.add_trace(go.Scatter(
        x=[ZONE_CENTER[z][0] for z in order],
        y=[ZONE_CENTER[z][1] for z in order],
        customdata=list(order), mode="markers",
        marker=dict(size=42, color="rgba(0,0,0,0)", line=dict(width=0)),
        hoverinfo="skip", showlegend=False, name="zone-hit",
    ))

    # --- goal structure (drawn above the fills) -----------------------------
    # Square net mesh inside the goal mouth (x 0..3, y 0..2); one-way diagonal
    # netting in the near-miss outer band; 2x3 zone dividers a touch stronger;
    # a solid posts/crossbar frame; and a goal line grounding the whole thing.
    shapes = []
    grid_step = 0.25
    n_v = int(round(3 / grid_step))
    n_h = int(round(2 / grid_step))
    for i in range(1, n_v):
        x = round(i * grid_step, 4)
        shapes.append(dict(type="line", x0=x, y0=0, x1=x, y1=2,
                           line=dict(color=net, width=1), layer="above"))
    for i in range(1, n_h):
        y = round(i * grid_step, 4)
        shapes.append(dict(type="line", x0=0, y0=y, x1=3, y1=y,
                           line=dict(color=net, width=1), layer="above"))
    # Diagonal netting for the outer band — only the four margins that can occur
    # (left/right/top strips + top-right corner; never bottom or top-left).
    for m in MARGINS:
        shapes += _diagonal_lines(ZONE_BOX[m], net)
    # 2x3 zone dividers (cols at x=1,2; the High/Low split at y=1).
    div = dict(type="line", line=dict(color=divider, width=1.4), layer="above")
    shapes += [
        {**div, "x0": 1, "y0": 0, "x1": 1, "y1": 2},
        {**div, "x0": 2, "y0": 0, "x1": 2, "y1": 2},
        {**div, "x0": 0, "y0": 1, "x1": 3, "y1": 1},
    ]
    # Posts + crossbar (solid frame) and the goal line.
    frame = dict(type="line", line=dict(color=fg, width=5), layer="above")
    shapes += [
        {**frame, "x0": 0, "y0": 0, "x1": 0, "y1": 2},      # left post
        {**frame, "x0": 3, "y0": 0, "x1": 3, "y1": 2},      # right post
        {**frame, "x0": 0, "y0": 2, "x1": 3, "y1": 2},      # crossbar
        dict(type="line", x0=-0.6, y0=0, x1=3.6, y1=0,
             line=dict(color=fg, width=3), layer="above"),  # goal line
    ]

    # Ranges hug the goal + margins (no reserved readout strip), and the graph
    # autosizes responsively to the card; the totals readout lives beside the
    # figure (see build_goal_mouth_panel) so the goal fills the space.
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=6, r=6, t=6, b=6), showlegend=False, autosize=True,
        shapes=shapes,
        hoverlabel=dict(bgcolor="#23262B" if dark else "#FFFFFF", font_color=fg),
        xaxis=dict(visible=False, range=[-0.8, 3.8], fixedrange=True),
        yaxis=dict(visible=False, range=[-0.3, 2.8], fixedrange=True,
                   scaleanchor="x", scaleratio=1),
    )
    return fig


_GRAPH_CONFIG = {"displayModeBar": False, "responsive": True}


def build_goal_mouth_panel() -> dmc.Box:
    """Shoot map card: header (title + fill-mode control) over a Plotly graph
    that fills the card, with a one-line legend + totals readout footer."""
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
    footer = dmc.Group(
        [
            dmc.Text("inside the posts = on target · outer band = near miss",
                     size="xs", c="dimmed", style={"flex": 1, "minWidth": 0}),
            dmc.Text("", id="goal-mouth-readout", size="xs", c="dimmed",
                     ta="right", style={"whiteSpace": "nowrap"}),
        ],
        justify="space-between", align="center", wrap="wrap", gap="xs",
    )
    body = dmc.Box([graph, footer], className="goal-mouth-panel__body")
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
