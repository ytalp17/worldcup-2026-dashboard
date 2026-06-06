# Team-Mode Squad Table — Design

**Date:** 2026-06-06
**Status:** Approved

## Goal

Add a per-team **squad table** to the Team-mode bento dashboard. When a team is
centered in the carousel, a card shows that team's full World Cup 2026 squad
(every player + their attributes) in a dash-ag-grid styled like the existing
group-standings grid. The squad updates as the carousel changes, mirroring the
group panel.

## Data source

`assets/data/world_cup_2026_squads.csv` — 1,247 rows, 48 teams, ~25–27 players
each. Columns:

`country, team_id, shirt_number, name, position, date_of_birth, age, club,
height_m, foot, international_caps, international_goals, debut, market_value`

- **Dropped from display:** `country`, `team_id` (per user).
- **Blanks exist** in `international_caps`, `foot` (and possibly others) — render
  gracefully (empty string), never crash.
- `market_value` is a pre-formatted string (`€40.00m`, `€550k`) — display as-is.
- `height_m` is a bare number (`1.91`) — display as `1.91 m`.
- `date_of_birth` / `debut` are `dd/mm/yyyy` strings — display as-is.

### Name mapping (CSV → canonical)

The squad CSV spells 10 teams differently from the app's canonical team names
(which match the carousel, the matches data, and the `country_logos/*.svg`
filenames). The repository maps CSV `country` → canonical name at load time so
the squad keys off the same team the carousel centers on:

```
Bosnia-Herzegovina  -> Bosnia and Herzegovina
Cape Verde          -> Cabo Verde
Curacao             -> Curaçao
Czech Republic      -> Czechia
DR Congo            -> Congo DR
Iran                -> IR Iran
Ivory Coast         -> Côte d'Ivoire
South Korea         -> Korea Republic
Turkey              -> Türkiye
United States       -> USA
```

All other 38 names are identical. Verified: all 48 squad teams resolve to an
existing canonical team / logo.

## Layout — bento rearrangement

The user granted freedom to re-arrange the bento for the squad. The squad table
(26 rows × 12 columns) gets a **full-height right strip** — maximum vertical room
for players, with horizontal scroll for the wide column set. The map stays the
largest tile; the group standings stay; 4 empty placeholder cards remain.

```
grid-template-columns: 1.3fr 1.3fr 1fr 1.4fr
grid-template-rows:    1.4fr 1fr 1fr
grid-template-areas:
    "map  map  table squad"
    "map  map  e1    squad"
    "e2   e3   e4    squad"
```

- `map`   — cols 1–2 × rows 1–2 (largest tile, unchanged role).
- `table` — group standings (unchanged component), row 1 col 3.
- `squad` — col 4 × all 3 rows (full-height strip).
- `e1`–`e4` — empty placeholder cards (down from e1–e7).

**Mobile (`max-width: 768px`):** single column, order map → table → squad →
e1–e4. Squad card gets a fixed height (≈ 60vh) with internal scroll.

## Squad table (dash-ag-grid)

Columns, in CSV order (all except `country`/`team_id`). `#` and `Player` are
**pinned left** so identity stays visible while scrolling stats horizontally.

| Header | field      | source             | width | notes                       |
|--------|------------|--------------------|-------|-----------------------------|
| #      | number     | shirt_number       | 48    | pinned left, dimmed         |
| Player | name       | name               | 150   | pinned left                 |
| Pos    | pos        | position → code    | 56    | short code (GK, CB, DM…)    |
| DOB    | dob        | date_of_birth      | 96    |                             |
| Age    | age        | age                | 56    |                             |
| Club   | club       | club               | 150   |                             |
| Ht     | height     | height_m → `x.xx m`| 70    |                             |
| Foot   | foot       | foot (Title-case)  | 64    |                             |
| Caps   | caps       | international_caps  | 56    | blank when missing          |
| Gls    | goals      | international_goals | 56    |                             |
| Debut  | debut      | debut              | 96    |                             |
| Value  | value      | market_value       | 84    | raw string (`€40.00m`)      |

- **No `columnSize`** (same lesson as the group grid: `sizeToFit` treats width as
  a ratio). Fixed widths + grid narrower than their sum ⇒ native horizontal
  scroll. `domLayout: "normal"` + a 100%-height card ⇒ native vertical scroll for
  the ~26 rows.
- Same compact, transparent quartz styling; theme follows the light/dark toggle
  via a clientside callback (mirrors `group-grid`).
- Cell padding overridden to 6px (same quartz-padding clipping fix as group grid).

### Position short codes

```
Goalkeeper -> GK            Defensive Midfield -> DM    Left Winger   -> LW
Centre-Back -> CB           Central Midfield   -> CM    Right Winger  -> RW
Left-Back -> LB             Attacking Midfield -> AM    Centre-Forward-> CF
Right-Back -> RB            Left Midfield      -> LM    Second Striker-> SS
                            Right Midfield     -> RM
```
Unknown position → first letters fallback (defensive; shouldn't occur).

## Components / data flow

- **`src/data/squads.py`** (new): `Player` (frozen dataclass: number, name, pos,
  dob, age, club, height_m, foot, caps, goals, debut, market_value), `Squad`
  (name + players tuple), `SquadRepository(path).load() -> dict[str, Squad]`
  keyed by canonical name (pandas read + CSV→canonical map), `squad_for_team(squads, team) -> Squad | None`.
- **`src/components/squad_table.py`** (new): `POSITION_CODES` map +
  `position_code()`, `COL_DEFS`, `_GRID_OPTIONS`, `squad_rows(squad) -> list[dict]`,
  `build_squad_panel(squad | None) -> dmc.Box` (header "Squad" / "World Cup" /
  team name id `squad-table-title`, then `dag.AgGrid` id `squad-grid`).
- **`src/components/layout.py`**: `build_layout(..., squad_panel=None)`; add
  `squad_card`; rearrange bento cards to map/table/squad + e1–e4.
- **`app.py`**: load `SQUADS`; `squad_panel_payload(index)`; pass `squad_panel`;
  `update_squad_panel` callback (Input `carousel-index.data` → Output
  `squad-grid.rowData`, `squad-table-title.children`); `squad-grid` theme-sync
  clientside callback.
- **`assets/styles.css`**: new bento template-areas (map/table/squad/e1–e4),
  `.bento-card--squad`, `.squad-panel__*`, `.squad-grid` (scrollable both axes),
  mobile stacking.

## Testing

- `tests/test_squads.py`: repository loads, canonical name mapping (all 10
  overrides + an identity case), blanks tolerated, `squad_for_team`.
- `tests/test_squad_table.py`: `position_code` map, `squad_rows` shape +
  formatting (`height` → `x.xx m`, blank caps), `build_squad_panel` (grid id,
  pinned columns, None → empty), COL_DEFS excludes country/team_id.
- `tests/test_layout.py`: bento has `bento-card--squad` + `squad-grid`; empty
  cards now e1–e4 (update the e1–e7 assertion).
- `tests/test_app.py`: `squad_panel_payload` returns name + rows for centered
  team; None-safe.
- Playwright e2e (`scripts/e2e_squad_panel.py`, Framework 3.11 python): Team mode
  shows the squad card with rows; carousel change updates it; horizontal scroll
  present; theme flips; mobile stacks. (See [[e2e-playwright-setup]].)

## Out of scope

Sorting/filtering controls, player photos, click-through detail, API wiring
(stats are static from the CSV).
