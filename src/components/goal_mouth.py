# src/components/goal_mouth.py
"""Goal-mouth map UI: pure figure/hover/color/drawer-body builders plus the
panel and left-drawer constructors. Plotly + dash-mantine-components only."""
from __future__ import annotations

import dash_mantine_components as dmc
import plotly.graph_objects as go
from dash import dcc

from src.data.live.goal_mouth_zones import ON_TARGET, parse_shot_minute

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


def _rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{round(alpha, 3)})"


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
    """A goal frame: filled, hoverable, clickable rectangles per zone (grid +
    present margins), posts/crossbar lines, and a side readout."""
    dark = theme != "light"
    fills = cell_fill_colors(agg, mode, theme)
    line_color = "rgba(255,255,255,0.35)" if dark else "rgba(0,0,0,0.35)"
    fg = "#E9ECEF" if dark else "#1A1B1E"

    fig = go.Figure()
    # Draw grid cells always; margins only when present in agg["zones"].
    order = [z for z in ON_TARGET] + [z for z in agg["zones"] if z not in ON_TARGET]
    for zid in order:
        x0, y0, x1, y1 = ZONE_BOX[zid]
        fig.add_trace(go.Scatter(
            x=[x0, x1, x1, x0, x0], y=[y0, y0, y1, y1, y0],
            fill="toself", fillcolor=fills[zid], mode="lines",
            line=dict(color=line_color, width=1), hoveron="fills",
            hovertemplate=zone_hover_text(zid, agg["zones"][zid]) + "<extra></extra>",
            customdata=[zid] * 5, showlegend=False, name=ZONE_LABEL.get(zid, zid),
        ))

    # Posts + crossbar (the on-target / near-miss divider).
    post = dict(type="line", line=dict(color=fg, width=3), layer="above")
    shapes = [
        {**post, "x0": 0, "y0": 0, "x1": 0, "y1": 2},
        {**post, "x0": 3, "y0": 0, "x1": 3, "y1": 2},
        {**post, "x0": 0, "y0": 2, "x1": 3, "y1": 2},
    ]

    t = agg["totals"]
    readout = (f"On target {t['on_target']}<br>Near miss {t['near_miss']}<br>"
               f"Woodwork {t['woodwork']}<br>Off target {t['off_target']}<br>"
               f"<b>Total {t['total']}</b>")
    annotations = [dict(
        xref="paper", yref="paper", x=1.0, y=1.0, xanchor="right", yanchor="top",
        align="right", showarrow=False, font=dict(color=fg, size=11), text=readout)]

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=8, r=8, t=8, b=8), showlegend=False, autosize=True,
        shapes=shapes, annotations=annotations,
        hoverlabel=dict(bgcolor="#23262B" if dark else "#FFFFFF", font_color=fg),
        xaxis=dict(visible=False, range=[-0.9, 5.4], fixedrange=True),
        yaxis=dict(visible=False, range=[-0.3, 2.8], fixedrange=True,
                   scaleanchor="x", scaleratio=1),
    )
    return fig


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
