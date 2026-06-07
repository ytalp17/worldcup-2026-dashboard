# Team-Mode Dashboard Layout — Design

**Date:** 2026-06-07

## Goal

Rework the Team-mode bento grid into a team dashboard (per the user's mockup):
a full-width KPI strip on top, then Leaders + Table + Formation + a small
host-cities Map, with the Squad as the tall right column. The large travel map
is demoted — it stays full-screen only in Time mode.

## Layout

Team-mode grid (`main-split--team`), squad spans the two content rows on the
right:

```
grid-template-areas:
  "kpi        kpi    squad"
  "leaders    table  squad"
  "formation  map    squad";
grid-template-rows: auto 1fr 1fr;     /* kpi strip auto-height */
grid-template-columns: 1.15fr 1.1fr 1.25fr;
```

- **kpi** — a flex strip (`#kpi-strip`) of 7 individual stat cards, full width
  across the top two content columns.
- **leaders** — Leaders placeholder card (top-left).
- **table** — existing group-standings ag-grid (top-middle).
- **formation** — existing estimated-XI pitch card (bottom-left).
- **map** — the existing Leaflet map, resized to a small tile (bottom-middle).
- **squad** — existing squad ag-grid, tall right column (rows 2–3).

Time mode is unchanged: only the map card shows, full-screen. A robust hide rule
collapses the rest: `.main-split:not(.main-split--team) > *:not(.bento-card--map)
{ display: none; }`.

## KPI strip (7 cards)

Each is a small bordered card: icon + label (top), big value, small sub-label.
A clientside-independent server callback rebuilds the strip on carousel change.

| Card        | Source                                   | v1 value |
|-------------|------------------------------------------|----------|
| Avg age     | mean of squad ages                       | real     |
| Avg height  | mean of squad heights (m)                | real     |
| FIFA rank   | — (no data yet)                          | "—"      |
| Value       | sum of squad market values, formatted    | real     |
| Abroad      | — (no club-country data yet)             | "—"      |
| Foot        | right vs left/both %, `dmc.RingProgress` | real     |
| Manager     | — (lineups coach is mostly empty)        | "—"      |

`TeamStats` (placeholders are `None` → rendered as "—").

### Data layer — `src/data/team_stats.py`

- `TeamStats` frozen dataclass: `avg_age: float|None`, `avg_height: float|None`,
  `squad_value: float|None` (euros), `value_display: str`, `foot_right_pct:
  int|None`, `foot_left_pct: int|None`, `squad_size: int`, plus
  `fifa_rank: int|None`, `manager: str|None`, `abroad: int|None` (all `None`).
- `parse_market_value("€1.60m") -> 1_600_000.0` (`k`/`m` suffix; "" → 0).
- `format_value(euros) -> "€32M"` (≥1e9 → "€1.2B", ≥1e6 → "€32M", else "€700K").
- `compute_team_stats(squad) -> TeamStats` (ignores blank cells; division-safe).

## Components

- **`src/components/team_kpis.py`**
  - `stat_card(icon, label, value, sub=None, ring=None) -> dmc.Box`
    (`className="stat-card"`); `ring` (a `dmc.RingProgress`) replaces the value.
  - `kpi_cards(stats) -> list[dmc.Box]` — the 7 cards (foot card uses
    `RingProgress` with `sections=[{value: right%, color}]` + `label`).
  - `build_kpi_strip(stats) -> dmc.Box(id="kpi-strip", className="kpi-strip")`.
- **`src/components/leaders_card.py`**
  - `build_leaders_card() -> dmc.Box(className="leaders-panel")`: a
    `bento-card__header` ("Leaders" + "tournament"), a `dmc.SegmentedControl`
    (Goals/Assists/Cards, id `leaders-tabs`), and an empty-state Stack with a
    clock icon + "Fills in once matches start (Jun 11)". Static placeholder.

## Wiring — `layout.py` + `app.py`

- `layout.py`: `build_layout(..., kpi_strip=None, leaders_panel=None)`; main-split
  children become `[kpi_strip, leaders_panel(card), table_card, map_card,
  formation_card, squad_card]` (map keeps `bento-card--map`; no empty
  placeholders any more).
- `app.py`:
  - `team_stats_payload(index) -> TeamStats` for the centred team's squad.
  - Pass `kpi_strip=build_kpi_strip(stats0)` and
    `leaders_panel=build_leaders_card()` to `build_layout`.
  - New callback `update_kpi_strip(index)` → `Output("kpi-strip","children")`,
    `Input("carousel-index","data")` → `kpi_cards(team_stats_payload(index))`.
  - Map flow/pulse callbacks unchanged (already team-aware).

## Styling — `assets/styles.css`

- New `main-split--team` grid (areas above). `bento-card--map` mapped to area
  `map` and sized as a small tile (no longer the 2×2 hero).
- `.kpi-strip { display:flex; gap; }`, `.stat-card` (flex:1; bordered; padding;
  icon row, big value, sub). Foot ring sized small.
- `.leaders-panel` flex column (header + body), empty-state centred/dimmed.
- Replace the time-mode hide rule with the `> *:not(.bento-card--map)` form.
- Mobile: KPI strip wraps (`flex-wrap`); grid stacks
  (kpi → leaders → table → formation → map → squad) with sensible heights.

## DMC components to verify via context7

`RingProgress`, `SegmentedControl` (and `Tabs` as fallback), per CLAUDE.md.

## Testing

- `test_team_stats.py`: market-value parse + format; `compute_team_stats` on a
  small synthetic squad (avg age/height, value display, foot %, size);
  placeholders are `None`; division-safe on empty squad.
- `test_team_kpis.py`: `kpi_cards` returns 7 cards; foot card contains a
  `RingProgress`; placeholder fields render "—"; `build_kpi_strip` id.
- `test_leaders_card.py`: header text, segmented control with 3 options, empty
  state present.
- `test_layout.py`: kpi-strip + leaders + table + squad + formation + map
  present; no `bento-e*` ids remain; map keeps `bento-card--map`.
- `test_app.py`: `team_stats_payload(0)` returns a `TeamStats` with a real
  `value_display`; KPI strip children rebuild per index.
- Playwright `e2e_team_dashboard.py`: Team mode shows the KPI strip (7 cards),
  the map is small (≪ Time-mode full map), carousel updates KPI values, no
  mobile overflow.

Out of scope (v1): real FIFA rank / manager / abroad data, live Leaders content,
a dedicated host-cities-only map layer (the existing team travel layer stands in).
