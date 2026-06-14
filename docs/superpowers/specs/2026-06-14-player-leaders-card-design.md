# Player Leaders Card — Design

**Date:** 2026-06-14
**Status:** Approved, ready for implementation plan
**Branch:** feat/highlightly-live-data (do NOT merge to main without user validation)

## Goal

Replace the placeholder Leaders card (team / club view) with **player-level leader
grids for the selected team**: tabs for **Goals · Assists · Cards · Rating**, each a
`dash-ag-grid` listing every player we have data for, ranked descending. The data is
aggregated across the team's matches and persisted to a per-match player-stats CSV
that the existing `live_feed` WebSocket loop maintains.

## Scope & decisions

| Topic | Decision |
|---|---|
| Perspective | **Player level only**, for the selected (carousel-centred) team. Team perspective is deferred to the calendar view (separate, later). |
| Stats / tabs | **Goals, Assists, Cards, Rating**. xG dropped — see data availability. |
| Ranking | **All players with data, uncapped** (no top-N). Ranked desc by the active stat. |
| Render | `dash-ag-grid`, one grid driven by a tab/segmented control; columns **#, Player, ⟨stat⟩, Apps**. |
| Persistence | A per-match player-stats CSV cache, updated by `live_feed`. |
| Player names | From `/events` / `topPlayers` as-is (abbreviated, e.g. "M. Cunha"); reconcile within a match by `playerId` when present, else normalized name. No fuzzy match to `squads.csv`. |

## Data availability (verified against the live API, PRO tier, 2026-06-14)

Probed real finished matches (Mexico–South Africa, Brazil–Morocco, USA–Paraguay …):
- **`/events/{id}`** — per-player `Goal` / `Own Goal` / `Penalty`, `Yellow Card`,
  `Red Card`, with `player`, `playerId`, and `assist` / `assistingPlayerId`. Covers
  **every** player involved. → Goals, Assists, Cards.
- **`/matches/{id}` → `homeTeam/awayTeam.topPlayers`** — only the **top few** players
  per match, each with `Goals`, `Rating`, `Assists`, `Yellow:Red`. → **Rating** (partial).
- **`/statistics/{id}`** — **team-level only**; xG is a team total. **No per-player xG.**
- No per-player stats in `/lineups` for this purpose. Full-roster zero-fill is out of scope.

So the grids draw from **events (Goals/Assists/Cards) + topPlayers (Rating)**. A player
appears in the grids when they have ≥1 recorded stat or a topPlayers entry. "Apps" =
the number of the team's matches in which the player recorded data (not true minutes).

## Architecture

### 1. Per-match aggregation — `src/data/live/player_stats.py` (pure)
- `@dataclass PlayerMatchStat(match_id, team, player, player_id, goals, assists, yellow, red, rating)`.
- `parse_player_stats(match_id, events, detail) -> list[PlayerMatchStat]`:
  - Walk `/events`: tally `goals` (Goal/Penalty; **exclude Own Goal** from the scorer's
    goals), `assists` (from `assistingPlayerId`/`assist`), `yellow`, `red`, per
    `(team, playerId|player)`.
  - Merge `topPlayers` from match `detail` for `rating` (and as a fallback source of
    players), keyed by normalized name within the same team.
  - Returns one row per distinct player who appears in either source.

### 2. Store — `src/data/live/player_store.py`
- CSV at `assets/data/live_player_stats.csv` (a **gitignored cache**, not committed).
  Columns: `match_id, team, player, player_id, goals, assists, yellow, red, rating, state`.
- `load(path) -> dict[int, list[PlayerMatchStat]]` keyed by `match_id` (+ each match's
  stored `state`). Missing file → `{}`.
- `stored_match_states(path) -> dict[int, str]` — match_id → last stored state, so the
  updater can skip finished matches already on disk.
- `upsert(path, match_id, state, rows)` — atomically replace all rows for `match_id`.

### 3. Service — `src/data/live/service.py`
- `update_player_stats(self, matches, now) -> None`: for each match dict (id + state):
  - **finished & already stored** → skip (no fetch).
  - **finished & not stored** → fetch `events` + `match` detail once, `upsert`.
  - **live** → fetch + `upsert` (overwrite that match's rows each call).
  - Broad `except` with `logger.exception`, per existing service style.
- `team_leaders(self, team) -> dict[str, list[dict]]`: read the store, filter to `team`
  (canonical), group by player → `goals`=Σ, `assists`=Σ, `cards`=Σyellow+Σred (also keep
  yellow/red), `rating`=avg(non-null), `apps`=count distinct match_id; return ranked
  rows per stat key (`goals`/`assists`/`cards`/`rating`).

### 4. Component — `src/components/leaders_card.py`
- Replace the empty-state body with: a `SegmentedControl` (`Goals/Assists/Cards/Rating`,
  id `leaders-tabs`, already present) over a `dash_ag_grid.AgGrid` (id `leaders-grid`),
  mirroring the existing journey grid's theme/options.
- Pure helpers: `leaders_columns(stat) -> list[dict]` (colDefs: #, Player, stat, Apps)
  and `leaders_row_data(leaders, stat) -> list[dict]`. Empty list → grid shows its
  built-in "no rows" overlay (graceful pre-data state).

### 5. Wiring — `app.py`
- `live_feed` loop: after building the snapshot, also call
  `LIVE.update_player_stats(snapshot["matches"], now)` (today's matches) — and a
  one-time **backfill** of prior finished matches on first run (iterate the schedule's
  past dates via `matches_on`, update the store).
- Callback `update_leaders_grid(stat, index, live)` → Inputs `leaders-tabs.value`,
  `carousel-index.data`, `live-store.data` → `team = center_team(TEAM_NAMES, index)`;
  `leaders = LIVE.team_leaders(team) if LIVE else {}`; output grid `rowData` + `columnDefs`.

## Data flow
```
live_feed poll ─► update_player_stats(matches) ─► player_store CSV  (skip stored-finished)
carousel/tab/live-store change ─► team_leaders(team) ─► row_data(stat) ─► AgGrid
```

## Testing (TDD, offline, fixtures)
- `parse_player_stats`: goals/assists/cards from `finished_events.json`; rating from a
  `topPlayers` fixture; Own Goal excluded; assist tally; multi-player.
- `player_store`: `upsert` replaces a match's rows; `load`/`stored_match_states` round-trip;
  missing file → empty.
- `service.update_player_stats`: fake client + fixtures — finished-stored skipped (no
  fetch), finished-new fetched once, live overwritten. `team_leaders`: sum/avg/apps/rank.
- `leaders_columns` / `leaders_row_data`: shape per stat; empty input → empty rows.
- Full suite stays green and offline (no-key mode: no updates, grids empty).

## Error handling / degradation
- API errors during an update → logged, skip that match, keep the existing CSV.
- No API key (dev/tests) → no updates; if no CSV, grids render empty (no crash).
- CSV is a cache: deleting it triggers a full backfill on next run.

## Out of scope (YAGNI)
- Team perspective (goals for/against, xG, possession, standings) — calendar view, later.
- Per-player xG (no API data); full 26-man roster zero-fill and true minutes (need lineups
  + name reconciliation); committing the CSV; linking players to `squads.csv` rows.
