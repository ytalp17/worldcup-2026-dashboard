# Tournament Stats Drawer — Design

**Date:** 2026-06-14
**Status:** Approved, ready for implementation plan
**Branch:** new feature branch off `main` (do NOT merge to main without user validation)

## Goal

A tournament-wide stats drawer, opened from a new map pin (a "Tournament Stats" trophy
pin placed just above the ✈ Team Travel Map pin, shown only in the calendar / Time view).
The drawer has a **Team / Players** switch at the top that flips the whole drawer between
two tab sets; each tab renders one `dash-ag-grid`:

- **Team** (tournament-wide, all teams): **Standings · Attack & xG · Possession & Passing · Defense · Discipline**.
- **Players** (tournament-wide, every player with data): **Goals · Assists · Cards**.

## Scope & decisions

| Topic | Decision |
|---|---|
| Launcher | A new map `DivMarker` pin ("Tournament Stats", trophy icon), just above `filter-pin`; visible only in Time/calendar mode (same toggle pattern as `filter-pin`). |
| Container | A right-side `dmc.Drawer` (mirrors `filter-drawer`: frosted, `withOverlay=False`), title "Tournament Stats". |
| Switch | A `dmc.SegmentedControl` (`Team` / `Players`) at the top. Changing it swaps the tab set below and resets to the first tab. |
| Tabs | A second `dmc.SegmentedControl` whose `data` is set by the switch. Team → 5 tabs; Players → 3 tabs. |
| Grid | One `dash_ag_grid.AgGrid`; a callback swaps its `columnDefs` + `rowData` on (scope, tab, live-store) change. Grids scroll horizontally for wide team tabs (like the squad grid). |
| Player data | Goals / Assists / Cards only (the API exposes no per-player xG/rating). Tournament-wide = the existing `live_player_stats.csv` aggregated across **all** teams. |
| Team data | A new per-match team-statistics cache (`live_team_stats.csv`), aggregated tournament-wide. Standings tab uses `live-store` standings directly. |
| Aggregation | Counting stats summed; xG/xA summed; `Possession` averaged; accuracy columns recomputed from aggregated components (e.g. Pass Acc% = Σsuccessful / Σtotal). `apps` = matches with a row. |
| Persistence | Switch/tab state resets each open (no persistence). |

## Data availability (verified against the live API, PRO tier, 2026-06-14)

- **`/statistics/{id}`** returns 40 team-level `displayName`/`value` pairs per team, including
  **Expected Goals**, **Expected Assists**, Big Chances Created, Possession (0–1), Shots on/off
  target, Shots accuracy (0–1), Blocked shots, Shots within penalty area, Corners, Total/Successful
  passes, Key Passes, Passes Into Final Third, Long Passes, Crosses / Successful Crosses, Dribbles /
  Successful Dribbles, Tackles / Successful Tackles, Interceptions, Clearances, Aerial Duels /
  Successful Aerial Duels, Goalkeeper saves, Fouls, Offsides, Yellow cards, Red cards.
  `models.parse_statistics(raw)` already shapes this into `{team_name: {displayName: value}}`.
- **`/standings`** (already fetched in `snapshot`) gives per-group rows: P/W/D/L, scoredGoals (GF),
  receivedGoals (GA), points, position. `models.parse_standings` parses it.
- **Per-player:** only Goals/Assists/Cards from `/events` (no xG/rating). The `live_player_stats.csv`
  store already holds rows for every team's matches.
- Low-value team fields (Attacks, Free Kicks, Throw-Ins, Goal Kicks, Backward Passes, Passes Own/Opp
  Half) are **out of scope** — not persisted, not shown.

### Persisted team-stat fields (key → API displayName)

`xg`→"Expected Goals", `xa`→"Expected Assists", `big_chances`→"Big Chances Created",
`possession`→"Possession", `shots_on`→"Shots on target", `shots_off`→"Shots off target",
`shots_blocked`→"Blocked shots", `shots_in_box`→"Shots within penalty area",
`corners`→"Corners", `passes_total`→"Total passes", `passes_succ`→"Successful passes",
`key_passes`→"Key Passes", `passes_final_third`→"Passes Into Final Third",
`long_passes`→"Long Passes", `crosses`→"Crosses", `crosses_succ`→"Successful Crosses",
`dribbles`→"Dribbles", `dribbles_succ`→"Successful Dribbles", `tackles`→"Tackles",
`tackles_succ`→"Successful Tackles", `interceptions`→"Interceptions", `clearances`→"Clearances",
`aerials`→"Aerial Duels", `aerials_won`→"Successful Aerial Duels", `gk_saves`→"Goalkeeper saves",
`fouls`→"Fouls", `offsides`→"Offsides", `yellow`→"Yellow cards", `red`→"Red cards".

All numeric; missing fields default to 0. `possession` is a 0–1 float; all others are counts.

## Architecture

### 1. Team-stat parsing — `src/data/live/team_match_stats.py` (pure)
- `STAT_KEYS`: the ordered list of persisted keys above; `_DISPLAY_TO_KEY`: displayName→key map.
- `@dataclass(frozen=True) TeamMatchStat(match_id: int, team: str, stats: dict[str, float])`
  where `stats` holds every key in `STAT_KEYS` (missing → 0).
- `parse_team_match_stats(match_id, statistics) -> list[TeamMatchStat]`: takes the
  `{team: {displayName: value}}` dict from `models.parse_statistics`, returns one
  `TeamMatchStat` per team, mapping known displayNames to keys (unknown displayNames ignored;
  absent keys → 0.0).

### 2. Team-stats store — `src/data/live/team_stats_store.py`
- CSV `assets/data/live_team_stats.csv` (gitignored cache). Columns: `match_id, team, state` + one
  column per `STAT_KEYS` entry.
- `load(path) -> dict[int, list[TeamMatchStat]]` (missing file → `{}`).
- `stored_match_states(path) -> dict[int, str]`.
- `upsert(path, match_id, state, rows)` — atomic temp-file + `os.replace`, replacing all rows for
  `match_id`. (Same shape/contract as `player_store`.)

### 3. Service — `src/data/live/service.py`
- `__init__` gains `team_store=None` (a path), stored as `self._team_store`.
- `update_team_stats(self, matches, now) -> None`: mirror `update_player_stats` — for each match,
  finished-and-stored → skip; finished-new or live → fetch `/statistics` (via the existing cached
  `match_statistics`? No — fetch raw `self._client.statistics(mid)` so live overwrites aren't TTL-
  cached, matching `update_player_stats`'s direct fetch), parse via `models.parse_statistics` +
  `parse_team_match_stats`, `upsert`. Broad try/except per match.
- `tournament_player_leaders(self) -> dict`: aggregate the **whole** player store (no team filter),
  grouped by `player_id` when present else `(team, normalized name)`. Returns
  `{"goals"|"assists"|"cards": [{player, team, value, apps, (yellow,red for cards)}, ...]}`, each
  sorted desc (tie-break by player). `{}` when no player store.
- `tournament_team_leaders(self, standings=None) -> dict`: aggregate the team store per team across
  matches (sum counts, mean `possession`, `apps`=match count). Returns
  `{"attack"|"possession"|"defense"|"discipline": [row, ...]}` where each row carries the aggregated
  raw keys plus computed display fields: `shots` (=on+off+blocked), `shot_acc` (on/shots),
  `pass_acc` (succ/total). When `standings` (a `{group: [Standing]}` dict) is given, join each
  team's `gf`/`ga`/`gd` so the Attack tab can show **Goals**. Sorted per the tab's headline stat.
  `{}` when no team store.

### 4. Component — `src/components/tournament_stats.py`
- `build_tournament_drawer() -> dmc.Drawer`: header `SegmentedControl` `id="tourn-scope"`
  (`["Team","Players"]`, value "Team") + tab `SegmentedControl` `id="tourn-tabs"` (initial Team
  tabs) + `AgGrid` `id="tourn-grid"` (frosted theme, horizontal scroll), in a right `dmc.Drawer`
  `id="tournament-drawer"`.
- Tab definitions as data: `TEAM_TABS` and `PLAYER_TABS` (each: label, key, colDefs builder).
- Pure helpers:
  - `tab_options(scope) -> list[str]` (the SegmentedControl `data` for that scope).
  - `tourn_columns(scope, tab) -> list[dict]` — colDefs for the active (scope, tab). If `tab`
    is not valid for `scope` (a transient state right after the switch flips, before
    `set_tournament_tabs` resets the value), fall back to the scope's first tab. Same fallback in
    `tourn_row_data`. This keeps the grid coherent during the switch.
  - `tourn_row_data(scope, tab, team_leaders, player_leaders, standings) -> list[dict]` — rows for
    the active grid, adding 1-based `rank`. Standings tab flattens `standings` groups (all teams),
    adds a Group column, sorts by Pts then GD. Empty inputs → `[]`.
- `standings_table_rows(standings) -> list[dict]` helper for the Standings tab.

### 5. Map pin — `src/components/map_view.py`
- `tournament_pin() -> dl.DivMarker` (`id="tournament-pin"`, trophy SVG, tooltip "Tournament
  Stats"), positioned just above `FILTER_PIN` (e.g. `[21.3, -134.5]`).
- Add a `tournament-pin-layer` `LayerGroup` next to `filter-pin-layer`.

### 6. Wiring — `app.py`
- `TEAM_STATS_PATH = DATA_DIR / "live_team_stats.csv"`; pass `team_store=TEAM_STATS_PATH` to `LIVE`.
- Add `build_tournament_drawer()` to the layout; add `tournament-pin-layer` to the map.
- `toggle_tournament_pin(team_mode)` → `[]` in Team mode else `[tournament_pin()]` (mirrors
  `toggle_filter_pin`).
- `open_tournament_drawer(n_clicks)` → opens `tournament-drawer` (and closes the other left/right
  drawers as appropriate, matching existing drawer-coordination).
- `set_tournament_tabs(scope)` → `tourn-tabs.data` + `tourn-tabs.value` (first tab for the scope).
- `update_tournament_grid(scope, tab, live)` → `tourn-grid.columnDefs` + `rowData`:
  `tl = LIVE.tournament_team_leaders((live or {}).get("standings")) if LIVE else {}`,
  `pl = LIVE.tournament_player_leaders() if LIVE else {}`, then `tourn_columns` / `tourn_row_data`.
- `live_feed`: also `update_team_stats` per poll and in `_backfill_player_stats` (rename to
  `_backfill_live_stats`, calling both `update_player_stats` and `update_team_stats`).

## Data flow
```
live_feed poll ─► update_player_stats + update_team_stats ─► live_player_stats.csv + live_team_stats.csv
tournament-pin click ─► open tournament-drawer
tourn-scope change ─► set_tournament_tabs (swap tab set, reset to first)
(scope, tab, live-store) change ─► tournament_team_leaders(standings) / tournament_player_leaders()
                                 ─► tourn_columns + tourn_row_data ─► tourn-grid
```

## Tab columns (display)

- **Standings:** Pos · Team · Group · P · W · D · L · GF · GA · GD · **Pts** (sort Pts↓, then GD↓).
- **Attack & xG:** Team · Goals · **xG** · **xA** · Big Chances · Shots · On Target · Off Target ·
  Shot Acc% · In Box · Blocked · Corners · Apps (sort Goals↓).
- **Possession & Passing:** Team · **Poss%** · Passes · Pass Acc% · Key Passes · Final Third ·
  Long Passes · Crosses · Succ Crosses · Dribbles · Succ Dribbles · Apps (sort Poss%↓).
- **Defense:** Team · Tackles · Succ Tackles · Interceptions · Clearances · Aerial Duels ·
  Aerials Won · GK Saves · Apps (sort Succ Tackles↓).
- **Discipline:** Team · 🟨 Yellow · 🟥 Red · Fouls · Offsides · Apps (sort Yellow↓).
- **Goals (players):** # · Player · Team · Goals · Apps (sort Goals↓).
- **Assists (players):** # · Player · Team · Assists · Apps.
- **Cards (players):** # · Player · Team · 🟨 · 🟥 · Apps (sort total↓).

## Testing (TDD, offline, fixtures)
- `parse_team_match_stats`: maps displayNames→keys, two teams, missing fields→0, ignores unknown.
- `team_stats_store`: upsert replaces a match's rows; load / stored_match_states round-trip;
  missing file → empty.
- `service.update_team_stats`: fake client + fixtures — finished-stored skipped, finished-new
  fetched once, live overwritten. `tournament_team_leaders`: sum/mean/ratio/apps + standings join.
  `tournament_player_leaders`: cross-team aggregation, Team column, cards yellow/red.
- Component: `tab_options`, `tourn_columns`, `tourn_row_data` (incl. standings flatten + sort),
  empty inputs → empty rows.
- `app.leaders`-style payload/callback smoke tests run with `LIVE=None` (offline) → empty grids.
- Full suite stays green and offline.

## Error handling / degradation
- API errors during an update → logged, skip that match, keep the CSV (per existing service style).
- No API key → no updates; grids render empty (built-in "no data" overlay), no crash.
- Caches are gitignored; deleting them triggers a fresh backfill on next run.

## Out of scope (YAGNI)
- Per-player xG/rating/shots (no reliable API data).
- Low-value team fields listed above.
- Persisting switch/tab state; CSV commit; per-90 or per-match normalization (raw sums + averages
  only); clean sheets (needs per-match goals-conceded join — defer).
