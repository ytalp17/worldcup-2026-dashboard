# Leaflet Theming, Tighter Bounds & Timezone-in-Drawer — Design

**Date:** 2026-05-30
**Status:** Approved for planning

## Goal

Three improvements to the map, from `ideas.txt`:
1. The base map tiles follow the dark/light theme toggle (dark tiles in dark
   mode, light tiles in light mode).
2. Tighten the map so the user effectively stays over USA/Mexico/Canada.
3. Show each stadium's timezone in the detail drawer.

Constraints from `CLAUDE.md` still apply: dash-leaflet map, DMC for UI, pandas,
OOP, TDD, dark/light toggle always present, full-screen no-scroll.

## Scope

In scope: themed tiles, tighter bounds, timezone in the drawer.
Out of scope (explicitly declined): country-shape masking overlay, timezone
boundary overlay on the map, timezone labels on markers/tooltips.

## 1. Themed tiles

`src/components/map_view.py`:
- `LIGHT_TILE = "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"`
  (CartoDB Positron).
- `DARK_TILE  = "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"`
  (CartoDB Dark Matter).
- `TILE_ATTRIBUTION = "© OpenStreetMap contributors © CARTO"`.
- The base `TileLayer` gets `id="base-tiles"` and an initial `url=DARK_TILE`
  (the app defaults to dark, so this avoids a flash).

The tile swap is folded into the **existing** theme clientside callback in
`app.py`: input is the switch `checked` value; the callback sets
`document.documentElement`'s `data-mantine-color-scheme` AND returns the
matching tile URL. Output changes from the previous no-op
(`color-scheme-toggle.id`) to `base-tiles.url`. `prevent_initial_call` stays
false so tiles sync to the persisted switch state on load.

```js
(checked) => {
    document.documentElement.setAttribute(
        'data-mantine-color-scheme', checked ? 'dark' : 'light');
    return checked ? "<DARK_TILE>" : "<LIGHT_TILE>";
}
```

## 2. Tighter bounds

`src/components/map_view.py`:
- Keep rectangular `maxBounds` but snug it to the three countries:
  `NA_BOUNDS = [[12.0, -172.0], [74.0, -50.0]]` (covers southern Mexico through
  northern Canada and the Aleutians without excess open ocean).
- Add `maxBoundsViscosity=1.0` so the bounds are a hard wall (can't drag past).
- Keep `minZoom=3` so the user cannot zoom out past the continent.

## 3. Timezone in the drawer

New `src/data/timezones.py`:
- `CITY_TIMEZONES: dict[str, tuple[str, str]]` mapping each of the 16 host
  cities to `(iana_name, friendly_label)`, e.g.
  `"Dallas": ("America/Chicago", "Central Time")`.
- `timezone_for(city: str) -> tuple[str, str]`; raises `ValueError` for an
  unknown city.

`src/data/venues.py` — `Venue` gains:
- `timezone: str` (IANA name) and `tz_label: str` (friendly label).
- `build_venues` populates them via `timezone_for(city.city)`. Because every
  host city must be mapped, an unmapped city raises (caught by a test that all
  16 join and carry a timezone).

`src/components/detail_panel.py`:
- Add a timezone row to `stadium_detail`: a clock icon plus text
  `"<friendly> · UTC<offset> · <iana>"`, where `<offset>` is computed at render
  from `zoneinfo.ZoneInfo(iana)` (stdlib, no new dependency). Example:
  `"Central Time · UTC-05:00 · America/Chicago"`.

## City → timezone map (all 16)

| City | IANA | Label |
|------|------|-------|
| New York/New Jersey | America/New_York | Eastern Time |
| Boston | America/New_York | Eastern Time |
| Philadelphia | America/New_York | Eastern Time |
| Atlanta | America/New_York | Eastern Time |
| Miami | America/New_York | Eastern Time |
| Toronto | America/Toronto | Eastern Time |
| Dallas | America/Chicago | Central Time |
| Houston | America/Chicago | Central Time |
| Kansas City | America/Chicago | Central Time |
| Mexico City | America/Mexico_City | Central Time |
| Monterrey | America/Monterrey | Central Time |
| Guadalajara | America/Mexico_City | Central Time |
| Seattle | America/Los_Angeles | Pacific Time |
| San Francisco | America/Los_Angeles | Pacific Time |
| Los Angeles | America/Los_Angeles | Pacific Time |
| Vancouver | America/Vancouver | Pacific Time |

## Testing (TDD)

- `tests/test_timezones.py`: `timezone_for` returns expected tuples for sample
  cities; unknown city raises `ValueError`.
- `tests/test_venues.py`: every venue carries a non-empty `timezone`/`tz_label`;
  Dallas → `America/Chicago` / "Central Time".
- `tests/test_detail_panel.py`: drawer content includes the friendly label and
  the IANA name.
- `tests/test_map_view.py`: base `TileLayer` has `id="base-tiles"` and initial
  `url == DARK_TILE`; map sets `maxBoundsViscosity == 1.0` and the tightened
  `NA_BOUNDS`.
- `scripts/e2e_check.py` (manual): after toggling the theme, the `base-tiles`
  `src` switches between the light and dark CartoDB hosts.

## Risks / notes

- CartoDB public tiles are keyless but rate-limited; fine for a demo dashboard.
- Marker tooltips and the existing 16-city join are unchanged.
- `{r}` retina + `{s}` subdomain placeholders are standard Leaflet and pass
  through dash-leaflet's `TileLayer.url` unchanged.
