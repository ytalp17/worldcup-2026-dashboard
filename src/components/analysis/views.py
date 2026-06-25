from __future__ import annotations

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.components.analysis import theme
from src.data.analysis import aggregate

# Capture at module scope so dumbbell_figure (which shadows `theme` as a
# string param) can reference these without calling theme.<anything>.
DUMBBELL = theme.DUMBBELL

VIEWS = [
    {"id": "ATTACKING_THREAT", "type": "radar", "title": "Attacking threat",
     "caption": "Where each team generates danger (per-90, scaled to the group).",
     "metrics": [("xg", "Expected goals", "rate"), ("xa", "Expected assists", "rate"),
                 ("big_chances", "Big chances", "count"),
                 ("shots_in_box", "Shots in box", "count"),
                 ("key_passes", "Key passes", "count")]},
    {"id": "BUILD_UP", "type": "radar", "title": "Build-up",
     "caption": "How teams progress the ball (per-90, scaled to the group).",
     "metrics": [("possession", "Possession", "rate"),
                 ("passes_succ", "Successful passes", "count"),
                 ("passes_final_third", "Passes into final third", "count"),
                 ("key_passes", "Key passes", "count"),
                 ("dribbles_succ", "Successful dribbles", "count")]},
    {"id": "DEFENSIVE_WORK", "type": "radar", "title": "Defensive work",
     "caption": "Defensive actions (per-90, scaled to the group).",
     "caveat": "High volume often means a team played without the ball — a bigger "
               "shape is not necessarily better defending.",
     "metrics": [("tackles_succ", "Successful tackles", "count"),
                 ("interceptions", "Interceptions", "count"),
                 ("clearances", "Clearances", "count"),
                 ("aerials_won", "Aerial duels won", "count"),
                 ("gk_saves", "Goalkeeper saves", "count")]},
    {"id": "STYLE_FINGERPRINT", "type": "radar", "title": "Style fingerprint",
     "caption": "How a team plays — raw attempt volumes (per-90, scaled).",
     "metrics": [("possession", "Possession", "rate"),
                 ("crosses", "Crosses", "count"),
                 ("long_passes", "Long passes", "count"),
                 ("dribbles", "Dribbles", "count"),
                 ("aerials", "Aerial duels", "count")]},
    {"id": "FINISHING", "type": "dumbbell", "title": "Finishing: goals vs xG",
     "caption": "Actual goals against expected goals — over- and under-performance.",
     "caveat": "With few shots or matches, finishing looks extreme and tends to "
               "regress."},
    {"id": "RACE", "type": "race", "title": "Race over matchdays",
     "caption": "A selected metric accumulating matchday by matchday."},
    {"id": "SHOT_FUNNEL", "type": "funnel", "title": "Shot funnel",
     "caption": "Shots → on target → goals, per team."},
    {"id": "QUALITY_VS_CONV", "type": "quadrant", "title": "Chance quality vs conversion",
     "caption": "xG per shot (quality) against conversion % (goals ÷ shots)."},
    {"id": "HOW_THEY_DEFEND", "type": "defend", "title": "How they defend",
     "caption": "Defensive volume and its mix, per-90.",
     "caveat": "High defensive volume often signals playing without the ball — "
               "more actions is not better defending."},
    {"id": "VOLUME_VS_PENETR", "type": "bubble", "title": "Volume vs penetration",
     "caption": "Total passes against passes into the final third; bubble = accuracy %."},
]

VIEW_BY_ID = {v["id"]: v for v in VIEWS}


def radar_figure(records, view, theme: str = "dark") -> go.Figure:
    series = aggregate.radar_series(records, view["metrics"])
    cmap = _theme_team_color(series["teams"])
    fmap = _theme_team_fill(series["teams"])
    axes = series["axes"] + series["axes"][:1]  # close the loop
    fig = go.Figure()
    for t in series["teams"]:
        scaled = series["scaled"][t] + series["scaled"][t][:1]
        raw = series["raw"][t] + series["raw"][t][:1]
        fig.add_trace(go.Scatterpolar(
            r=scaled, theta=axes, name=t, fill="toself",
            fillcolor=fmap[t], line=dict(color=cmap[t], width=2),
            customdata=list(zip(raw, axes)),
            hovertemplate="<b>%{fullData.name}</b><br>%{theta}: "
                          "%{customdata[0]}<extra></extra>",
        ))
    lay = theme_layout(theme)
    fig.update_layout(
        polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(range=[0, 100], showticklabels=False,
                            gridcolor=lay["gridcolor_hint"], showline=False),
            angularaxis=dict(gridcolor=lay["gridcolor_hint"]),
        ),
        paper_bgcolor=lay["paper_bgcolor"], font=lay["font"],
        margin=dict(l=40, r=40, t=10, b=20), showlegend=False, autosize=True,
    )
    return fig


# small indirections so later tasks can reuse the same helpers
def theme_layout(t):
    return theme.plotly_layout(t)


def _theme_team_color(teams):
    return theme.team_color_map(teams)


def _theme_team_fill(teams):
    return theme.team_fill_map(teams)


def dumbbell_figure(records, theme: str = "dark") -> go.Figure:
    rows = sorted(records, key=lambda r: (r.get("goals", 0) - r.get("xg", 0.0)))
    teams = [r["team"] for r in rows]  # ascending -> biggest gap on top
    lay = theme_layout(theme)
    fig = go.Figure()
    for r in rows:
        over = r.get("goals", 0) >= r.get("xg", 0.0)
        fig.add_trace(go.Scatter(
            x=[r["xg"], r["goals"]], y=[r["team"], r["team"]], mode="lines",
            line=dict(color=DUMBBELL["over"] if over else DUMBBELL["under"],
                      width=4),
            hoverinfo="skip", showlegend=False))
    fig.add_trace(go.Scatter(
        x=[r["xg"] for r in rows], y=teams, mode="markers", name="xG",
        marker=dict(color=DUMBBELL["xg"], size=13),
        hovertemplate="<b>%{y}</b><br>xG: %{x:.2f}<extra></extra>"))
    fig.add_trace(go.Scatter(
        x=[r["goals"] for r in rows], y=teams, mode="markers", name="Goals",
        marker=dict(color=DUMBBELL["goals"], size=13),
        hovertemplate="<b>%{y}</b><br>Goals: %{x}<extra></extra>"))
    fig.update_layout(
        paper_bgcolor=lay["paper_bgcolor"], plot_bgcolor=lay["plot_bgcolor"],
        font=lay["font"], margin=dict(l=80, r=30, t=10, b=40), autosize=True,
        showlegend=False,
        xaxis=dict(title="Goals (with xG)", gridcolor=lay["gridcolor_hint"],
                   zeroline=False),
        yaxis=dict(categoryorder="array", categoryarray=teams,
                   gridcolor="rgba(0,0,0,0)"))
    return fig


def race_frame_count(history: dict) -> int:
    return max((len(v) for v in history.values()), default=0)


def race_figure(history, metric, frame, theme: str = "dark",
                color_map=None) -> go.Figure:
    teams = list(history.keys())
    cmap = color_map or _theme_team_color(teams)
    n = race_frame_count(history)
    f = max(0, min(frame, n - 1)) if n else 0
    vals = []
    for t in teams:
        series = history[t]
        vals.append((t, series[f] if f < len(series) else (series[-1] if series else 0)))
    vals.sort(key=lambda tv: tv[1])  # ascending -> leader on top
    lay = theme_layout(theme)
    fig = go.Figure(go.Bar(
        x=[v for _t, v in vals], y=[t for t, _v in vals], orientation="h",
        marker=dict(color=[cmap[t] for t, _v in vals]),
        text=[f"{v:g}" for _t, v in vals], textposition="outside",
        hovertemplate="<b>%{y}</b><br>" + accessors_label(metric) +
                      ": %{x:g}<extra></extra>"))
    fig.update_layout(
        paper_bgcolor=lay["paper_bgcolor"], plot_bgcolor=lay["plot_bgcolor"],
        font=lay["font"], margin=dict(l=80, r=40, t=10, b=30), autosize=True,
        showlegend=False,
        xaxis=dict(title=accessors_label(metric), gridcolor=lay["gridcolor_hint"],
                   zeroline=False),
        yaxis=dict(gridcolor="rgba(0,0,0,0)"),
        annotations=[dict(x=1, y=1.08, xref="paper", yref="paper",
                          xanchor="right", showarrow=False,
                          text=f"Matchday {f + 1}")])
    return fig


def accessors_label(metric: str) -> str:
    from src.data.analysis.accessors import RACE_METRICS
    return RACE_METRICS.get(metric, metric)


def funnel_figure(records, theme: str = "dark", color_map=None) -> go.Figure:
    """2×2 small-multiples shot funnel: shots → on target → goals (view 7)."""
    teams = [r["team"] for r in records]
    cmap = color_map or _theme_team_color(teams)
    lay = theme_layout(theme)
    fig = make_subplots(rows=2, cols=2, subplot_titles=teams[:4],
                        vertical_spacing=0.18, horizontal_spacing=0.12)
    for i, r in enumerate(records[:4]):
        total = r.get("shots_on", 0) + r.get("shots_off", 0) + r.get("shots_blocked", 0)
        x = [total, r.get("shots_on", 0), r.get("goals", 0)]
        fig.add_trace(go.Funnel(
            y=["Shots", "On target", "Goals"], x=x, name=r["team"],
            marker=dict(color=cmap[r["team"]]),
            textinfo="value+percent previous",
            hovertemplate="<b>%{y}</b>: %{x}<br>%{percentInitial} of all shots"
                          "<extra></extra>"),
            row=i // 2 + 1, col=i % 2 + 1)
    fig.update_layout(
        paper_bgcolor=lay["paper_bgcolor"], plot_bgcolor=lay["plot_bgcolor"],
        font=lay["font"], margin=dict(l=20, r=20, t=30, b=10), autosize=True,
        showlegend=False, funnelmode="stack")
    return fig
