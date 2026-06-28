"""A modern spotlight "how to use this dashboard" walkthrough.

The tour is a guided, step-by-step overlay that dims the screen and spotlights
one real element at a time (the map, each control, the mode switch, the team
dashboards) with a floating card describing it. The step *data* lives here in
Python (single source of truth, unit-tested); the imperative engine that
positions the spotlight and steps through the sequence lives in
``assets/tour.js`` (loaded automatically by Dash) and reads these steps from
the ``tour-steps`` store.

Each step is a dict:
  - ``id``     stable identifier (for keys/debugging)
  - ``title``  short heading shown in the card
  - ``body``   one or two sentences explaining the feature
  - ``target`` CSS selector of the element to spotlight, or ``None`` to show a
               centered card over a full dim (used for the welcome / finish)
  - ``mode``   which app mode must be active for the target to exist:
               ``"time"`` (calendar + controls) or ``"team"`` (team dashboard),
               or ``None`` when it doesn't matter. The engine flips the mode
               switch as needed and restores the original mode when the tour
               ends.
"""
from __future__ import annotations

import dash_mantine_components as dmc
from dash import dcc, html
from dash_iconify import DashIconify

# Ordered walkthrough. Time-mode steps first (map, calendar, the four controls,
# theme), then the hand-off to Team mode and its dashboards, then a sign-off.
TOUR_STEPS: list[dict] = [
    {
        "id": "welcome",
        "title": "Welcome to the World Cup 2026 dashboard",
        "body": "The interactive map is the heart of everything. Pan across the "
                "three host nations — USA, Mexico and Canada — where each marker "
                "is one of the 16 host stadiums. Live matches pulse and show "
                "their score right on the map.",
        "target": "#map-container",
        "mode": "time",
    },
    {
        "id": "calendar",
        "title": "Travel through match days",
        "body": "Scrub the match-day calendar at the top to jump between dates. "
                "The stadiums hosting games that day light up with a pulse, so "
                "you always see where the action is.",
        "target": "#calendar-wrapper",
        "mode": "time",
    },
    {
        "id": "tournament-stats",
        "title": "Tournament Stats",
        "body": "Open the trophy for live leaderboards — top scorers, assists "
                "and team leaders across the whole tournament, with full group "
                "standings.",
        "target": "#tournament-control",
        "mode": "time",
    },
    {
        "id": "travel-map",
        "title": "Team Travel Map",
        "body": "Pick teams here to draw their journeys between host cities on "
                "the map, with total distance travelled — a feel for who logs "
                "the most air miles.",
        "target": "#filter-control",
        "mode": "time",
    },
    {
        "id": "third-place",
        "title": "Third-Place Ranking",
        "body": "The eight best group runners-up advance. This ranking tracks "
                "exactly which third-placed teams are in the knockout picture.",
        "target": "#third-place-control",
        "mode": "time",
    },
    {
        "id": "knockout",
        "title": "Tournament Knockout",
        "body": "Follow the bracket from the Round of 32 all the way to the "
                "Final, two stages at a time, updating as results land.",
        "target": "#knockout-control",
        "mode": "time",
    },
    {
        "id": "theme",
        "title": "Light or dark, your call",
        "body": "Flip this switch to recolour the entire dashboard — every map, "
                "chart and card follows your choice.",
        "target": "#color-scheme-toggle",
        "mode": "time",
    },
    {
        "id": "mode-switch",
        "title": "Switch to Team view",
        "body": "This is the big one: flip from Time view to Team view for a "
                "full, per-nation dashboard. Let's take a look — we'll switch it "
                "for you now.",
        "target": "#mode-toggle",
        "mode": "time",
    },
    {
        "id": "team-picker",
        "title": "Choose any nation",
        "body": "Step through the qualified teams here. Each one loads its own "
                "dashboard: squad, recent form, key stats and an estimated "
                "starting XI.",
        "target": "#carousel-wrapper",
        "mode": "team",
    },
    {
        "id": "deep-analysis",
        "title": "Deep Analysis",
        "body": "Compare every team in the group with radar and race charts. "
                "Hover the ⓘ for how to read each chart, or expand it for a "
                "full-screen view.",
        "target": "#analysis-panel",
        "mode": "team",
    },
    {
        "id": "shoot-map",
        "title": "The Shoot Map",
        "body": "See where a team takes its shots across the goal mouth. Click "
                "any zone to pull up every shot from that spot — who, when and "
                "the outcome.",
        "target": "#goal-mouth-graph",
        "mode": "team",
    },
    {
        "id": "finish",
        "title": "You're all set",
        "body": "That's the tour! Tap the light bulb in the corner any time to "
                "run it again. Enjoy the World Cup.",
        "target": None,
        "mode": "time",
    },
]


def _tour_card() -> dmc.Paper:
    """The floating step card. The engine fills the text/progress and positions
    it; the structure (DMC) is rendered once here."""
    return dmc.Paper(
        dmc.Stack(
            [
                dmc.Text(id="tour-card-title", fw=700, size="md"),
                dmc.Text(id="tour-card-body", size="sm", c="dimmed"),
                html.Div(id="tour-card-progress", className="tour-dots"),
                # Controls on their own line, centered beneath the dots.
                dmc.Group(
                    [
                        dmc.Button("Skip", id="tour-skip",
                                   variant="subtle", color="gray", size="xs"),
                        dmc.Button("Back", id="tour-back",
                                   variant="default", size="xs"),
                        dmc.Button("Next", id="tour-next",
                                   variant="filled", size="xs"),
                    ],
                    justify="center", gap="xs", wrap="nowrap",
                ),
            ],
            gap="sm",
        ),
        id="tour-card",
        className="tour-card",
        shadow="lg",
        radius="md",
        p="md",
        withBorder=True,
    )


def build_tour() -> html.Div:
    """The whole tour widget: the dim/spotlight overlay (hidden until started),
    the floating step card, and the step-data store. Mounted once at app level;
    driven entirely client-side from ``assets/tour.js``."""
    overlay = html.Div(
        [
            html.Div(id="tour-spotlight", className="tour-spotlight"),
            _tour_card(),
        ],
        id="tour-overlay",
        className="tour-overlay",
        style={"display": "none"},
    )
    return html.Div(
        [
            overlay,
            dcc.Store(id="tour-steps", data=TOUR_STEPS),
            # Throwaway sinks for the clientside init/start callbacks.
            dcc.Store(id="tour-init-sink"),
            dcc.Store(id="tour-start-sink"),
        ],
        id="tour-root",
    )
