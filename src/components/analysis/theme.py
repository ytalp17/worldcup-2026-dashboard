from __future__ import annotations

# Fixed team palette (group-seeding order). A team keeps its color across all
# 10 views. Colors and 0.15-alpha fills come straight from the spec.
TEAM_COLORS = ["#534AB7", "#1D9E75", "#D85A30", "#378ADD"]
TEAM_FILLS = [
    "rgba(83,74,183,0.15)",
    "rgba(29,158,117,0.15)",
    "rgba(216,90,48,0.15)",
    "rgba(55,138,221,0.15)",
]

# Fixed action->color mapping for HOW_THEY_DEFEND (consistent across teams).
DEFEND_COLORS = {
    "tackles_succ": "#1D9E75",
    "interceptions": "#378ADD",
    "clearances": "#EF9F27",
    "aerials_won": "#D85A30",
}

# FINISHING dumbbell colors.
DUMBBELL = {"xg": "#888780", "goals": "#185FA5", "over": "#1D9E75", "under": "#D85A30"}


def team_color_map(teams: list[str]) -> dict[str, str]:
    """Team -> hex color, assigned in the given order, cycling if >4 teams."""
    return {t: TEAM_COLORS[i % len(TEAM_COLORS)] for i, t in enumerate(teams)}


def team_fill_map(teams: list[str]) -> dict[str, str]:
    """Team -> rgba fill, assigned in the given order, cycling if >4 teams."""
    return {t: TEAM_FILLS[i % len(TEAM_FILLS)] for i, t in enumerate(teams)}


def plotly_layout(theme: str = "dark", **overrides) -> dict:
    """Base layout kwargs shared by every figure: transparent background,
    theme-aware text/grid colors, tight margins, autosize, clean hover."""
    dark = theme != "light"
    fg = "#E9ECEF" if dark else "#1A1B1E"
    grid = "rgba(255,255,255,0.10)" if dark else "rgba(0,0,0,0.10)"
    base = dict(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=fg, size=10),
        margin=dict(l=40, r=20, t=10, b=30),
        autosize=True,
        showlegend=False,  # views render a slim custom legend strip instead
        hoverlabel=dict(bgcolor="#23262B" if dark else "#FFFFFF",
                        font_color=fg, bordercolor=grid),
        colorway=TEAM_COLORS,
        gridcolor_hint=grid,  # consumed by view builders for axis grid color
    )
    base.update(overrides)
    return base
