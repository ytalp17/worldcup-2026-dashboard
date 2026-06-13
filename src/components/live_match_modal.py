from __future__ import annotations

import dash_mantine_components as dmc


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


def _timeline_tab(events: list[dict]):
    if not events:
        return dmc.Text("No events yet.", c="dimmed", size="sm")
    items = [
        dmc.Group(
            [
                dmc.Badge(f"{e['minute']}'", variant="light", color="blue", miw=40),
                dmc.Text(
                    f"{e['type']} — {e['player']} ({e['team']})",
                    size="sm",
                ),
            ],
            gap="xs",
        )
        for e in events
    ]
    return dmc.Stack(items, gap=6)


def _lineups_tab(lineups: dict, home_name: str, away_name: str):
    if not lineups:
        return dmc.Text("Lineups not available.", c="dimmed", size="sm")

    home = lineups.get("home", {})
    away = lineups.get("away", {})

    if not home.get("starters") and not away.get("starters"):
        return dmc.Text("Lineups not available.", c="dimmed", size="sm")

    def _team_col(data: dict, team_name: str):
        formation = data.get("formation", "")
        starters = data.get("starters", [])
        header = dmc.Text(
            f"{team_name} · {formation}" if formation else team_name,
            fw=700,
            size="sm",
        )
        player_rows = [
            dmc.Text(f"{p['number']}  {p['name']}", size="sm")
            for p in starters
        ]
        return dmc.Stack([header] + player_rows, gap=4)

    return dmc.SimpleGrid(
        [
            _team_col(home, home_name),
            _team_col(away, away_name),
        ],
        cols=2,
        spacing="md",
    )


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


def build_modal() -> dmc.Modal:
    """Mount the closed modal shell; the open callback fills ``children`` on demand."""
    return dmc.Modal(
        id="live-match-modal",
        opened=False,
        size="lg",
        zIndex=3000,
        children=modal_body(None, [], {}, {}),
    )
