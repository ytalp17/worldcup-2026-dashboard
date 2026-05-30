# Team Travel Distance — Design

**Date:** 2026-05-30
**Status:** Approved (design)

## Goal

Show how far each team travels during the group stage — the summed great-circle
distance between its three group-stage stadiums, in chronological order. Distances
are **precomputed offline into a data file**; the app only loads and displays them.

## Definition

- **What is measured:** the path through a team's group-stage venues only — exactly
  the points the flow lines already draw. For 3 venues that is 2 legs. No
  home-country leg, no knockout venues (those are placeholders until results exist).
- **Metric:** great-circle (haversine) distance, Earth radius 6371 km.
- **Units shown:** both km and miles, e.g. `1,840 km / 1,143 mi`. Kilometers is the
  single source of truth (stored); miles are derived at display (`km × 0.621371`).
  Both rounded to whole numbers with thousands separators.

## Architecture

Mirrors the existing data-file patterns (`team_continents.csv`, `altitudes.py`):
the math runs offline in a generator script, the result is committed as a CSV, and
the app loads the CSV with zero runtime math.

### Data layer

**`src/data/flows.py`** — add pure functions (used by the generator script and the
consistency test, NOT at app runtime):

- `haversine_km(lat1, lon1, lat2, lon2) -> float` — great-circle distance, R = 6371 km.
- `path_distance_km(stops: tuple[FlowStop, ...]) -> float` — sum of haversine over
  consecutive stops. Zero or one stop → `0.0`.
- `format_distance(km: float) -> str` — `"1,840 km / 1,143 mi"`. Shared by legend and
  map so the two surfaces cannot drift apart.
- `rank_by_distance(team_flows, n=5) -> tuple[list[TeamFlow], list[TeamFlow]]` —
  returns the `n` longest (descending) and `n` shortest (ascending) by `distance_km`.
  Pure, deterministic.

Add a `distance_km: float` field to the frozen `TeamFlow` dataclass (default `0.0`).
`build_team_flows` gains a `distances: dict[str, float] | None = None` parameter and
populates each flow's `distance_km` from that dict — exactly how `build_venues`
takes `altitudes`. When `distances` is `None`, `distance_km` stays `0.0`.

**`scripts/compute_team_distances.py`** — generator. Loads matches + venues via the
existing repositories, builds flows, computes `path_distance_km` per team, and writes
`assets/data/team_distances.csv` with columns `team,distance_km` (full precision,
e.g. `1839.7`). Re-runnable; this is how the file is regenerated if the schedule
changes.

**`assets/data/team_distances.csv`** — the precomputed artifact (48 rows + header).

**`src/data/distances.py`** — `DistanceRepository.load(csv_path) -> dict[str, float]`,
mapping team → km. Mirrors `src/data/altitudes.py`.

### App wiring

`app.py` loads `DISTANCES = DistanceRepository.load(...)`, passes it to
`build_team_flows(MATCHES, VENUES, distances=DISTANCES)`, and passes `TEAM_FLOWS` to
the filter drawer so it can render the static leaderboard.

### Display

**Legend** (`src/components/filter_panel.py`, `legend()`): each selected-team row gains
a dimmed distance via `format_distance(flow.distance_km)` —
`● Brazil — 1,840 km / 1,143 mi`. Reacts to selection (unchanged behavior otherwise).

**Map** (`src/components/flow_layer.py`, `render_flow()`): attach a `dl.Tooltip` child
to the existing `Polyline` showing `"{team}: {format_distance(distance)}"` (visible on
hover). Verified API: `dl.Polyline(..., children=[dl.Tooltip(...)])`.

**Leaderboard** (`src/components/filter_panel.py`, `build_filter_drawer`): a static
block below the selector and legend, computed once at layout build, **independent of
selection**:

- **Longest journeys** — 5 rows: color dot · team · formatted distance.
- **Shortest journeys** — 5 rows, same format.

Drawer reads top to bottom: team selector → selected-team legend → leaderboard
(longest / shortest).

## Testing (TDD)

- `haversine_km` against a known city pair (within tolerance).
- `path_distance_km`: multi-leg sum; zero/one stop → `0.0`.
- `format_distance`: exact string for a known value.
- `rank_by_distance`: correct 5 longest / 5 shortest, correct order.
- `DistanceRepository.load`: parses CSV → dict.
- `build_team_flows`: populates `distance_km` from the `distances` dict; `0.0` when omitted.
- **CSV consistency**: recomputing from matches + venues equals the CSV values (within
  tolerance) and covers all 48 group-stage teams — keeps the file correct and the
  single source of truth (same idea as the `team_continents` CSV test).
- `legend`: selected row contains the formatted distance text.
- `build_filter_drawer`: drawer contains both leaderboard sections with team names and
  formatted distances.
- `render_flow`: the `Polyline` carries a `Tooltip` whose text includes the distance.

## Out of scope

- Home-country travel legs (no per-team home coordinates exist).
- Knockout-stage path (venues/opponents are placeholders).
- Per-leg breakdowns (only the total is shown).
