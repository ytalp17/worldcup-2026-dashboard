#!/usr/bin/env python3
"""
World Cup 2026 — estimated starting-XI pitch images, one per team per theme.

Input : assets/data/estimated_starting_eleven.json (produced by
        scrape_mylineups.py): {slug: {name, formation, coach, xi:[[surname,num]]}}.
        Players are GK -> defence -> midfield -> attack, matching the order
        mplsoccer's get_formation() returns position slots in.
Output: assets/pitches/<slug>-dark.png and <slug>-light.png — horizontal pitch
        (GK left -> attack right) with a shirt number inside each node and the
        surname beneath it. Transparent margins so the bento card shows through;
        the team name + formation are rendered by the card header in the app, so
        the image itself carries no title.

Build-time only (mplsoccer + matplotlib are dev dependencies); the Dash app
just serves the generated PNGs as static assets.

Usage:
    pip install mplsoccer            # or: requirements-dev.txt
    python wc2026_pitches.py
"""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless
import matplotlib.pyplot as plt  # noqa: E402
from mplsoccer import Pitch  # noqa: E402

DATA = Path("assets/data/estimated_starting_eleven.json")
OUTDIR = Path("assets/pitches")

# Two palettes so the card honours the app's dark/light switch. Margins are
# saved transparent; these colours apply to the pitch surface, lines, nodes and
# on-pitch text (which always sits on the green, so white reads in both).
THEMES = {
    "dark": {
        "pitch_color": "#16241c",
        "line_color": "#6f9d87",
        "node_color": "#23a35f",
        "gk_color": "#e0a526",
        "text_color": "#ffffff",
        "fig_color": "#16241c",
        "number_color": "#06120b",  # dark — reads on the bright-green/gold nodes
    },
    "light": {
        "pitch_color": "#2f8a4e",
        "line_color": "#eafff2",
        "node_color": "#0f5d2c",
        "gk_color": "#c9760a",
        "text_color": "#ffffff",
        "fig_color": "#2f8a4e",
        "number_color": "#ffffff",  # light — reads on the dark-green/gold nodes
    },
}


def render_team(key: str, data: dict, theme: dict, name: str, outdir) -> Path:
    """Render one team's pitch for one theme; return the written PNG path."""
    outdir = Path(outdir)
    pitch = Pitch(
        pitch_type="opta",
        pitch_color=theme["pitch_color"],
        line_color=theme["line_color"],
        linewidth=1.4,
        line_zorder=1,
    )
    fig, ax = pitch.draw(figsize=(10, 7))
    fig.set_facecolor(theme["fig_color"])
    ax.set_facecolor(theme["pitch_color"])

    formation = data["formation"]
    xi = data["xi"]
    positions = pitch.get_formation(formation)
    if len(xi) != len(positions):
        raise ValueError(
            f"{key}: {len(xi)} players but formation {formation} "
            f"expects {len(positions)}"
        )

    colors = [theme["gk_color"] if i == 0 else theme["node_color"]
              for i in range(len(xi))]
    pitch.formation(
        formation, kind="scatter", ax=ax,
        s=2100, color=colors, edgecolors="white", linewidth=2.4, zorder=3,
    )

    # Shirt number centred in each node; surname just beneath it. On a
    # horizontal pitch "beneath" is a smaller y.
    for pos, (surname, num) in zip(positions, xi):
        pitch.annotate(str(num), xy=(pos.x, pos.y), ax=ax, ha="center",
                       va="center", color=theme["number_color"], fontsize=23,
                       fontweight="bold", zorder=4)
        pitch.annotate(surname, xy=(pos.x, pos.y - 7.8), ax=ax, ha="center",
                       va="top", color=theme["text_color"], fontsize=17,
                       fontweight="bold", zorder=4)

    outdir.mkdir(parents=True, exist_ok=True)
    out = outdir / f"{key}-{name}.png"
    fig.savefig(out, dpi=150, facecolor=theme["fig_color"],
                bbox_inches="tight", pad_inches=0.06)
    plt.close(fig)
    return out


def main():
    raw = json.loads(DATA.read_text(encoding="utf-8"))
    made = 0
    for slug, data in raw.items():
        for name, theme in THEMES.items():
            render_team(slug, data, theme, name, OUTDIR)
            made += 1
        print(f"  ✓ {data['name']:<24} {data['formation']}")
    print(f"\nGenerated {made} pitch images in ./{OUTDIR}/ "
          f"({len(raw)} teams × {len(THEMES)} themes).")


if __name__ == "__main__":
    main()
