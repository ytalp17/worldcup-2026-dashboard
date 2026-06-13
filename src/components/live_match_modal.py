from __future__ import annotations

import dash_mantine_components as dmc
from dash import html


def _score_line(m: dict) -> str:
    h, a = m.get("home_score"), m.get("away_score")
    score = f"{h} - {a}" if h is not None else "vs"
    return f"{m['home']}  {score}  {m['away']}"


def modal_body(match: dict | None, events: list[dict]):
    """Build the inner body of the live-match detail modal.

    Returns a Dash component that serialises cleanly (no callback needed).
    Empty events list renders a friendly 'No events yet.' message.
    """
    if not match:
        return dmc.Text("No match selected.")

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

    if events:
        timeline = dmc.Stack(
            [
                dmc.Text(
                    f"{e['minute']}'  {e['type']} — {e['player']} ({e['team']})",
                    size="sm",
                )
                for e in events
            ],
            gap=4,
        )
    else:
        timeline = dmc.Text("No events yet.", size="sm", c="dimmed")

    return html.Div([header, dmc.Divider(my="sm"), timeline])


def build_modal() -> dmc.Modal:
    """Mount the closed modal shell; the open callback fills `children` on demand."""
    return dmc.Modal(
        id="live-match-modal",
        opened=False,
        size="lg",
        zIndex=3000,
        children=modal_body(None, []),
    )
