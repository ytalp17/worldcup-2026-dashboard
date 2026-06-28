from __future__ import annotations

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.components.analysis import theme
from src.data.analysis import aggregate

# Capture at module scope so functions that shadow `theme` as a string param
# can reference these without calling theme.<anything>.
DUMBBELL = theme.DUMBBELL
DEFEND_COLORS = theme.DEFEND_COLORS

VIEWS = [
    {"id": "ATTACKING_THREAT", "type": "radar", "title": "Attacking threat",
     "caption": "Where each team generates danger (per-90, scaled to the group).",
     "info": "Each spoke is one attacking metric, normalised so the group's best "
             "on that axis reaches the rim. A wide, even shape is a rounded attack; "
             "a single spike marks a team that leans on one route to goal. Values "
             "are per 90 minutes, so sides with different match counts compare fairly.",
     "metrics": [("xg", "Expected goals", "rate"), ("xa", "Expected assists", "rate"),
                 ("big_chances", "Big chances", "count"),
                 ("shots_in_box", "Shots in box", "count"),
                 ("key_passes", "Key passes", "count")]},
    {"id": "BUILD_UP", "type": "radar", "title": "Build-up",
     "caption": "How teams progress the ball (per-90, scaled to the group).",
     "info": "Spokes track ball progression — possession, passing volume and "
             "dribbling. A wide footprint is a possession-heavy side that builds "
             "patiently; a small one a more direct team. Each axis is scaled to "
             "the group leader, per 90 minutes.",
     "metrics": [("possession", "Possession", "rate"),
                 ("passes_succ", "Successful passes", "count"),
                 ("passes_final_third", "Passes into final third", "count"),
                 ("key_passes", "Key passes", "count"),
                 ("dribbles_succ", "Successful dribbles", "count")]},
    {"id": "DEFENSIVE_WORK", "type": "radar", "title": "Defensive work",
     "caption": "Defensive actions (per-90, scaled to the group).",
     "info": "Spokes are defensive actions per 90, scaled to the group. Read it "
             "for a team's defensive workload and where it concentrates — aerial "
             "duels, tackles, interceptions or clearances.",
     "caveat": "High volume often means a team played without the ball — a bigger "
               "shape is not necessarily better defending.",
     "metrics": [("tackles_succ", "Successful tackles", "count"),
                 ("interceptions", "Interceptions", "count"),
                 ("clearances", "Clearances", "count"),
                 ("aerials_won", "Aerial duels won", "count"),
                 ("gk_saves", "Goalkeeper saves", "count")]},
    {"id": "STYLE_FINGERPRINT", "type": "radar", "title": "Style fingerprint",
     "caption": "How a team plays — raw attempt volumes (per-90, scaled).",
     "info": "Raw attempt volumes — what a team tries, not how well it does it. "
             "Lots of crosses and long passes points to a direct side; high "
             "possession and dribbling to a patient, ball-keeping one.",
     "metrics": [("possession", "Possession", "rate"),
                 ("crosses", "Crosses", "count"),
                 ("long_passes", "Long passes", "count"),
                 ("dribbles", "Dribbles", "count"),
                 ("aerials", "Aerial duels", "count")]},
    {"id": "FINISHING", "type": "dumbbell", "title": "Finishing: goals vs xG",
     "caption": "Actual goals against expected goals — over- and under-performance.",
     "info": "Each team's expected goals (xG) and actual goals sit on one line; the "
             "gap is finishing. A green line running right of xG is clinical — more "
             "goals than the chances were worth; a red line left of it is wasteful.",
     "caveat": "With few shots or matches, finishing looks extreme and tends to "
               "regress."},
    {"id": "RACE", "type": "race", "title": "Race over matchdays",
     "caption": "A selected metric accumulating matchday by matchday.",
     "info": "A bar chart that replays the group matchday by matchday for the "
             "chosen metric — press Replay to watch the standings form. The leader "
             "sits on top of each frame. Switch the metric with the selector."},
    {"id": "SHOT_FUNNEL", "type": "funnel", "title": "Shot funnel",
     "caption": "Shots → on target → goals, per team.",
     "info": "For each team, total shots narrow to shots on target and then to "
             "goals. The percentages show how much is lost at each step — shot "
             "selection and finishing combined."},
    {"id": "QUALITY_VS_CONV", "type": "quadrant", "title": "Chance quality vs conversion",
     "caption": "xG per shot (quality) against conversion % (goals ÷ shots).",
     "info": "Chance quality (xG per shot) runs left-to-right; conversion (goals ÷ "
             "shots) bottom-to-top. Top-right is clinical, top-left lucky, "
             "bottom-right wasteful, bottom-left toothless. Dotted lines mark the "
             "group average on each axis."},
    {"id": "HOW_THEY_DEFEND", "type": "defend", "title": "How they defend",
     "caption": "Defensive volume and its mix, per-90.",
     "info": "Stacked bars split each team's defensive actions per 90 into tackles, "
             "interceptions, clearances and aerials — a taller bar means more "
             "defending, and the segments show how that work is made up.",
     "caveat": "High defensive volume often signals playing without the ball — "
               "more actions is not better defending."},
    {"id": "VOLUME_VS_PENETR", "type": "bubble", "title": "Volume vs penetration",
     "caption": "Total passes against passes into the final third; bubble = accuracy %.",
     "info": "Total passes (x) against passes into the final third (y); the bubble "
             "size is pass accuracy. Teams to the top-right both pass a lot and "
             "penetrate, and a big bubble means they keep the ball while doing it."},
]

VIEW_BY_ID = {v["id"]: v for v in VIEWS}


def _wrap_label(label: str, width: int = 13) -> str:
    """Greedily wrap a multi-word axis label onto <=`width`-char lines with
    <br>, so long labels (e.g. 'Passes into final third') don't run past the
    plot edge on narrow/mobile screens — no extra margins needed."""
    words, lines, cur = label.split(), [], ""
    for w in words:
        if cur and len(cur) + 1 + len(w) > width:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        lines.append(cur)
    return "<br>".join(lines)


def radar_figure(records, view, theme: str = "dark") -> go.Figure:
    series = aggregate.radar_series(records, view["metrics"])
    cmap = _theme_team_color(series["teams"])
    fmap = _theme_team_fill(series["teams"])
    labels = series["axes"] + series["axes"][:1]  # close the loop (full labels)
    theta = [_wrap_label(a) for a in labels]       # wrapped for the angular axis
    fig = go.Figure()
    for t in series["teams"]:
        scaled = series["scaled"][t] + series["scaled"][t][:1]
        raw = series["raw"][t] + series["raw"][t][:1]
        fig.add_trace(go.Scatterpolar(
            r=scaled, theta=theta, name=t, fill="toself",
            fillcolor=fmap[t], line=dict(color=cmap[t], width=2),
            # customdata carries the raw value + the FULL (unwrapped) label so
            # the hover stays clean even though the axis text is wrapped.
            customdata=list(zip(raw, labels)),
            hovertemplate="<b>%{fullData.name}</b><br>%{customdata[1]}: "
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
        margin=dict(l=40, r=40, t=18, b=14), showlegend=False, autosize=True,
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
        font=lay["font"], margin=dict(l=80, r=20, t=18, b=34), autosize=True,
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
        font=lay["font"], margin=dict(l=80, r=28, t=34, b=26), autosize=True,
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
        font=lay["font"], margin=dict(l=12, r=12, t=32, b=6), autosize=True,
        showlegend=False, funnelmode="stack")
    return fig


def _shots_total(r):
    return r.get("shots_on", 0) + r.get("shots_off", 0) + r.get("shots_blocked", 0)


_DEFEND_ACTIONS = [("tackles_succ", "Tackles won"), ("interceptions", "Interceptions"),
                   ("clearances", "Clearances"), ("aerials_won", "Aerials won")]


def defend_figure(records, theme: str = "dark") -> go.Figure:
    teams = [r["team"] for r in records]
    lay = theme_layout(theme)
    fig = go.Figure()
    for key, label in _DEFEND_ACTIONS:
        y = [aggregate.per90(r.get(key, 0.0), r.get("matches_played", 0)) for r in records]
        fig.add_trace(go.Bar(
            x=teams, y=y, name=label, marker=dict(color=DEFEND_COLORS[key]),
            hovertemplate="<b>%{x}</b><br>" + label + " (per 90): %{y:.1f}<extra></extra>"))
    fig.update_layout(
        barmode="stack",
        paper_bgcolor=lay["paper_bgcolor"], plot_bgcolor=lay["plot_bgcolor"],
        font=lay["font"], margin=dict(l=40, r=14, t=28, b=24), autosize=True,
        showlegend=True, legend=dict(orientation="h", y=1.1, font=dict(size=10)),
        xaxis=dict(gridcolor="rgba(0,0,0,0)"),
        yaxis=dict(title="Defensive actions per 90", gridcolor=lay["gridcolor_hint"]))
    return fig


def _pad(lo, hi, frac=0.1):
    span = (hi - lo) or (abs(hi) or 1.0)
    return lo - span * frac, hi + span * frac


def bubble_figure(records, theme: str = "dark", color_map=None) -> go.Figure:
    # Empty-records guard: avoid ValueError on min/max of empty sequences.
    if not records:
        lay = theme_layout(theme)
        return go.Figure(layout=dict(paper_bgcolor=lay["paper_bgcolor"],
                                     plot_bgcolor=lay["plot_bgcolor"], font=lay["font"]))
    teams = [r["team"] for r in records]
    # Anti-shadowing: `theme` param is a string here, not the module.
    # Use _theme_team_color wrapper instead of theme.team_color_map(teams).
    cmap = color_map or _theme_team_color(teams)
    lay = theme_layout(theme)
    xs = [r.get("passes_total", 0.0) for r in records]
    ys = [r.get("passes_final_third", 0.0) for r in records]
    acc = [round(r.get("passes_succ", 0.0) / (r.get("passes_total", 0.0) or 1) * 100, 1)
           for r in records]
    fig = go.Figure(go.Scatter(
        x=xs, y=ys, mode="markers+text", text=teams, textposition="top center",
        marker=dict(size=[a * 0.6 for a in acc], color=[cmap[t] for t in teams],
                    sizemode="diameter", line=dict(width=1, color="rgba(0,0,0,0.3)")),
        customdata=[[a, round(ft / (tp or 1) * 100, 1)]
                    for a, ft, tp in zip(acc, ys, xs)],
        hovertemplate="<b>%{text}</b><br>Total passes: %{x:.0f}<br>"
                      "Into final third: %{y:.0f}<br>Accuracy: %{customdata[0]}%<br>"
                      "Final-third share: %{customdata[1]}%<extra></extra>"))
    fig.update_layout(
        paper_bgcolor=lay["paper_bgcolor"], plot_bgcolor=lay["plot_bgcolor"],
        font=lay["font"], margin=dict(l=46, r=24, t=18, b=32), autosize=True,
        showlegend=False,
        xaxis=dict(title="Total passes", gridcolor=lay["gridcolor_hint"],
                   range=list(_pad(min(xs), max(xs)))),
        yaxis=dict(title="Passes into final third", gridcolor=lay["gridcolor_hint"],
                   range=list(_pad(min(ys), max(ys)))))
    return fig


def build_figure(view, *, records=None, history=None, race_metric="points",
                 frame=0, theme="dark") -> go.Figure:
    t = view["type"]
    teams = [r["team"] for r in (records or [])] or list((history or {}).keys())
    # Anti-shadowing: `theme` param is a string here, not the module.
    # Use _theme_team_color wrapper instead of theme.team_color_map(teams).
    cmap = _theme_team_color(teams)
    if t == "radar":
        return radar_figure(records, view, theme)
    if t == "dumbbell":
        return dumbbell_figure(records, theme)
    if t == "race":
        return race_figure(history or {}, race_metric, frame, theme, color_map=cmap)
    if t == "funnel":
        return funnel_figure(records, theme, color_map=cmap)
    if t == "quadrant":
        return quadrant_figure(records, theme, color_map=cmap)
    if t == "defend":
        return defend_figure(records, theme)
    if t == "bubble":
        return bubble_figure(records, theme, color_map=cmap)
    raise ValueError(f"unknown view type: {t}")


def quadrant_figure(records, theme: str = "dark", color_map=None) -> go.Figure:
    """xG/shot vs conversion % quadrant chart (view 8: QUALITY_VS_CONV)."""
    if not records:
        lay = theme_layout(theme)
        return go.Figure(layout=dict(paper_bgcolor=lay["paper_bgcolor"],
                                     plot_bgcolor=lay["plot_bgcolor"], font=lay["font"]))
    teams = [r["team"] for r in records]
    # Anti-shadowing: `theme` param is a string here, not the module.
    # Use _theme_team_color wrapper instead of theme.team_color_map(teams).
    cmap = color_map or _theme_team_color(teams)
    lay = theme_layout(theme)
    xs, ys, txt, cols, cd = [], [], [], [], []
    for r in records:
        st = _shots_total(r) or 1
        xq = round(r.get("xg", 0.0) / st, 3)
        yc = round(r.get("goals", 0) / st * 100, 1)
        xs.append(xq); ys.append(yc); txt.append(r["team"])
        cols.append(cmap[r["team"]])
        cd.append([r.get("goals", 0), _shots_total(r)])
    fig = go.Figure(go.Scatter(
        x=xs, y=ys, mode="markers+text", text=txt, textposition="top center",
        marker=dict(color=cols, size=16),
        customdata=cd,
        hovertemplate="<b>%{text}</b><br>xG/shot: %{x:.3f}<br>"
                      "Conversion: %{y:.1f}%<br>Goals %{customdata[0]} / "
                      "Shots %{customdata[1]}<extra></extra>"))
    mx = sum(xs) / len(xs); my = sum(ys) / len(ys)
    fig.add_vline(x=mx, line=dict(color=lay["gridcolor_hint"], dash="dot"))
    fig.add_hline(y=my, line=dict(color=lay["gridcolor_hint"], dash="dot"))
    for x, y, t in [(max(xs), max(ys), "clinical"), (min(xs), max(ys), "lucky"),
                    (max(xs), min(ys), "wasteful"), (min(xs), min(ys), "toothless")]:
        fig.add_annotation(x=x, y=y, text=t, showarrow=False,
                           opacity=0.4, font=dict(size=10))
    fig.update_layout(
        paper_bgcolor=lay["paper_bgcolor"], plot_bgcolor=lay["plot_bgcolor"],
        font=lay["font"], margin=dict(l=46, r=24, t=18, b=32), autosize=True,
        showlegend=False,
        xaxis=dict(title="xG per shot (chance quality)", gridcolor=lay["gridcolor_hint"]),
        yaxis=dict(title="Conversion % (goals ÷ shots)", gridcolor=lay["gridcolor_hint"]))
    return fig
