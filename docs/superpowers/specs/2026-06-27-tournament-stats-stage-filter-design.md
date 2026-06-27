# Tournament Stats — Group-Stage Filter Design

**Date:** 2026-06-27
**Status:** Approved (pending spec review)

## Problem

The Tournament Stats drawer aggregates team/player leaders across **every**
played match. Once the knockout rounds begin, eliminated teams' group-stage
contributions sit alongside knockout data, and the combined table stops telling
a coherent story. Users need to narrow the stats to the group stage.

## Decision Summary

- **Control:** a binary toggle — **All** / **Group Stage**.
- **Default:** **All** (everything accumulated so far). Users opt into
  "Group Stage" to narrow.
- **Approach (A):** tag each stored stat row with the match's stage at
  write time, derived from a kickoff-date cutoff. Read-time aggregation skips
  knockout-tagged rows when the toggle is on "Group Stage".

## Why a stored stage tag (Approach A)

The live stat stores (`live_team_stats.csv`, `live_player_stats.csv`) key rows
by API `match_id` + `state` only — no round/stage. The fixture schedule
(`matches.csv`) has a `stage` column but uses placeholder team names for
knockout rows ("Winner Group A"), so joining live knockout matches back to
fixtures by team name is unreliable. The robust, cheap option is to classify a
match's stage **when its stats are written** (the write path already sees the
match's `kickoff`) and persist a `stage` value on each row. Read-time filtering
is then a simple field check.

The group/knockout boundary is unambiguous by kickoff time: the last group
match kicks off 2026-06-28 02:00 UTC; the first Round-of-32 match is
2026-06-28 19:00 UTC.

## Architecture

```
matches.csv ──► MatchRepository ──► knockout_start (min non-group kickoff)
                                          │
                                          ▼
                              LiveDataService(knockout_start=…)
                                          │  (write path)
   update_team_stats / update_player_stats
        classify match.kickoff vs knockout_start ──► stage "group"|"knockout"
                                          │
                                          ▼
              team_stats_store.upsert / player_store.upsert  (stage column)
                                          │  (read path)
   tournament_team_leaders(group_only) / tournament_player_leaders(group_only)
        skip rows where stage != "group" when group_only
                                          │
                                          ▼
         tournament_grid_payload(scope, tab, live, group_only)
                                          ▲
                       update_tournament_grid  ◄── Input("tourn-stage","value")
                                          ▲
                       tourn-stage SegmentedControl  (All | Group Stage)
```

## Components

### 1. Stage classifier
A pure helper that maps a kickoff to a stage string.

- **Location:** `src/data/live/reconcile.py` (already holds fixture-matching
  helpers like `find_stadium`).
- **Signature:** `classify_stage(kickoff, knockout_start) -> str`
  - `kickoff`: a `datetime` or ISO string or `None`.
  - `knockout_start`: a `datetime` (the cutoff) or `None`.
  - Returns `"knockout"` when `knockout_start` is set and `kickoff >=
    knockout_start`; otherwise `"group"` (this covers missing kickoff, missing
    cutoff, and pre-cutoff kickoffs — all default to `"group"`, the safe value).
- **Cutoff derivation (in `app.py`):** `knockout_start = min((m.kickoff_utc for
  m in KO_MATCHES), default=None)` where `KO_MATCHES` already exists
  (`[m for m in MATCHES if m.stage != "Group Stage"]`). Passed into
  `LiveDataService`.

### 2. Stat stores — `stage` column
Both `src/data/live/team_stats_store.py` and `src/data/live/player_store.py`:

- Add `"stage"` to `FIELDS`.
- `TeamMatchStat` / `PlayerMatchStat` dataclasses gain `stage: str = "group"`.
- `load()` reads `stage` from the row, defaulting to `"group"` when the column
  is absent (legacy CSVs) or blank.
- `upsert(path, match_id, state, rows, stage="group")` gains a `stage`
  parameter and writes it on every row for that match. When rewriting the file,
  rows kept from other matches that lack a `stage` value default to `"group"`.

The tag is per-match but stored per-row, mirroring how `state` is already
handled.

### 3. Service — write path tags stage
`LiveDataService.__init__` gains `knockout_start=None`, stored as
`self._knockout_start`.

In `update_team_stats` and `update_player_stats`, before each `upsert`:
```python
stage = classify_stage(m.get("kickoff"), self._knockout_start)
... upsert(store, mid, state, rows, stage)
```

### 4. Service — read path filters
- `tournament_team_leaders(self, standings=None, group_only=False)`: in the
  `by_match` aggregation loop, `if group_only and r.stage != "group": continue`.
- `tournament_player_leaders(self, group_only=False)`: same guard.

### 5. UI — `tournament_stats.py`
- New control:
  ```python
  stage = dmc.SegmentedControl(id="tourn-stage", value="All",
                               data=["All", "Group Stage"], size="xs", fullWidth=True)
  ```
- Body becomes `dmc.Stack([scope, stage, tabs, grid], gap="xs")`.
- Helper: `group_only(stage_value) -> bool` returns `stage_value == "Group Stage"`.
- No new DMC component (SegmentedControl already used). No new colours/classes;
  reuses existing drawer styling.

### 6. App wiring — `app.py`
- `tournament_grid_payload(scope, tab, live, group_only=False)` threads the flag
  into both leader calls.
- `update_tournament_grid` gains `Input("tourn-stage", "value")` and converts it
  via `group_only(stage_value)`.

## Data flow (read)

1. User flips `tourn-stage` to "Group Stage".
2. `update_tournament_grid(scope, tab, stage_value, live)` fires →
   `group_only("Group Stage") == True`.
3. `tournament_grid_payload(..., group_only=True)` calls the leader functions
   with `group_only=True`.
4. Aggregation skips any row whose `stage != "group"`; grid shows group-stage
   leaders only.

## Error handling / edge cases

- Missing kickoff or missing cutoff → `"group"` (safe default; nothing is
  silently dropped from "Group Stage").
- Legacy CSV rows with no `stage` column → `"group"` on load.
- Offline (no `LIVE`) → existing empty-rows behaviour is unchanged; the toggle
  has no data to act on.
- `_resolve_tab` fallback behaviour is untouched.

## Known limitation (accepted)

In "All" mode, the Team-tab **Goals** column is sourced from the live
standings (`goals_for`), which are group-stage standings. Knockout goals are
therefore not reflected in that one column under "All". **Group Stage** mode is
fully correct. Out of scope for this change; documented for future work.

## Testing (TDD)

- **classify_stage:** kickoff before cutoff → `"group"`; at/after cutoff →
  `"knockout"`; `None` kickoff → `"group"`; `None` cutoff → `"group"`; accepts
  ISO string and `datetime`.
- **team_stats_store / player_store:** `upsert` with a stage round-trips through
  `load`; a legacy row written without the column loads as `"group"`; `upsert`
  preserves other matches' rows (kept rows lacking stage default to `"group"`).
- **service aggregation:** with mixed group/knockout stored rows,
  `tournament_team_leaders(group_only=True)` and
  `tournament_player_leaders(group_only=True)` exclude knockout matches;
  `group_only=False` includes both.
- **tournament_stats:** `group_only()` helper truth table; drawer body contains
  a `tourn-stage` control with data `["All", "Group Stage"]` and value `"All"`;
  Stack order is `[scope, stage, tabs, grid]`.
- **app callback:** `update_tournament_grid` passes the stage value through as
  `group_only` (e.g. monkeypatch `tournament_grid_payload` or assert payload).

## Out of scope

- Cumulative / per-stage pickers (settled on a binary toggle).
- Fixing knockout goals in "All" mode (documented limitation above).
- Any change to the live-standings or third-place features.
