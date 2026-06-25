from __future__ import annotations

import plotly.graph_objects as go

from src.components.analysis import theme
from src.data.analysis import aggregate

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
