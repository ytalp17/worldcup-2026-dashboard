# WC2026 — Minimal Map Dashboard (v1) — Design

**Date:** 2026-05-30
**Status:** Approved for planning

## Goal

A minimal but clean Plotly Dash app whose centerpiece is an interactive map of
the three 2026 FIFA World Cup host countries (USA, Mexico, Canada). The map
displays the 16 host-city markers. Nothing else in v1.

Constraints come from `CLAUDE.md` and are non-negotiable: `dash-leaflet` map
with OpenStreetMap tiles, `dash-mantine-components` for all UI, `pandas` for
data, OOP for data entities/services, TDD, dark/light toggle always present,
full-screen layout with no scrollbars, responsive / no horizontal overflow.

## Scope (v1)

In scope:
- Load and validate the 16 host cities from CSV.
- Full-screen shell: header (title + theme toggle) and a map filling the rest.
- Map locked to a North-America bounding box; one marker per host city with a
  tooltip showing city, stadium, capacity.
- Light/dark theme toggle.

Explicitly out of scope (later versions): side panels, city list, match data,
filtering, search, fly-to interactions, any data-driven callbacks beyond theme.

## Architecture

Layered package (approach A):

```
app.py                    # entry: load cities, build layout, register theme callback
src/
  data/
    host_cities.py        # HostCity dataclass + HostCityRepository
  components/
    map_view.py           # build_map(cities) -> dl.Map
    layout.py             # build_layout(cities) -> MantineProvider shell
tests/
  test_host_cities.py
  test_map_view.py
assets/
  styles.css              # full-screen, no-scroll rules
  data/                   # provided CSVs (already present)
```

Data flows one direction at startup: `app.py` → `HostCityRepository` loads
cities once → passed into `build_layout` → into `build_map`. v1 has no
data-driven callbacks; the only callback is the theme toggle.

## Data layer — `src/data/host_cities.py`

Source: `assets/data/fifa_2026_host_cities.csv`
Columns: `City, Country, Stadium, Capacity, Latitude, Longitude` (16 rows).

- `HostCity` — frozen dataclass with fields: `city: str`, `country: str`,
  `stadium: str`, `capacity: int`, `lat: float`, `lon: float`.
- `HostCityRepository`:
  - `__init__(self, csv_path: str | Path)`.
  - `load(self) -> list[HostCity]`: reads via pandas, validates the schema
    (all 6 expected columns present), coerces `Capacity`→int and
    `Latitude/Longitude`→float, builds `HostCity` objects.
  - Validation raises `ValueError` on: missing columns, non-coercible types,
    latitude outside [-90, 90], longitude outside [-180, 180].

## Component layer

### `src/components/map_view.py` — `build_map(cities) -> dl.Map`
- `dl.TileLayer` with the OpenStreetMap URL template (no API key).
- One `dl.Marker` per city at `[lat, lon]` with a `dl.Tooltip` showing
  `city`, `stadium`, and `capacity`.
- `maxBounds` set to a North-America box covering USA/MX/CA (approx
  SW `[14, -168]`, NE `[72, -52]`) so the view cannot pan away from the
  host region.
- `center` ~`[40, -100]`, `zoom` ~3, `minZoom` ~3 so the continent stays
  framed and the user can't zoom out past it.
- Map fills its container (`style` height/width 100%).

### `src/components/layout.py` — `build_layout(cities) -> MantineProvider`
- `MantineProvider` at the root; `forceColorScheme` driven by a `dcc.Store`
  (default `"dark"`).
- Header: title "FIFA World Cup 2026" and a light/dark `ActionIcon` toggle.
- Body: the map from `build_map(cities)` filling remaining viewport height.
- Exact DMC components (e.g. `AppShell` vs `Group`/`Stack`, `ActionIcon`)
  confirmed against current `dash-mantine-components` API via context7 MCP
  before implementation.

## Theme toggle

A `dcc.Store` holds the current scheme. The `ActionIcon` click callback in
`app.py` flips it between `"light"` and `"dark"`; a callback feeds that value
into `MantineProvider`'s `forceColorScheme`. The toggle is always visible.

## Full-screen / responsive

`assets/styles.css`: set `html, body, #react-entry-point` to `height: 100vh`,
`width: 100vw`, `margin: 0`, `overflow: hidden`. The shell uses a column flex
layout so the header takes its natural height and the map flexes to fill the
rest. No horizontal overflow on mobile widths.

## Testing (TDD — tests written first)

`tests/test_host_cities.py`:
- Loads exactly 16 cities from the real CSV.
- Each `HostCity` has correct types; `capacity` is int.
- Coordinates fall within valid ranges.
- Missing-column CSV raises `ValueError`.
- Out-of-range coordinate raises `ValueError`.

`tests/test_map_view.py`:
- `build_map` returns a `dl.Map`.
- Contains exactly 16 markers.
- Contains an OSM `TileLayer`.
- `maxBounds` equals the North-America box.

Run: `pytest tests/ -v`.

## Dependencies

`dash`, `dash-leaflet`, `dash-mantine-components`, `pandas`, `pytest`.
Captured in `requirements.txt`.
