from __future__ import annotations

import dash_mantine_components as dmc
from dash import html

from src.components.lineup_pitch import build_lineup_pitch


# ---------------------------------------------------------------------------
# Curated stat set definition
# Each entry: (label, home_raw_fn, away_raw_fn, home_display_fn, away_display_fn)
# ---------------------------------------------------------------------------

def _pct(val: float) -> str:
    return f"{round(val * 100)}%"


def _int(val: float) -> str:
    return str(int(val))


def _xg(val: float) -> str:
    return f"{val:.2f}"


def _pass_acc(s: dict) -> float:
    total = s.get("Total passes", 0) or 0
    if total == 0:
        return 0.0
    return s.get("Successful passes", 0) / total


def _pass_acc_display(s: dict) -> str:
    return f"{round(_pass_acc(s) * 100)}%"


_CURATED: list[tuple] = [
    # (label, raw_key_or_fn, display_fn)
    # Format: (label, raw_value_fn, display_fn)
    ("Possession",
     lambda s: s.get("Possession", 0),
     lambda s: _pct(s.get("Possession", 0))),
    ("Shots",
     lambda s: int(s.get("Shots on target", 0) + s.get("Shots off target", 0) + s.get("Blocked shots", 0)),
     lambda s: _int(s.get("Shots on target", 0) + s.get("Shots off target", 0) + s.get("Blocked shots", 0))),
    ("Shots on target",
     lambda s: s.get("Shots on target", 0),
     lambda s: _int(s.get("Shots on target", 0))),
    ("xG",
     lambda s: s.get("Expected Goals", 0),
     lambda s: _xg(s.get("Expected Goals", 0))),
    ("Passes",
     lambda s: s.get("Total passes", 0),
     lambda s: _int(s.get("Total passes", 0))),
    ("Pass accuracy",
     _pass_acc,
     _pass_acc_display),
    ("Fouls",
     lambda s: s.get("Fouls", 0),
     lambda s: _int(s.get("Fouls", 0))),
    ("Corners",
     lambda s: s.get("Corners", 0),
     lambda s: _int(s.get("Corners", 0))),
    ("Offsides",
     lambda s: s.get("Offsides", 0),
     lambda s: _int(s.get("Offsides", 0))),
    ("Yellow cards",
     lambda s: s.get("Yellow cards", 0),
     lambda s: _int(s.get("Yellow cards", 0))),
    ("Red cards",
     lambda s: s.get("Red cards", 0),
     lambda s: _int(s.get("Red cards", 0))),
]

# Keys that must be present for a stat to show (if both sides have none, skip)
_PRESENCE_KEYS: dict[str, list[str]] = {
    "Possession": ["Possession"],
    "Shots": ["Shots on target", "Shots off target", "Blocked shots"],
    "Shots on target": ["Shots on target"],
    "xG": ["Expected Goals"],
    "Passes": ["Total passes"],
    "Pass accuracy": ["Total passes", "Successful passes"],
    "Fouls": ["Fouls"],
    "Corners": ["Corners"],
    "Offsides": ["Offsides"],
    "Yellow cards": ["Yellow cards"],
    "Red cards": ["Red cards"],
}


def stat_rows(statistics: dict, home: str, away: str) -> list[tuple]:
    """Return curated stat comparison rows.

    Each tuple: ``(label, home_display, away_display, home_is_larger_bool)``
    Skips rows where both teams have all relevant keys absent from ``statistics``.
    """
    if not statistics:
        return []

    hs = statistics.get(home, {})
    aws = statistics.get(away, {})
    rows: list[tuple] = []

    for label, raw_fn, display_fn in _CURATED:
        presence_keys = _PRESENCE_KEYS.get(label, [])
        home_missing = all(k not in hs for k in presence_keys)
        away_missing = all(k not in aws for k in presence_keys)
        if home_missing and away_missing:
            continue

        home_raw = raw_fn(hs)
        away_raw = raw_fn(aws)
        home_display = display_fn(hs)
        away_display = display_fn(aws)
        home_is_larger = home_raw > away_raw

        rows.append((label, home_display, away_display, home_is_larger))

    return rows


# ---------------------------------------------------------------------------
# Score helpers
# ---------------------------------------------------------------------------

def _score_line(m: dict) -> str:
    h, a = m.get("home_score"), m.get("away_score")
    score = f"{h} - {a}" if h is not None else "vs"
    return f"{m['home']}  {score}  {m['away']}"


# ---------------------------------------------------------------------------
# Tab content builders
# ---------------------------------------------------------------------------

def _stats_tab(statistics: dict, home_name: str, away_name: str):
    rows = stat_rows(statistics, home_name, away_name)
    if not rows:
        return dmc.Text("No statistics available yet.", c="dimmed", size="sm")

    items = []
    for label, home_val, away_val, home_larger in rows:
        home_variant = "filled" if home_larger else "light"
        home_color = "blue" if home_larger else "gray"
        away_variant = "filled" if not home_larger and home_val != away_val else "light"
        away_color = "blue" if not home_larger and home_val != away_val else "gray"
        items.append(
            dmc.Group(
                [
                    dmc.Badge(home_val, variant=home_variant, color=home_color, miw=48),
                    dmc.Text(label, size="xs", c="dimmed", style={"flexGrow": 1, "textAlign": "center"}),
                    dmc.Badge(away_val, variant=away_variant, color=away_color, miw=48),
                ],
                justify="space-between",
                gap="xs",
            )
        )
    return dmc.Stack(items, gap=6)


# ---------------------------------------------------------------------------
# Timeline event styling: emoji glyph + accent colour per event type.
# Keyed on the exact API ``type`` strings, with a fuzzy fallback for the
# variant spellings the live feed sometimes sends ("substitution",
# "VAR Goal Cancelled - ...", etc.).
# ---------------------------------------------------------------------------

_EVENT_VISUALS: dict[str, tuple[str, str]] = {
    "Goal": ("⚽", "green"),
    "Penalty": ("🎯", "green"),
    "Own Goal": ("🥅", "red"),
    "Yellow Card": ("🟨", "yellow"),
    "Red Card": ("🟥", "red"),
    "Substitution": ("🔄", "blue"),
    "VAR": ("📺", "grape"),
}
_DEFAULT_VISUAL: tuple[str, str] = ("🔹", "gray")


def event_visual(event_type: str) -> tuple[str, str]:
    """Return ``(emoji, mantine_color)`` for a timeline event type.

    Exact matches win; otherwise a fuzzy pass maps the feed's variant
    spellings onto the canonical set. Unknown types get a neutral default.
    """
    key = (event_type or "").strip()
    if key in _EVENT_VISUALS:
        return _EVENT_VISUALS[key]

    low = key.lower()
    if "substitut" in low:
        return _EVENT_VISUALS["Substitution"]
    if low.startswith("var") or " var" in low:
        return _EVENT_VISUALS["VAR"]
    if "yellow" in low:
        return _EVENT_VISUALS["Yellow Card"]
    if "red" in low:
        return _EVENT_VISUALS["Red Card"]
    if "own goal" in low:
        return _EVENT_VISUALS["Own Goal"]
    if "penalty" in low:
        return _EVENT_VISUALS["Penalty"]
    if "goal" in low:
        return _EVENT_VISUALS["Goal"]
    return _DEFAULT_VISUAL


def _event_card(e: dict):
    emoji, color = event_visual(e.get("type", ""))
    etype = e.get("type", "")
    player = e.get("player", "")
    team = e.get("team", "")
    is_highlight = color in ("green", "red")  # goals & dismissals stand out
    subline = " · ".join(part for part in (etype, team) if part)
    return dmc.Paper(
        dmc.Group(
            [
                dmc.Badge(f"{e.get('minute', 0)}'", variant="light",
                          color=color, miw=42, radius="sm"),
                dmc.Text(emoji, className="tl-event__emoji"),
                dmc.Stack(
                    [
                        dmc.Text(player or etype or "—",
                                 fw=700 if is_highlight else 600,
                                 size="sm", lineClamp=1),
                        dmc.Text(subline, size="xs", c="dimmed", lineClamp=1),
                    ],
                    gap=0,
                    style={"flexGrow": 1, "minWidth": 0},
                ),
            ],
            gap="sm",
            wrap="nowrap",
            align="center",
        ),
        withBorder=True,
        radius="md",
        p="xs",
        className="tl-event-card",
        style={"borderLeft": f"3px solid var(--mantine-color-{color}-6)"},
    )


def _timeline_tab(events: list[dict]):
    if not events:
        return dmc.Text("No events yet.", c="dimmed", size="sm")
    return dmc.Stack(
        [_event_card(e) for e in events],
        gap="xs",
        className="tl-stack",
    )


def _lineups_tab(lineups: dict, home_name: str, away_name: str):
    if not lineups:
        return dmc.Text("Lineups not available.", c="dimmed", size="sm")

    pitch = build_lineup_pitch(lineups)
    if pitch is None:
        return dmc.Text("Lineups not available.", c="dimmed", size="sm")

    home = lineups.get("home", {})
    away = lineups.get("away", {})

    # A compact team · formation caption flanking the centre, blue (home) left
    # and orange (away) right, so the colour coding on the pitch is legible.
    def _caption(data: dict, team_name: str, side: str, justify: str):
        formation = data.get("formation", "")
        label = f"{team_name} · {formation}" if formation else team_name
        return dmc.Group(
            [dmc.Box(className=f"lu-key__dot lu-key__dot--{side}"),
             dmc.Text(label, size="sm", fw=600)],
            gap=6, align="center", justify=justify, wrap="nowrap",
        )

    legend = dmc.Group(
        [
            _caption(home, home_name, "home", "flex-start"),
            _caption(away, away_name, "away", "flex-end"),
        ],
        justify="space-between",
        align="center",
        wrap="nowrap",
        className="lu-legend",
    )

    return dmc.Stack([legend, pitch], gap="xs")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def modal_body(
    match: dict | None,
    events: list[dict],
    statistics: dict,
    lineups: dict,
):
    """Build the inner body of the live-match detail modal.

    Returns a Dash component. ``match=None`` renders a placeholder.
    """
    if not match:
        return dmc.Text("No match selected.")

    home_name = match.get("home", "")
    away_name = match.get("away", "")

    state = match.get("state", "")
    clock = match.get("clock")
    sub = state.upper() + (f" · {clock}'" if clock is not None else "")

    header = dmc.Stack(
        [
            dmc.Title(_score_line(match), order=3),
            dmc.Group(
                [
                    dmc.Badge(
                        sub or "—",
                        color="red" if match.get("is_live") else "gray",
                        variant="filled" if match.get("is_live") else "light",
                    ),
                    dmc.Text(match.get("venue") or "", size="sm", c="dimmed"),
                ],
                gap="sm",
            ),
        ],
        gap="xs",
    )

    tabs = dmc.Tabs(
        [
            dmc.TabsList(
                [
                    dmc.TabsTab("Stats", value="stats"),
                    dmc.TabsTab("Timeline", value="timeline"),
                    dmc.TabsTab("Lineups", value="lineups"),
                ]
            ),
            dmc.TabsPanel(
                _stats_tab(statistics, home_name, away_name),
                value="stats",
                pt="md",
            ),
            dmc.TabsPanel(
                _timeline_tab(events),
                value="timeline",
                pt="md",
            ),
            dmc.TabsPanel(
                _lineups_tab(lineups, home_name, away_name),
                value="lineups",
                pt="md",
            ),
        ],
        value="stats",
        color="blue",
    )

    return dmc.Stack([header, dmc.Divider(my="sm"), tabs], gap="xs")


def loading_body():
    """Skeleton placeholder shaped like the real body.

    Shown the instant the modal opens (Phase 1), before the live data arrives
    (Phase 2). Mimicking the layout — title, status badge, tab strip, rows —
    avoids a spinner-on-blank flash and a layout jump when content lands.
    """
    return dmc.Stack(
        [
            dmc.Skeleton(height=26, width="58%", radius="sm"),          # title
            dmc.Skeleton(height=18, width=120, radius="xl"),           # status badge
            dmc.Divider(my="sm"),
            dmc.Group(
                [dmc.Skeleton(height=20, width=70, radius="sm") for _ in range(3)],
                gap="sm",
            ),                                                          # tab strip
            dmc.Stack(
                [dmc.Skeleton(height=34, radius="md") for _ in range(5)],
                gap="xs",
                mt="xs",
            ),                                                          # rows
        ],
        gap="xs",
        className="live-modal-loading",
    )


def build_modal() -> dmc.Modal:
    """Mount the closed modal shell.

    The body lives in a stable ``#live-modal-content`` container so two
    callbacks can write it: Phase 1 drops in the loading skeleton instantly,
    Phase 2 swaps in the fetched match detail.
    """
    return dmc.Modal(
        id="live-match-modal",
        opened=False,
        size="lg",
        zIndex=3000,
        children=html.Div(modal_body(None, [], {}, {}), id="live-modal-content"),
    )
