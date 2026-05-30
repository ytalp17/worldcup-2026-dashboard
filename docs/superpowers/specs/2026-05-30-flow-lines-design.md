# Flow Lines — Design

**Date:** 2026-05-30
**Status:** Approved for planning

## Goal

A yellow funnel "filter" pin on the (otherwise static) map opens a left,
non-blocking drawer with a continent-grouped multi-select of all 48 group-stage
teams. Selecting teams draws, for each, a colored line through the three
stadiums of that team's group-stage matches in chronological order, with
arrowheads indicating order. Each team has a fixed color. Deselecting removes
its line. Lines update live while the drawer is open.

Constraints (CLAUDE.md): dash-leaflet map, DMC UI, pandas, OOP, TDD, dark/light
toggle, full-screen no-scroll. The map stays static (no pan, zoom-in only).

## Decisions (from brainstorming)

- Multi-select; each selected team draws its own line simultaneously.
- Dropdown grouped by **geographic continent**.
- Direction shown with **arrowheads** (PolylineDecorator).
- **Fixed per-team** color (stable identity).
- Filter drawer: **left, non-blocking** (no overlay, no scroll-lock).
- Filter pin: **yellow funnel/filter icon**, fixed at a visible right-middle
  Atlantic point (≈ `[37.5, -71.0]`, tunable).
- The two left drawers (stadium, filter) are **mutually exclusive**: opening one
  closes the other. Toggling teams inside the filter drawer keeps it open.

## Data layer

### `src/data/team_continents.py`
- `TEAM_CONTINENT: dict[str, str]` covering all 48 group-stage teams. Continents:
  Europe, South America, North America, Africa, Asia, Oceania.
- `continent_for(team) -> str` (raises `ValueError` if unmapped).
- `grouped_team_options(teams) -> list[dict]` → DMC MultiSelect grouped data:
  `[{"group": "<continent>", "items": [{"value": t, "label": t}, ...]}, ...]`,
  continents in a fixed display order, teams sorted within each.

Mapping (exact CSV strings):
- **Europe (16):** Austria, Belgium, Bosnia and Herzegovina, Croatia, Czechia,
  England, France, Germany, Netherlands, Norway, Portugal, Scotland, Spain,
  Sweden, Switzerland, Türkiye
- **South America (6):** Argentina, Brazil, Colombia, Ecuador, Paraguay, Uruguay
- **North America (6):** Canada, Curaçao, Haiti, Mexico, Panama, USA
- **Africa (10):** Algeria, Cabo Verde, Congo DR, Côte d'Ivoire, Egypt, Ghana,
  Morocco, Senegal, South Africa, Tunisia
- **Asia (8):** IR Iran, Iraq, Japan, Jordan, Korea Republic, Qatar,
  Saudi Arabia, Uzbekistan
- **Oceania (2):** Australia, New Zealand

(Türkiye → Europe per UEFA convention; tunable.)

### `src/data/flows.py`
- `team_color(team: str) -> str` — deterministic hex color, evenly spread over
  the 48 sorted teams (HSL hue spaced around the wheel with fixed S/L), so each
  team always renders the same color.
- `TeamFlow` (frozen dataclass): `team, continent, color, stops` where
  `stops: list[FlowStop]` and `FlowStop` is `(lat, lon, stadium_name, date,
  match_number)`, ordered by `(date, match_number)`.
- `build_team_flows(matches, venues) -> dict[str, TeamFlow]`: for each group-stage
  team, collect its matches (home or away), sort chronologically, map each
  match's `stadium` (generic name) to the venue's coordinates via a
  `{stadium_name: Venue}` index, and build the ordered stops. Knockout stages are
  ignored. Raises if a stadium name has no matching venue.

## Components

### Map — `src/components/map_view.py`
- Add an empty `dl.LayerGroup(id="flow-layer")` (filled by callback).
- Add the funnel filter pin: `dl.DivMarker(id="filter-pin", position=FILTER_PIN,
  iconOptions={html: funnel svg, className: "filter-pin-icon"})`. Styled yellow
  in `assets/styles.css` (`.filter-pin`). `FILTER_PIN = [37.5, -71.0]`.

### Flow rendering — `src/components/flow_layer.py`
- `render_flow(flow: TeamFlow) -> list`: returns
  - `dl.Polyline(positions=[[lat,lon],...], color=flow.color, weight=3)`,
  - `dl.PolylineDecorator(positions=..., patterns=[{offset, repeat, endOffset,
    arrowHead: {pixelSize, pathOptions: {color: flow.color, ...}}}])`,
  - small stop dots (`dl.CircleMarker` per stop, `flow.color`).
- `flows_for(selected: list[str], team_flows) -> list`: flat list of components
  for all selected teams (empty list when none selected). Exact `arrowHead`
  pattern keys confirmed against dash-leaflet before coding.

### Filter drawer — `src/components/filter_panel.py`
- `build_filter_drawer(options) -> dmc.Drawer`:
  `dmc.Drawer(id="filter-drawer", position="left", withOverlay=False,
  lockScroll=False, title="Flow lines by team", ...)` containing
  `dmc.MultiSelect(id="team-filter", data=options, searchable=True,
  clearable=True, placeholder="Select teams…")` and a legend container
  (`id="filter-legend"`) filled by callback with selected team → color dot.
- Grouped-data format for MultiSelect confirmed against DMC 0.15 before coding.

## Interaction — `app.py`

- Build `TEAM_FLOWS = build_team_flows(MATCHES, VENUES)` and
  `TEAM_OPTIONS = grouped_team_options(sorted(TEAM_FLOWS))` at startup.
- Layout includes the filter drawer (inside MantineProvider).
- Callback A (existing marker-click): also `Output("filter-drawer","opened")=False`
  so opening the stadium drawer closes the filter drawer.
- Callback B (filter pin): `Input filter-pin n_clicks` →
  `Output filter-drawer.opened=True`, `Output stadium-drawer.opened=False`.
- Callback C: `Input("team-filter","value")` →
  `Output("flow-layer","children") = flows_for(value, TEAM_FLOWS)` and
  `Output("filter-legend","children") = legend(value)`. Pure helpers
  `flows_for` and `legend` are unit-tested.

## Testing (TDD)

- `test_team_continents.py`: all 48 teams mapped; `continent_for` known + raises;
  `grouped_team_options` groups by continent, sorted, correct shape.
- `test_flows.py`: `team_color` deterministic and stable; `build_team_flows`
  yields 48 flows, Brazil stops = New York/Philadelphia/Miami coords in date
  order, Mexico doubles back (stop1 == stop3 coords); unmatched stadium raises.
- `test_flow_layer.py`: `render_flow` returns a Polyline (team color) + a
  PolylineDecorator + one CircleMarker per stop; `flows_for([])` is empty;
  `flows_for(["Brazil"])` contains a Polyline with Brazil's color.
- `test_filter_panel.py`: drawer is left + `withOverlay=False`; contains a
  MultiSelect `id="team-filter"` with grouped data.
- `test_layout.py`: layout contains the filter drawer and `flow-layer`;
  map contains the filter pin.
- `test_app.py`: `flows_for`/`legend` wired; selecting "Brazil" yields layer
  children; pin/stadium mutual-exclusion helper.
- e2e: click filter pin → filter drawer opens (stadium drawer closed); select a
  team in the MultiSelect → a colored polyline appears in `flow-layer`.

## Out of scope

- Knockout-stage flow lines (placeholder teams), animation along the line,
  per-team flags. Geographic continent assignment of transcontinental nations is
  a fixed editorial choice (Türkiye→Europe, Australia→Oceania, IR Iran→Asia).
