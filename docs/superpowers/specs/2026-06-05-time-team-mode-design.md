# Time / Team Mode + Team Carousel — Design

**Date:** 2026-06-05
**Status:** Approved (pending written-spec review)

## Goal

Add a header **mode switch** — in the same spirit as the existing light/dark theme
switch — that toggles the app between **Time mode** (today's behavior) and **Team
mode** (new). In Team mode the header-center calendar is replaced by a **team
carousel**: three team logos at once, the centered one full-brightness and the two
neighbours dimmed, scrolling endlessly through all 48 teams in alphabetical order.
The centered team drives the map: its group-stage **flow lines** are drawn and its
three group-stage **stadiums pulse**.

## Behavior Decisions (locked)

| Decision | Choice |
|---|---|
| What Team mode does to the map | Draw the centered team's flow lines **and** pulse its 3 stadiums |
| Carousel vs filter drawer | **Clean separation**: filter pin/drawer only in Time mode; carousel only in Team mode |
| Mode switch control | `dmc.Switch` (icon switch) on the right, beside the theme toggle |
| Team order | Alphabetical A→Z (single flat sequence of all 48) |
| Wrap-around | Endless loop (modulo); arrows never disabled |
| Default mode | Time (unchecked) — preserves current default behavior |
| Center logo click | No-op (already selected); only neighbours/arrows navigate |

Out of scope (YAGNI): touch-swipe gestures, a team-detail drawer on logo click,
animated slide transitions beyond a simple CSS opacity/scale.

## Architecture

The mode switch's `checked` value is the **single source of truth** for the active
mode (`checked == True` ⇒ Team mode). Three things react to it:

1. **Header center** — both the calendar and the carousel are always mounted; a
   callback toggles each one's `style.display` so only the active widget shows.
2. **Map layers** — the existing `flow-layer` and `pulse-layer` callbacks become
   *mode-aware*. In Time mode they read the calendar/filter as today; in Team mode
   they read the carousel's centered team.
3. **Filter pin** — moved into its own `LayerGroup`; a callback shows the pin in
   Time mode and empties the layer in Team mode (and closes the filter drawer when
   entering Team mode).

### New / changed files

| File | Responsibility |
|---|---|
| `src/components/team_carousel.py` | **New.** Carousel construction + pure helpers (`team_order`, `window`, `advance`) and the centered-team resolver. |
| `src/components/mode_switch.py` | **New.** The `dmc.Switch` for Time/Team, mirroring `theme_toggle`. |
| `src/data/flows.py` | Add pure helper `team_cities(team_flow, stadium_to_city)`. |
| `src/components/map_view.py` | Wrap the filter pin in `LayerGroup id="filter-pin-layer"`. |
| `src/components/layout.py` | Mount calendar + carousel in the center Box; add mode switch to the right zone; add the carousel-index `dcc.Store`. |
| `app.py` | Mode-aware `flow-layer` / `pulse-layer` callbacks; center-visibility callback; carousel navigation + render callbacks; filter-pin visibility callback. |
| `assets/styles.css` | Carousel layout + brightness/ring styling (themed cyan/rose). |

## Component: Team Carousel (`src/components/team_carousel.py`)

### Data + pure functions (tested first, no Dash)

```python
def team_order(team_flows: dict[str, TeamFlow]) -> list[str]:
    """All teams, alphabetical A→Z (case-insensitive on the raw team name)."""
    return sorted(team_flows.keys(), key=str.casefold)

def advance(index: int, delta: int, n: int) -> int:
    """Move the carousel index with wrap-around (endless loop)."""
    return (index + delta) % n

def window(teams: list[str], index: int) -> tuple[str, str, str]:
    """(prev, center, next) team names with wrap-around. Requires len>=1."""
    n = len(teams)
    return (teams[(index - 1) % n], teams[index % n], teams[(index + 1) % n])

def center_team(teams: list[str], index: int) -> str:
    return teams[index % len(teams)]
```

### Logo source

Logos already exist named exactly per team: `assets/country_logos/{team}.svg`.
The component builds the src via `app.get_asset_url(f"country_logos/{team}.svg")`
(an `asset_url` callable is passed into the builder so the module stays free of a
hard Dash-app dependency).

### Structure / IDs

```
Box  (carousel root, id="team-carousel")
├── ActionIcon  id="carousel-prev"     (‹ — index −1)
├── UnstyledButton id="carousel-logo-prev"  → dim Image (prev team)   (index −1)
├── Stack (center)  → bright Image + ring (center team) + Text (team name)
│       id="carousel-logo-center"  (no-op click)
├── UnstyledButton id="carousel-logo-next"  → dim Image (next team)   (index +1)
└── ActionIcon  id="carousel-next"     (› — index +1)
```

`dcc.Store id="carousel-index"` (int, default 0) holds the current index. Lives in
the layout so it persists regardless of which widget is visible. `persistence=True`
on both the store and the mode switch.

## Map: Mode-Aware Layers

### Pure deciders (tested first, no Dash)

`team_cities` (in `flows.py`):

```python
def team_cities(team_flow: TeamFlow, stadium_to_city: dict[str, str]) -> set[str]:
    """The set of host cities a team plays its group-stage matches in."""
    return {stadium_to_city[s.stadium_name] for s in team_flow.stops
            if s.stadium_name in stadium_to_city}
```

Decider helpers (in `app.py`, factored as module-level pure functions so they are
unit-testable without firing callbacks):

```python
def flow_children_for_mode(team_mode, filter_value, center):
    # Team mode → single centered team's flow; Time mode → the multiselect.
    selected = [center] if team_mode else filter_value
    return flows_for(selected, TEAM_FLOWS)

def pulse_children_for_mode(team_mode, selected_date, center):
    # Team mode → centered team's cities; Time mode → calendar date's cities.
    if team_mode:
        active = team_cities(TEAM_FLOWS[center], STADIUM_TO_CITY) if center else set()
    else:
        active = _active_cities_for_date(selected_date)   # existing date logic
    return pulse_markers(VENUES, active)
```

### Callback wiring (in `app.py`)

- **Center visibility:** `Input mode-toggle.checked` → `Output calendar-wrapper.style`,
  `Output carousel-wrapper.style` (toggle `display: none`).
- **Carousel navigation:** Inputs = `carousel-prev.n_clicks`, `carousel-next.n_clicks`,
  `carousel-logo-prev.n_clicks`, `carousel-logo-next.n_clicks`; State = `carousel-index.data`.
  Uses `ctx.triggered_id` to pick `advance(index, ±1, 48)` → `Output carousel-index.data`.
- **Carousel render:** `Input carousel-index.data` → `Output team-carousel-body.children`
  (rebuild the three logos + center label from `window(...)`).
- **flow-layer:** Inputs = `mode-toggle.checked`, `team-filter.value`, `carousel-index.data`
  → `flow_children_for_mode(...)`. (Replaces the current flow callback; legend output
  for the filter drawer stays driven by `team-filter.value` as today.)
- **pulse-layer:** Inputs = `mode-toggle.checked`, `match-calendar.value`,
  `carousel-index.data` → `pulse_children_for_mode(...)`. (Replaces the current pulse
  callback.)
- **Filter-pin visibility:** `Input mode-toggle.checked` → `Output filter-pin-layer.children`
  ([pin] in Time mode, [] in Team mode) and `Output filter-drawer.opened` (False when
  entering Team mode).

The legend callback keeps its own output; to avoid duplicate outputs the flow + legend
are split: `flow-layer.children` from the mode-aware callback, `filter-legend.children`
from a callback on `team-filter.value` (Team mode doesn't touch the filter legend).

## Styling (`assets/styles.css`)

- `.team-carousel` — fl/ex row, centered, gap, fixed height matching the calendar's
  footprint so the header doesn't reflow on mode switch.
- `.carousel-logo` — base logo wrapper; `.carousel-logo--side` dimmed (`opacity: .45`,
  smaller), `.carousel-logo--center` full opacity, larger, with an accent ring
  (`box-shadow` using the existing `--marker-rgb` cyan/rose accent + glow). Themed via
  the existing `[data-mantine-color-scheme]` selectors.
- Arrows use the accent color; cursor pointer; `user-select: none`.

## Testing (TDD)

Pure functions first (`pytest tests/ -v`, conda base env):

1. `team_order` — returns all 48 teams sorted case-insensitively; stable.
2. `advance` — wraps forward past the end (`advance(47, +1, 48) == 0`) and backward
   past the start (`advance(0, -1, 48) == 47`).
3. `window` — returns correct (prev, center, next) including both wrap edges.
4. `center_team` — returns the indexed team with wrap.
5. `team_cities` — returns the set of cities for a known team's stops; ignores
   unknown stadium names.
6. `flow_children_for_mode` — Team mode uses `[center]`; Time mode uses the
   multiselect; empty/None inputs yield `[]`.
7. `pulse_children_for_mode` — Team mode pulses the centered team's cities; Time mode
   pulses the date's cities; no center / no date yields no pulses.

Then component/layout construction (builders return the expected DMC tree with the
documented IDs) and, where practical, the visibility/render callback logic via the
pure deciders above.

## Non-Goals / Preserved Behavior

- Time mode is byte-for-byte the current experience (calendar pulses, filter pin,
  filter drawer, leaderboard, theme switch).
- No data files change; no new dependencies (DMC + dash-leaflet + dash-iconify only).
- Map bounds, tiles, stadium click→drawer behavior unchanged.
