from __future__ import annotations

from collections.abc import Callable

import dash_mantine_components as dmc

from src.data.lineups import StartingEleven, format_formation


def pitch_src(slug: str, asset_url: Callable[[str], str], dark: bool) -> str:
    """Asset URL for a team's pitch PNG in the requested theme."""
    theme = "dark" if dark else "light"
    return asset_url(f"pitches/{slug}-{theme}.png")


def formation_title(lineup: StartingEleven | None) -> str:
    """Header label: '4-3-3 · Argentina' (or '—' when unknown)."""
    if lineup is None:
        return "—"
    return f"{format_formation(lineup.formation)} · {lineup.team}"


def build_formation_panel(
    lineup: StartingEleven | None,
    asset_url: Callable[[str], str],
    dark: bool = True,
) -> dmc.Box:
    """Bento card: a header bar ('Formation' + formation·team) over the pitch
    image. The image id is stable so a callback can swap its src on
    carousel/theme change."""
    # Card header bar: bold "Formation" label left, live formation·team right.
    header = dmc.Group(
        [
            dmc.Text("Formation", fw=700, size="sm"),
            dmc.Text(
                formation_title(lineup),
                id="formation-title",
                size="sm",
                c="dimmed",
            ),
        ],
        justify="space-between",
        align="center",
        wrap="nowrap",
        className="bento-card__header",
    )

    src = pitch_src(lineup.slug, asset_url, dark) if lineup else ""
    image = dmc.Image(
        id="formation-img",
        src=src,
        fit="contain",
        alt="Estimated starting XI",
    )
    body = dmc.Box(image, className="formation-panel__body")
    return dmc.Box([header, body], className="formation-panel")
