# Tournament Stats Drawer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A tournament-wide stats drawer (opened by a new map pin above the Team Travel Map pin) with a Team/Players switch over tabbed `dash-ag-grid` leaderboards — team tabs (Standings, Attack & xG, Possession & Passing, Defense, Discipline) and player tabs (Goals, Assists, Cards).

**Architecture:** The player side reuses the existing `live_player_stats.csv` store aggregated across all teams. The team side adds a per-match team-statistics cache (`live_team_stats.csv`) fed by the `live_feed` loop from `/statistics`, aggregated tournament-wide. The Standings tab reads `live-store` standings. A pure component exposes column/row helpers per tab; `app.py` wires a pin, a drawer, a scope→tabs callback, and a (scope, tab, live-store)→grid callback.

**Tech Stack:** Python, `dash-ag-grid` (dag), `dash-mantine-components` (dmc), `dash-leaflet` (dl), the existing `src/data/live/` subsystem (plain dataclasses + dicts, no pandas; the cache is serialization), pytest.

**Environment:** Run tests with `conda run -n wc2026-live pytest tests/ -v` (the `wc2026-live` conda env, NOT plain pytest). The branch is `feat/tournament-stats-drawer` — **do NOT merge to main without explicit user validation.**

**Reference spec:** `docs/superpowers/specs/2026-06-14-tournament-stats-drawer-design.md`

---

## File Structure

- **Modify `src/data/live/models.py`** — add `goals_for` / `goals_against` (defaulted) to `Standing`; populate in `parse_standings`.
- **Create `src/data/live/team_match_stats.py`** — pure: `STAT_KEYS`, `TeamMatchStat`, `parse_team_match_stats`.
- **Create `src/data/live/team_stats_store.py`** — CSV cache: `load` / `stored_match_states` / `upsert`.
- **Modify `src/data/live/service.py`** — `team_store` ctor arg, `update_team_stats`, `tournament_team_leaders`, `tournament_player_leaders`.
- **Create `src/components/tournament_stats.py`** — drawer builder + pure `tab_options` / `tourn_columns` / `tourn_row_data` / `standings_table_rows`.
- **Modify `src/components/map_view.py`** — `tournament_pin()` + `tournament-pin-layer`.
- **Modify `src/components/layout.py`** — add the tournament drawer to the provider.
- **Modify `app.py`** — `TEAM_STATS_PATH`, construct `LIVE` with it, pin toggle + open-drawer + tabs + grid callbacks, extend `live_feed`.
- **Modify `.gitignore`** — ignore `assets/data/live_team_stats.csv`.
- **Tests:** `tests/test_team_match_stats.py`, `tests/test_team_stats_store.py`, `tests/test_tournament_stats.py`; extend `tests/test_live_service.py`, `tests/test_live_models.py`, `tests/test_app.py`.

---

## Task 1: Standing carries goals_for / goals_against

**Files:**
- Modify: `src/data/live/models.py`
- Test: `tests/test_live_models.py` (append)

`Standing` is currently `@dataclass(frozen=True)` with fields `team, played, won, drawn, lost, goal_diff, points`. `parse_standings` builds it from `total` (which has `scoredGoals`/`receivedGoals`). We need GF/GA preserved for the Standings tab and the Attack tab's Goals column.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_live_models.py`:

```python
def test_parse_standings_keeps_goals_for_and_against():
    from src.data.live.models import parse_standings
    raw = {"groups": [
        {"name": "Group A", "standings": [
            {"team": {"name": "Mexico"}, "points": 3,
             "total": {"games": 1, "wins": 1, "draws": 0, "loses": 0,
                       "scoredGoals": 4, "receivedGoals": 1}},
        ]},
    ]}
    table = parse_standings(raw)
    row = table["Group A"][0]
    assert row.goals_for == 4
    assert row.goals_against == 1
    assert row.goal_diff == 3
```

- [ ] **Step 2: Run test to verify it fails**

Run: `conda run -n wc2026-live pytest tests/test_live_models.py::test_parse_standings_keeps_goals_for_and_against -v`
Expected: FAIL with `AttributeError: 'Standing' object has no attribute 'goals_for'`

- [ ] **Step 3: Add the fields and populate them**

In `src/data/live/models.py`, change the `Standing` dataclass to add two defaulted fields (defaults keep any existing direct constructions valid):

```python
@dataclass(frozen=True)
class Standing:
    team: str
    played: int
    won: int
    drawn: int
    lost: int
    goal_diff: int
    points: int
    goals_for: int = 0
    goals_against: int = 0
```

In `parse_standings`, change the `rows.append(Standing(...))` call to pass GF/GA (compute `goal_diff` from them as before):

```python
            total = s.get("total") or {}
            scored = int(total.get("scoredGoals", 0))
            received = int(total.get("receivedGoals", 0))
            rows.append(Standing(
                team=(s.get("team") or {}).get("name", ""),
                played=int(total.get("games", 0)),
                won=int(total.get("wins", 0)),
                drawn=int(total.get("draws", 0)),
                lost=int(total.get("loses", 0)),
                goal_diff=scored - received,
                points=int(s.get("points", 0)),
                goals_for=scored,
                goals_against=received,
            ))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `conda run -n wc2026-live pytest tests/test_live_models.py -v`
Expected: PASS (existing + the new test). The snapshot `standings` dicts (built via `vars(s)`) now include `goals_for`/`goals_against` automatically.

- [ ] **Step 5: Commit**

```bash
git add src/data/live/models.py tests/test_live_models.py
git commit -m "feat: Standing carries goals_for/goals_against"
```

---

## Task 2: Team-match-stats parser

**Files:**
- Create: `src/data/live/team_match_stats.py`
- Test: `tests/test_team_match_stats.py`

`models.parse_statistics(raw)` already returns `{team_name: {displayName: value}}`. This module maps the kept displayNames to short keys.

- [ ] **Step 1: Write the failing test**

Create `tests/test_team_match_stats.py`:

```python
from __future__ import annotations

from src.data.live.team_match_stats import (
    STAT_KEYS,
    TeamMatchStat,
    parse_team_match_stats,
)

STATS = {
    "Mexico": {
        "Expected Goals": 1.8, "Expected Assists": 1.2, "Possession": 0.6,
        "Shots on target": 4, "Shots off target": 7, "Blocked shots": 5,
        "Total passes": 520, "Successful passes": 467, "Yellow cards": 1,
        "Red cards": 1, "Unknown Stat": 99,
    },
    "South Africa": {
        "Expected Goals": 0.4, "Possession": 0.4, "Shots on target": 1,
    },
}


def test_parses_one_row_per_team_with_all_keys():
    rows = parse_team_match_stats(7, STATS)
    assert {r.team for r in rows} == {"Mexico", "South Africa"}
    mex = next(r for r in rows if r.team == "Mexico")
    assert set(mex.stats) == set(STAT_KEYS)        # every key present
    assert isinstance(rows[0], TeamMatchStat)
    assert all(r.match_id == 7 for r in rows)


def test_maps_displaynames_and_defaults_missing_to_zero():
    rows = parse_team_match_stats(7, STATS)
    mex = next(r for r in rows if r.team == "Mexico").stats
    assert mex["xg"] == 1.8
    assert mex["xa"] == 1.2
    assert mex["possession"] == 0.6
    assert mex["shots_on"] == 4
    assert mex["passes_succ"] == 467
    assert mex["yellow"] == 1 and mex["red"] == 1
    rsa = next(r for r in rows if r.team == "South Africa").stats
    assert rsa["xa"] == 0.0          # missing -> 0
    assert rsa["corners"] == 0.0     # missing -> 0


def test_ignores_unknown_displaynames():
    rows = parse_team_match_stats(7, STATS)
    mex = next(r for r in rows if r.team == "Mexico").stats
    assert "Unknown Stat" not in mex
    assert 99 not in mex.values()


def test_handles_empty_input():
    assert parse_team_match_stats(7, {}) == []
    assert parse_team_match_stats(7, None) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `conda run -n wc2026-live pytest tests/test_team_match_stats.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.data.live.team_match_stats'`

- [ ] **Step 3: Write the implementation**

Create `src/data/live/team_match_stats.py`:

```python
from __future__ import annotations

from dataclasses import dataclass

# Persisted team-stat keys (ordered) and the API displayName each maps from.
# Low-value fields (Attacks, Free Kicks, Throw-Ins, ...) are intentionally omitted.
_DISPLAY_TO_KEY = {
    "Expected Goals": "xg",
    "Expected Assists": "xa",
    "Big Chances Created": "big_chances",
    "Possession": "possession",
    "Shots on target": "shots_on",
    "Shots off target": "shots_off",
    "Blocked shots": "shots_blocked",
    "Shots within penalty area": "shots_in_box",
    "Corners": "corners",
    "Total passes": "passes_total",
    "Successful passes": "passes_succ",
    "Key Passes": "key_passes",
    "Passes Into Final Third": "passes_final_third",
    "Long Passes": "long_passes",
    "Crosses": "crosses",
    "Successful Crosses": "crosses_succ",
    "Dribbles": "dribbles",
    "Successful Dribbles": "dribbles_succ",
    "Tackles": "tackles",
    "Successful Tackles": "tackles_succ",
    "Interceptions": "interceptions",
    "Clearances": "clearances",
    "Aerial Duels": "aerials",
    "Successful Aerial Duels": "aerials_won",
    "Goalkeeper saves": "gk_saves",
    "Fouls": "fouls",
    "Offsides": "offsides",
    "Yellow cards": "yellow",
    "Red cards": "red",
}

STAT_KEYS = list(_DISPLAY_TO_KEY.values())


@dataclass(frozen=True)
class TeamMatchStat:
    match_id: int
    team: str
    stats: dict   # every key in STAT_KEYS -> float (missing -> 0.0)


def parse_team_match_stats(match_id: int, statistics) -> list[TeamMatchStat]:
    """One TeamMatchStat per team from a parsed statistics dict
    ({team: {displayName: value}}). Unknown displayNames are ignored; any
    persisted key absent from the API defaults to 0.0."""
    out = []
    for team, sd in (statistics or {}).items():
        vals = {k: 0.0 for k in STAT_KEYS}
        for disp, value in (sd or {}).items():
            key = _DISPLAY_TO_KEY.get(disp)
            if key is None or value is None:
                continue
            try:
                vals[key] = float(value)
            except (TypeError, ValueError):
                pass
        out.append(TeamMatchStat(match_id=match_id, team=team, stats=vals))
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `conda run -n wc2026-live pytest tests/test_team_match_stats.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add src/data/live/team_match_stats.py tests/test_team_match_stats.py
git commit -m "feat: parse per-match team statistics into keyed rows"
```

---

## Task 3: Team-stats store (CSV cache)

**Files:**
- Create: `src/data/live/team_stats_store.py`
- Test: `tests/test_team_stats_store.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_team_stats_store.py`:

```python
from __future__ import annotations

from src.data.live import team_stats_store
from src.data.live.team_match_stats import STAT_KEYS, TeamMatchStat


def _row(match_id, team, **overrides):
    stats = {k: 0.0 for k in STAT_KEYS}
    stats.update(overrides)
    return TeamMatchStat(match_id=match_id, team=team, stats=stats)


def test_load_missing_file_returns_empty(tmp_path):
    assert team_stats_store.load(tmp_path / "nope.csv") == {}
    assert team_stats_store.stored_match_states(tmp_path / "nope.csv") == {}


def test_upsert_then_load_roundtrip(tmp_path):
    path = tmp_path / "ts.csv"
    team_stats_store.upsert(path, 1, "finished",
                            [_row(1, "Mexico", xg=1.8, shots_on=4, possession=0.6)])
    loaded = team_stats_store.load(path)
    assert set(loaded) == {1}
    row = loaded[1][0]
    assert row.team == "Mexico"
    assert row.stats["xg"] == 1.8
    assert row.stats["shots_on"] == 4.0
    assert row.stats["possession"] == 0.6
    assert set(row.stats) == set(STAT_KEYS)
    assert team_stats_store.stored_match_states(path) == {1: "finished"}


def test_upsert_replaces_only_target_match(tmp_path):
    path = tmp_path / "ts.csv"
    team_stats_store.upsert(path, 1, "finished", [_row(1, "Mexico", xg=1.0)])
    team_stats_store.upsert(path, 2, "live", [_row(2, "Brazil", xg=3.0)])
    team_stats_store.upsert(path, 1, "finished", [_row(1, "Mexico", xg=5.0)])
    loaded = team_stats_store.load(path)
    assert loaded[1][0].stats["xg"] == 5.0
    assert loaded[2][0].stats["xg"] == 3.0
    assert team_stats_store.stored_match_states(path) == {1: "finished", 2: "live"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `conda run -n wc2026-live pytest tests/test_team_stats_store.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.data.live.team_stats_store'`

- [ ] **Step 3: Write the implementation**

Create `src/data/live/team_stats_store.py`:

```python
from __future__ import annotations

import csv
import os
from pathlib import Path

from src.data.live.team_match_stats import STAT_KEYS, TeamMatchStat

# A gitignored cache of per-match team statistics. `state` records the match
# state at write time so the updater can skip finished matches already on disk.
FIELDS = ["match_id", "team", "state"] + STAT_KEYS


def load(path) -> dict[int, list[TeamMatchStat]]:
    """match_id -> list[TeamMatchStat]. Missing file -> {}."""
    p = Path(path)
    if not p.exists():
        return {}
    out: dict[int, list[TeamMatchStat]] = {}
    with p.open(newline="") as f:
        for row in csv.DictReader(f):
            mid = int(row["match_id"])
            stats = {k: float(row[k]) if row.get(k) else 0.0 for k in STAT_KEYS}
            out.setdefault(mid, []).append(
                TeamMatchStat(match_id=mid, team=row["team"], stats=stats))
    return out


def stored_match_states(path) -> dict[int, str]:
    """match_id -> last stored state. Missing file -> {}."""
    p = Path(path)
    if not p.exists():
        return {}
    out: dict[int, str] = {}
    with p.open(newline="") as f:
        for row in csv.DictReader(f):
            out[int(row["match_id"])] = row["state"]
    return out


def upsert(path, match_id: int, state: str, rows) -> None:
    """Atomically replace all rows for `match_id` with `rows` (tagged `state`)."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    kept = []
    if p.exists():
        with p.open(newline="") as f:
            kept = [r for r in csv.DictReader(f) if int(r["match_id"]) != match_id]
    tmp = p.with_suffix(p.suffix + ".tmp")
    with tmp.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for r in kept:
            w.writerow({k: r.get(k, "") for k in FIELDS})
        for s in rows:
            base = {"match_id": s.match_id, "team": s.team, "state": state}
            base.update({k: s.stats.get(k, 0.0) for k in STAT_KEYS})
            w.writerow(base)
    os.replace(tmp, p)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `conda run -n wc2026-live pytest tests/test_team_stats_store.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add src/data/live/team_stats_store.py tests/test_team_stats_store.py
git commit -m "feat: csv-backed per-match team-stats store"
```

---

## Task 4: Service — `team_store` ctor + `update_team_stats`

**Files:**
- Modify: `src/data/live/service.py`
- Test: `tests/test_live_service.py` (append)

`service.py` already imports `from src.data.live import models, player_store`, `from src.data.live.player_stats import parse_player_stats`, `from src.data.live.reconcile import canonical_team, find_stadium, normalize`, and `from pathlib import Path`. `__init__` currently ends with `self._player_store = Path(player_store) if player_store else None` then `self._cache = {}` and `self._last_good = None`. `update_player_stats` is the pattern to mirror.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_live_service.py`:

```python
# ---------------------------------------------------------------------------
# update_team_stats
# ---------------------------------------------------------------------------

from src.data.live import team_stats_store  # noqa: E402


class _TeamStatsClient(_FakeClient):
    def __init__(self):
        super().__init__()
        self.stat_calls = {}

    def statistics(self, match_id):
        self.stat_calls[match_id] = self.stat_calls.get(match_id, 0) + 1
        return [
            {"team": {"name": "USA"}, "statistics": [
                {"displayName": "Expected Goals", "value": 1.5},
                {"displayName": "Shots on target", "value": 4},
                {"displayName": "Possession", "value": 0.6},
                {"displayName": "Yellow cards", "value": 2}]},
            {"team": {"name": "Paraguay"}, "statistics": [
                {"displayName": "Expected Goals", "value": 0.7},
                {"displayName": "Possession", "value": 0.4}]},
        ]


def test_update_team_stats_fetches_and_stores_finished(tmp_path):
    path = tmp_path / "ts.csv"
    c = _TeamStatsClient()
    svc = LiveDataService(c, _index(), team_store=path)
    svc.update_team_stats([{"match_id": 1, "state": MatchState.FINISHED.value}], now=0.0)
    assert team_stats_store.stored_match_states(path) == {1: MatchState.FINISHED.value}
    assert c.stat_calls[1] == 1
    loaded = team_stats_store.load(path)
    usa = next(r for r in loaded[1] if r.team == "USA")
    assert usa.stats["xg"] == 1.5


def test_update_team_stats_skips_already_stored_finished(tmp_path):
    path = tmp_path / "ts.csv"
    c = _TeamStatsClient()
    svc = LiveDataService(c, _index(), team_store=path)
    m = [{"match_id": 1, "state": MatchState.FINISHED.value}]
    svc.update_team_stats(m, now=0.0)
    svc.update_team_stats(m, now=1.0)
    assert c.stat_calls[1] == 1


def test_update_team_stats_overwrites_live(tmp_path):
    path = tmp_path / "ts.csv"
    c = _TeamStatsClient()
    svc = LiveDataService(c, _index(), team_store=path)
    m = [{"match_id": 2, "state": MatchState.LIVE.value}]
    svc.update_team_stats(m, now=0.0)
    svc.update_team_stats(m, now=1.0)
    assert c.stat_calls[2] == 2


def test_update_team_stats_noop_without_store():
    svc = LiveDataService(_TeamStatsClient(), _index())   # no team_store
    svc.update_team_stats([{"match_id": 1, "state": "finished"}], now=0.0)  # no crash
```

- [ ] **Step 2: Run test to verify it fails**

Run: `conda run -n wc2026-live pytest tests/test_live_service.py -k update_team_stats -v`
Expected: FAIL with `TypeError: __init__() got an unexpected keyword argument 'team_store'`

- [ ] **Step 3: Implement**

In `src/data/live/service.py`, add these imports next to the existing live imports:

```python
from src.data.live import team_stats_store
from src.data.live.team_match_stats import parse_team_match_stats
```

Change `__init__` to accept `team_store` (add the parameter after `player_store=None`, and store it next to `self._player_store`):

```python
    def __init__(self, client, stadium_index, league_id=LEAGUE_ID, season=SEASON,
                 player_store=None, team_store=None):
        self._client = client
        self._stadium_index = stadium_index
        self._league_id = league_id
        self._season = season
        self._player_store = Path(player_store) if player_store else None
        self._team_store = Path(team_store) if team_store else None
        self._cache: dict[str, tuple[float, object]] = {}
        self._last_good: dict | None = None
```

Add `update_team_stats` immediately after `update_player_stats`:

```python
    def update_team_stats(self, matches, now: float) -> None:
        """Refresh the team-stats cache from today's matches (mirrors
        update_player_stats). Finished & already stored -> skip; finished-new or
        live -> fetch /statistics once and overwrite that match's rows."""
        if self._team_store is None:
            return
        stored = team_stats_store.stored_match_states(self._team_store)
        live_states = {models.MatchState.LIVE.value, models.MatchState.HALF_TIME.value}
        for m in matches:
            mid = m.get("match_id")
            state = m.get("state")
            if mid is None:
                continue
            finished = state == models.MatchState.FINISHED.value
            if finished and stored.get(mid) == models.MatchState.FINISHED.value:
                continue
            if not (finished or state in live_states):
                continue
            try:
                parsed = models.parse_statistics(self._client.statistics(mid))
                rows = parse_team_match_stats(mid, parsed)
                team_stats_store.upsert(self._team_store, mid, state, rows)
            except Exception:
                logger.exception("team stats update failed for match %s", mid)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `conda run -n wc2026-live pytest tests/test_live_service.py -v`
Expected: PASS (all existing + 4 new)

- [ ] **Step 5: Commit**

```bash
git add src/data/live/service.py tests/test_live_service.py
git commit -m "feat: LiveDataService.update_team_stats + team_store"
```

---

## Task 5: Service — tournament aggregators

**Files:**
- Modify: `src/data/live/service.py`
- Test: `tests/test_live_service.py` (append)

Two aggregators: `tournament_player_leaders` (whole player store, no team filter, adds Team) and `tournament_team_leaders(standings)` (team store, sums + averages + recomputed ratios + GF join). Both return display-ready numeric rows; the component only picks/orders columns.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_live_service.py`:

```python
# ---------------------------------------------------------------------------
# tournament_player_leaders / tournament_team_leaders
# ---------------------------------------------------------------------------

from src.data.live.player_stats import PlayerMatchStat  # noqa: E402
from src.data.live.team_match_stats import TeamMatchStat, STAT_KEYS  # noqa: E402


def _pstat(mid, team, player, pid, goals=0, assists=0, yellow=0, red=0):
    return PlayerMatchStat(match_id=mid, team=team, player=player, player_id=pid,
                           goals=goals, assists=assists, yellow=yellow, red=red)


def _tstat(mid, team, **ov):
    stats = {k: 0.0 for k in STAT_KEYS}
    stats.update(ov)
    return TeamMatchStat(match_id=mid, team=team, stats=stats)


def test_tournament_player_leaders_aggregates_all_teams(tmp_path):
    path = tmp_path / "ps.csv"
    player_store.upsert(path, 1, "finished",
                        [_pstat(1, "USA", "F. Balogun", 100, goals=2, yellow=1),
                         _pstat(1, "Brazil", "Vinicius", 200, goals=1, assists=1)])
    player_store.upsert(path, 2, "finished",
                        [_pstat(2, "USA", "F. Balogun", 100, goals=1)])
    svc = LiveDataService(_FakeClient(), _index(), player_store=path)
    L = svc.tournament_player_leaders()
    goals = L["goals"]
    assert goals[0]["player"] == "F. Balogun"
    assert goals[0]["team"] == "USA"
    assert goals[0]["value"] == 3        # 2 + 1 across two matches
    assert goals[0]["apps"] == 2
    cards = L["cards"][0]
    assert cards["yellow"] == 1 and cards["red"] == 0


def test_tournament_player_leaders_empty_without_store():
    svc = LiveDataService(_FakeClient(), _index())
    assert svc.tournament_player_leaders() == {}


def test_tournament_team_leaders_sums_avgs_and_ratios(tmp_path):
    path = tmp_path / "ts.csv"
    team_stats_store.upsert(path, 1, "finished",
                            [_tstat(1, "USA", xg=1.5, shots_on=4, shots_off=6,
                                    passes_total=400, passes_succ=300, possession=0.6,
                                    yellow=1)])
    team_stats_store.upsert(path, 2, "finished",
                            [_tstat(2, "USA", xg=0.5, shots_on=2, shots_off=4,
                                    passes_total=600, passes_succ=480, possession=0.5,
                                    yellow=2)])
    svc = LiveDataService(_FakeClient(), _index(), team_store=path)
    standings = {"Group A": [{"team": "USA", "goals_for": 5, "goals_against": 2,
                              "goal_diff": 3, "points": 6, "played": 2,
                              "won": 2, "drawn": 0, "lost": 0}]}
    T = svc.tournament_team_leaders(standings)
    atk = next(r for r in T["attack"] if r["team"] == "USA")
    assert atk["xg"] == 2.0                 # summed
    assert atk["shots"] == 16               # (4+6)+(2+4)
    assert atk["goals"] == 5                # from standings GF
    assert atk["apps"] == 2
    poss = next(r for r in T["possession"] if r["team"] == "USA")
    assert poss["possession"] == 55.0       # mean(0.6,0.5)*100
    assert poss["pass_acc"] == 78.0         # 780/1000 *100
    disc = next(r for r in T["discipline"] if r["team"] == "USA")
    assert disc["yellow"] == 3


def test_tournament_team_leaders_empty_without_store():
    svc = LiveDataService(_FakeClient(), _index())
    assert svc.tournament_team_leaders() == {}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `conda run -n wc2026-live pytest tests/test_live_service.py -k tournament -v`
Expected: FAIL with `AttributeError: 'LiveDataService' object has no attribute 'tournament_player_leaders'`

- [ ] **Step 3: Implement**

Add the import for the team-stats keys near the other service imports:

```python
from src.data.live.team_match_stats import STAT_KEYS, parse_team_match_stats
```

(replace the Task-4 line `from src.data.live.team_match_stats import parse_team_match_stats` with the line above so both names are imported).

Add both methods after `team_leaders` (and before `_match_dict`):

```python
    def tournament_player_leaders(self) -> dict:
        """Player leaders across the whole tournament (every team). Same grouping
        as team_leaders but unscoped, with a Team column. {} when no store."""
        if self._player_store is None:
            return {}
        by_match = player_store.load(self._player_store)
        groups: dict = {}
        for rows in by_match.values():
            for r in rows:
                key = r.player_id if r.player_id else (canonical_team(r.team), normalize(r.player))
                g = groups.get(key)
                if g is None:
                    g = {"player": r.player, "team": r.team, "goals": 0, "assists": 0,
                         "yellow": 0, "red": 0, "matches": set()}
                    groups[key] = g
                if len(r.player) > len(g["player"]):
                    g["player"] = r.player
                g["goals"] += r.goals
                g["assists"] += r.assists
                g["yellow"] += r.yellow
                g["red"] += r.red
                g["matches"].add(r.match_id)

        def ranked(value_fn, keep_fn, extra_fn=None):
            out = []
            for g in groups.values():
                if not keep_fn(g):
                    continue
                row = {"player": g["player"], "team": g["team"],
                       "value": value_fn(g), "apps": len(g["matches"])}
                if extra_fn is not None:
                    row.update(extra_fn(g))
                out.append(row)
            out.sort(key=lambda d: (-d["value"], d["player"]))
            return out

        return {
            "goals": ranked(lambda g: g["goals"], lambda g: g["goals"] > 0),
            "assists": ranked(lambda g: g["assists"], lambda g: g["assists"] > 0),
            "cards": ranked(lambda g: g["yellow"] + g["red"],
                            lambda g: (g["yellow"] + g["red"]) > 0,
                            lambda g: {"yellow": g["yellow"], "red": g["red"]}),
        }

    def tournament_team_leaders(self, standings=None) -> dict:
        """Team leaders across the tournament: per-team sums of counting stats,
        mean possession, recomputed shot/pass accuracy, and goals from standings.
        Returns {"attack"|"possession"|"defense"|"discipline": [row, ...]}.
        {} when no team store."""
        if self._team_store is None:
            return {}
        by_match = team_stats_store.load(self._team_store)
        agg: dict = {}
        for rows in by_match.values():
            for r in rows:
                key = canonical_team(r.team)
                a = agg.get(key)
                if a is None:
                    a = {"team": r.team, "sums": {k: 0.0 for k in STAT_KEYS},
                         "poss": [], "matches": 0}
                    agg[key] = a
                for k in STAT_KEYS:
                    a["sums"][k] += r.stats.get(k, 0.0)
                a["poss"].append(r.stats.get("possession", 0.0))
                a["matches"] += 1

        # Goals from standings (canonical team -> goals_for).
        gf = {}
        for table in (standings or {}).values():
            for s in table:
                gf[canonical_team(s["team"])] = s.get("goals_for", 0)

        def _i(x):
            return int(round(x))

        def _pct(num, den):
            return round(num / den * 100, 1) if den else 0.0

        attack, possession, defense, discipline = [], [], [], []
        for key, a in agg.items():
            s = a["sums"]
            apps = a["matches"]
            shots = s["shots_on"] + s["shots_off"] + s["shots_blocked"]
            attack.append({
                "team": a["team"], "goals": gf.get(key, 0),
                "xg": round(s["xg"], 2), "xa": round(s["xa"], 2),
                "big_chances": _i(s["big_chances"]), "shots": _i(shots),
                "shots_on": _i(s["shots_on"]), "shots_off": _i(s["shots_off"]),
                "shot_acc": _pct(s["shots_on"], shots),
                "shots_in_box": _i(s["shots_in_box"]),
                "shots_blocked": _i(s["shots_blocked"]),
                "corners": _i(s["corners"]), "apps": apps,
            })
            possession.append({
                "team": a["team"],
                "possession": round(sum(a["poss"]) / apps * 100, 1) if apps else 0.0,
                "passes_total": _i(s["passes_total"]),
                "pass_acc": _pct(s["passes_succ"], s["passes_total"]),
                "key_passes": _i(s["key_passes"]),
                "passes_final_third": _i(s["passes_final_third"]),
                "long_passes": _i(s["long_passes"]),
                "crosses": _i(s["crosses"]), "crosses_succ": _i(s["crosses_succ"]),
                "dribbles": _i(s["dribbles"]), "dribbles_succ": _i(s["dribbles_succ"]),
                "apps": apps,
            })
            defense.append({
                "team": a["team"], "tackles": _i(s["tackles"]),
                "tackles_succ": _i(s["tackles_succ"]),
                "interceptions": _i(s["interceptions"]),
                "clearances": _i(s["clearances"]), "aerials": _i(s["aerials"]),
                "aerials_won": _i(s["aerials_won"]), "gk_saves": _i(s["gk_saves"]),
                "apps": apps,
            })
            discipline.append({
                "team": a["team"], "yellow": _i(s["yellow"]), "red": _i(s["red"]),
                "fouls": _i(s["fouls"]), "offsides": _i(s["offsides"]), "apps": apps,
            })

        attack.sort(key=lambda r: (-r["goals"], -r["xg"], r["team"]))
        possession.sort(key=lambda r: (-r["possession"], r["team"]))
        defense.sort(key=lambda r: (-r["tackles_succ"], r["team"]))
        discipline.sort(key=lambda r: (-r["yellow"], -r["red"], r["team"]))
        return {"attack": attack, "possession": possession,
                "defense": defense, "discipline": discipline}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `conda run -n wc2026-live pytest tests/test_live_service.py -v`
Expected: PASS (all existing + 4 new)

- [ ] **Step 5: Commit**

```bash
git add src/data/live/service.py tests/test_live_service.py
git commit -m "feat: tournament_player_leaders + tournament_team_leaders aggregators"
```

---

## Task 6: Tournament-stats component (drawer + pure helpers)

**Files:**
- Create: `src/components/tournament_stats.py`
- Test: `tests/test_tournament_stats.py`

Mirror `src/components/squad_table.py` for the AG-grid (`import dash_ag_grid as dag`, `ag-theme-quartz-dark` class, `dashGridOptions`) and `src/components/filter_panel.py` for the frosted right `dmc.Drawer`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_tournament_stats.py`:

```python
import dash_ag_grid as dag
import dash_mantine_components as dmc

from src.components.tournament_stats import (
    build_tournament_drawer,
    tab_options,
    tourn_columns,
    tourn_row_data,
    standings_table_rows,
)


def _walk(node):
    yield node
    children = getattr(node, "children", None)
    if isinstance(children, (list, tuple)):
        for c in children:
            yield from _walk(c)
    elif children is not None:
        yield from _walk(children)


def test_drawer_has_scope_switch_tabs_and_grid():
    drawer = build_tournament_drawer()
    assert isinstance(drawer, dmc.Drawer)
    assert drawer.id == "tournament-drawer"
    seg_ids = {n.id for n in _walk(drawer) if isinstance(n, dmc.SegmentedControl)}
    assert {"tourn-scope", "tourn-tabs"} <= seg_ids
    grid = next(n for n in _walk(drawer) if isinstance(n, dag.AgGrid))
    assert grid.id == "tourn-grid"


def test_tab_options_per_scope():
    assert tab_options("Team") == ["Standings", "Attack & xG",
                                    "Possession & Passing", "Defense", "Discipline"]
    assert tab_options("Players") == ["Goals", "Assists", "Cards"]


def test_player_columns_and_rows():
    cols = tourn_columns("Players", "Goals")
    assert [c["headerName"] for c in cols] == ["#", "Player", "Team", "Goals", "Ap"]
    leaders = {"goals": [{"player": "A", "team": "USA", "value": 3, "apps": 2}]}
    rows = tourn_row_data("Players", "Goals", {}, leaders, {})
    assert rows == [{"rank": 1, "player": "A", "team": "USA", "value": 3, "apps": 2}]


def test_player_cards_columns_split_yellow_red():
    cols = tourn_columns("Players", "Cards")
    assert [c["headerName"] for c in cols] == ["#", "Player", "Team", "🟨", "🟥", "Ap"]


def test_team_attack_rows_passthrough():
    cols = tourn_columns("Team", "Attack & xG")
    assert cols[0]["headerName"] == "Team"
    tl = {"attack": [{"team": "USA", "goals": 5, "xg": 2.0, "apps": 2}]}
    rows = tourn_row_data("Team", "Attack & xG", tl, {}, {})
    assert rows[0]["team"] == "USA" and rows[0]["goals"] == 5


def test_standings_rows_flatten_sort_and_position():
    standings = {
        "Group A": [{"team": "USA", "points": 6, "goal_diff": 3, "goals_for": 5,
                     "goals_against": 2, "played": 2, "won": 2, "drawn": 0, "lost": 0}],
        "Group B": [{"team": "Brazil", "points": 9, "goal_diff": 6, "goals_for": 8,
                     "goals_against": 2, "played": 3, "won": 3, "drawn": 0, "lost": 0}],
    }
    rows = standings_table_rows(standings)
    assert rows[0]["team"] == "Brazil"      # 9 pts first
    assert rows[0]["pos"] == 1
    assert rows[1]["team"] == "USA"
    assert rows[1]["pos"] == 2
    assert rows[0]["gf"] == 8 and rows[0]["ga"] == 2


def test_invalid_tab_for_scope_falls_back_to_first():
    # transient state right after the scope switch flips
    cols = tourn_columns("Players", "Defense")           # Defense is a Team tab
    assert [c["headerName"] for c in cols][:2] == ["#", "Player"]   # fell back to Goals
    rows = tourn_row_data("Players", "Defense", {}, {}, {})
    assert rows == []


def test_empty_inputs_give_empty_rows():
    assert tourn_row_data("Team", "Standings", {}, {}, {}) == []
    assert tourn_row_data("Team", "Attack & xG", {}, {}, {}) == []
    assert tourn_row_data("Players", "Goals", {}, {}, {}) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `conda run -n wc2026-live pytest tests/test_tournament_stats.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.components.tournament_stats'`

- [ ] **Step 3: Write the implementation**

Create `src/components/tournament_stats.py`:

```python
from __future__ import annotations

import dash_ag_grid as dag
import dash_mantine_components as dmc

# ---- tab catalogue -------------------------------------------------------

TEAM_TABS = ["Standings", "Attack & xG", "Possession & Passing", "Defense", "Discipline"]
PLAYER_TABS = ["Goals", "Assists", "Cards"]

# Team stat tabs (not Standings) -> the tournament_team_leaders key.
_TEAM_TAB_KEY = {"Attack & xG": "attack", "Possession & Passing": "possession",
                 "Defense": "defense", "Discipline": "discipline"}
# Player tabs -> the tournament_player_leaders key.
_PLAYER_TAB_KEY = {"Goals": "goals", "Assists": "assists", "Cards": "cards"}

_GRID_OPTIONS = {"suppressCellFocus": True, "rowHeight": 32, "headerHeight": 34,
                 "overlayNoRowsTemplate": "No data yet"}


def _num(header, field, width=66):
    return {"headerName": header, "field": field, "width": width,
            "sortable": True, "type": "rightAligned"}


# colDefs per (scope, tab). Player tabs lead with a # rank; team tabs lead with Team.
def _columns_for(scope, tab):
    if scope == "Players":
        rank = {"headerName": "#", "field": "rank", "width": 44, "sortable": False}
        player = {"headerName": "Player", "field": "player", "flex": 1,
                  "minWidth": 120, "sortable": True}
        team = {"headerName": "Team", "field": "team", "width": 110, "sortable": True}
        if tab == "Cards":
            return [rank, player, team, _num("🟨", "yellow", 50),
                    _num("🟥", "red", 50), _num("Ap", "apps", 50)]
        stat = {"Goals": "value", "Assists": "value"}[tab]
        head = {"Goals": "Goals", "Assists": "Assists"}[tab]
        return [rank, player, team, _num(head, stat, 70), _num("Ap", "apps", 50)]

    team = {"headerName": "Team", "field": "team", "flex": 1, "minWidth": 120,
            "sortable": True}
    if tab == "Standings":
        return [
            {"headerName": "Pos", "field": "pos", "width": 52, "sortable": True},
            team,
            {"headerName": "Grp", "field": "group", "width": 56, "sortable": True},
            _num("P", "played", 44), _num("W", "won", 44), _num("D", "drawn", 44),
            _num("L", "lost", 44), _num("GF", "gf", 48), _num("GA", "ga", 48),
            _num("GD", "gd", 50), _num("Pts", "points", 52),
        ]
    if tab == "Attack & xG":
        return [team, _num("Goals", "goals", 60), _num("xG", "xg", 56),
                _num("xA", "xa", 56), _num("BigCh", "big_chances", 64),
                _num("Shots", "shots", 60), _num("OnT", "shots_on", 52),
                _num("OffT", "shots_off", 54), _num("Acc%", "shot_acc", 58),
                _num("InBox", "shots_in_box", 60), _num("Blk", "shots_blocked", 50),
                _num("Cor", "corners", 50), _num("Ap", "apps", 48)]
    if tab == "Possession & Passing":
        return [team, _num("Poss%", "possession", 62), _num("Passes", "passes_total", 66),
                _num("Acc%", "pass_acc", 58), _num("Key", "key_passes", 52),
                _num("Fin3rd", "passes_final_third", 64), _num("Long", "long_passes", 56),
                _num("Crs", "crosses", 50), _num("CrsW", "crosses_succ", 56),
                _num("Drb", "dribbles", 50), _num("DrbW", "dribbles_succ", 56),
                _num("Ap", "apps", 48)]
    if tab == "Defense":
        return [team, _num("Tkl", "tackles", 52), _num("TklW", "tackles_succ", 58),
                _num("Int", "interceptions", 52), _num("Clr", "clearances", 52),
                _num("Aer", "aerials", 52), _num("AerW", "aerials_won", 58),
                _num("Saves", "gk_saves", 60), _num("Ap", "apps", 48)]
    # Discipline
    return [team, _num("🟨", "yellow", 54), _num("🟥", "red", 54),
            _num("Fouls", "fouls", 60), _num("Off", "offsides", 52), _num("Ap", "apps", 48)]


def _resolve_tab(scope, tab):
    """Fall back to a scope's first tab when `tab` isn't valid for `scope`
    (transient state right after the switch flips)."""
    valid = PLAYER_TABS if scope == "Players" else TEAM_TABS
    return tab if tab in valid else valid[0]


def tab_options(scope: str) -> list[str]:
    return PLAYER_TABS if scope == "Players" else TEAM_TABS


def tourn_columns(scope: str, tab: str) -> list[dict]:
    return _columns_for(scope, _resolve_tab(scope, tab))


def standings_table_rows(standings: dict | None) -> list[dict]:
    """Flatten the {group: [row]} standings into one tournament table sorted by
    points (then GD, GF), with a 1-based overall position."""
    rows = []
    for group, table in (standings or {}).items():
        for s in table:
            rows.append({
                "team": s.get("team", ""), "group": group,
                "played": s.get("played", 0), "won": s.get("won", 0),
                "drawn": s.get("drawn", 0), "lost": s.get("lost", 0),
                "gf": s.get("goals_for", 0), "ga": s.get("goals_against", 0),
                "gd": s.get("goal_diff", 0), "points": s.get("points", 0),
            })
    rows.sort(key=lambda r: (-r["points"], -r["gd"], -r["gf"], r["team"]))
    for i, r in enumerate(rows):
        r["pos"] = i + 1
    return rows


def tourn_row_data(scope: str, tab: str, team_leaders: dict | None,
                   player_leaders: dict | None, standings: dict | None) -> list[dict]:
    tab = _resolve_tab(scope, tab)
    if scope == "Players":
        rows = (player_leaders or {}).get(_PLAYER_TAB_KEY[tab], [])
        return [{"rank": i + 1, **r} for i, r in enumerate(rows)]
    if tab == "Standings":
        return standings_table_rows(standings)
    return list((team_leaders or {}).get(_TEAM_TAB_KEY[tab], []))


def build_tournament_drawer() -> dmc.Drawer:
    """Right-side drawer: a Team/Players scope switch over a tab control over one
    AG grid. The grid's columnDefs/rowData are driven by app callbacks."""
    scope = dmc.SegmentedControl(id="tourn-scope", value="Team",
                                 data=["Team", "Players"], size="xs", fullWidth=True)
    tabs = dmc.SegmentedControl(id="tourn-tabs", value="Standings",
                                data=TEAM_TABS, size="xs", fullWidth=True)
    grid = dag.AgGrid(
        id="tourn-grid",
        columnDefs=tourn_columns("Team", "Standings"),
        rowData=[],
        className="ag-theme-quartz-dark tourn-grid",
        dashGridOptions=_GRID_OPTIONS,
        style={"height": "70vh", "width": "100%"},
    )
    body = dmc.Stack([scope, tabs, grid], gap="xs")
    return dmc.Drawer(
        id="tournament-drawer",
        title="Tournament Stats",
        position="right",
        size="lg",
        padding="md",
        opened=False,
        withCloseButton=True,
        withOverlay=False,
        lockScroll=False,
        zIndex=2500,
        classNames={"content": "filter-drawer-frosted",
                    "header": "filter-drawer-frosted-header"},
        children=[body],
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `conda run -n wc2026-live pytest tests/test_tournament_stats.py -v`
Expected: PASS (8 tests)

- [ ] **Step 5: Commit**

```bash
git add src/components/tournament_stats.py tests/test_tournament_stats.py
git commit -m "feat: tournament stats drawer component + pure tab/column/row helpers"
```

---

## Task 7: Tournament map pin

**Files:**
- Modify: `src/components/map_view.py`
- Test: `tests/test_map_view.py` (append)

`map_view.py` defines `filter_pin()` (a `dl.DivMarker`, id `filter-pin`, at `FILTER_PIN = [19.5, -134.5]`) and `build_map` whose children include `dl.LayerGroup(id="filter-pin-layer", children=[filter_pin()])`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_map_view.py`:

```python
def test_tournament_pin_exists_and_is_north_of_filter_pin():
    from src.components.map_view import tournament_pin, FILTER_PIN
    pin = tournament_pin()
    assert pin.id == "tournament-pin"
    assert pin.position[0] > FILTER_PIN[0]      # higher latitude => above on the map


def test_build_map_includes_tournament_pin_layer():
    import dash_leaflet as dl
    from src.components.map_view import build_map
    m = build_map([])
    layer_ids = {c.id for c in m.children if isinstance(c, dl.LayerGroup)}
    assert "tournament-pin-layer" in layer_ids
```

- [ ] **Step 2: Run test to verify it fails**

Run: `conda run -n wc2026-live pytest tests/test_map_view.py -k tournament -v`
Expected: FAIL with `ImportError: cannot import name 'tournament_pin'`

- [ ] **Step 3: Implement**

In `src/components/map_view.py`, add a constant next to `FILTER_PIN` and a `tournament_pin()` function after `filter_pin()`:

```python
# Tournament Stats control pin, placed just above the Team Travel Map pin.
TOURNAMENT_PIN = [21.3, -134.5]


def tournament_pin() -> dl.DivMarker:
    trophy = (
        '<div class="filter-pin" data-icon="trophy">'
        '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="2" stroke-linecap="round" '
        'stroke-linejoin="round"><path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6"/>'
        '<path d="M18 9h1.5a2.5 2.5 0 0 0 0-5H18"/><path d="M4 22h16"/>'
        '<path d="M10 14.66V17c0 .55-.47.98-.97 1.21C7.85 18.75 7 20.24 7 22"/>'
        '<path d="M14 14.66V17c0 .55.47.98.97 1.21C16.15 18.75 17 20.24 17 22"/>'
        '<path d="M18 2H6v7a6 6 0 0 0 12 0V2Z"/></svg>'
        "</div>"
    )
    return dl.DivMarker(
        id="tournament-pin",
        position=TOURNAMENT_PIN,
        iconOptions={
            "html": trophy,
            "className": "filter-pin-icon",
            "iconSize": [34, 34],
            "iconAnchor": [17, 17],
        },
        children=[dl.Tooltip("Tournament Stats")],
    )
```

In `build_map`, add the new layer right after the `filter-pin-layer` line:

```python
            dl.LayerGroup(id="filter-pin-layer", children=[filter_pin()]),
            dl.LayerGroup(id="tournament-pin-layer", children=[tournament_pin()]),
```

- [ ] **Step 4: Run test to verify it passes**

Run: `conda run -n wc2026-live pytest tests/test_map_view.py -v`
Expected: PASS (existing + 2 new)

- [ ] **Step 5: Commit**

```bash
git add src/components/map_view.py tests/test_map_view.py
git commit -m "feat: Tournament Stats map pin above the travel pin"
```

---

## Task 8: Wire into layout + app.py

**Files:**
- Modify: `src/components/layout.py`
- Modify: `app.py`
- Modify: `.gitignore`
- Test: `tests/test_app.py` (append)

Anchors:
- `layout.py` imports `from src.components.filter_panel import build_filter_drawer` (line ~7); its provider `return` lists `shell, drawer, filter_drawer, build_live_strip(), build_modal(), ...`.
- `app.py`: `PLAYER_STORE_PATH = DATA_DIR / "live_player_stats.csv"` then `LIVE = (LiveDataService(HighlightlyClient(api_key=_API_KEY), STADIUM_INDEX, player_store=PLAYER_STORE_PATH) if _API_KEY else None)`.
- `app.py`: `toggle_filter_pin` callback (Output `filter-pin-layer.children`, Input `mode-toggle.checked`); `open_filter_drawer` (Output `filter-drawer.opened`, `stadium-drawer.opened` allow_duplicate; Input `filter-pin.n_clicks`); `open_stadium_drawer` (Outputs incl. `filter-drawer.opened` allow_duplicate).
- `app.py`: `_backfill_player_stats()` and the `live_feed` persistent callback (calls `LIVE.update_player_stats(snap["matches"], now)` per poll).

- [ ] **Step 1: Write the failing test**

Append to `tests/test_app.py`:

```python
def test_tournament_grid_payload_team_standings():
    import app
    rows, cols = app.tournament_grid_payload("Team", "Standings", {"standings": {}})
    assert [c["headerName"] for c in cols][:2] == ["Pos", "Team"]
    assert isinstance(rows, list)


def test_tournament_grid_payload_players_goals():
    import app
    rows, cols = app.tournament_grid_payload("Players", "Goals", {})
    assert [c["headerName"] for c in cols] == ["#", "Player", "Team", "Goals", "Ap"]
    assert isinstance(rows, list)


def test_app_layout_has_tournament_drawer():
    import app
    from dash_mantine_components import Drawer

    def walk(n):
        yield n
        ch = getattr(n, "children", None)
        if isinstance(ch, (list, tuple)):
            for c in ch:
                yield from walk(c)
        elif ch is not None:
            yield from walk(ch)

    ids = {n.id for n in walk(app.app.layout) if isinstance(n, Drawer)}
    assert "tournament-drawer" in ids
```

- [ ] **Step 2: Run test to verify it fails**

Run: `conda run -n wc2026-live pytest tests/test_app.py -k tournament -v`
Expected: FAIL with `AttributeError: module 'app' has no attribute 'tournament_grid_payload'`

- [ ] **Step 3a: Add the drawer to the layout**

In `src/components/layout.py`, add the import near the other component imports:

```python
from src.components.tournament_stats import build_tournament_drawer
```

In the provider `return`, add the drawer next to `filter_drawer`:

```python
            shell,
            drawer,
            filter_drawer,
            build_tournament_drawer(),
            build_live_strip(),
```

- [ ] **Step 3b: app.py — store path, imports, payload helper**

In `app.py`, add this import (only the three helper functions — the drawer itself is built inside `build_layout`, so `build_tournament_drawer` is imported in `layout.py`, NOT here):

```python
from src.components.tournament_stats import tab_options, tourn_columns, tourn_row_data
```

Add the team-stats cache path and pass it to `LIVE`. Replace the `LIVE = (...)` block:

```python
PLAYER_STORE_PATH = DATA_DIR / "live_player_stats.csv"
TEAM_STATS_PATH = DATA_DIR / "live_team_stats.csv"
LIVE = (
    LiveDataService(HighlightlyClient(api_key=_API_KEY), STADIUM_INDEX,
                    player_store=PLAYER_STORE_PATH, team_store=TEAM_STATS_PATH)
    if _API_KEY else None
)
```

Add the payload helper next to `leaders_payload`:

```python
def tournament_grid_payload(scope, tab, live):
    """(rowData, columnDefs) for the tournament grid. Empty rows when offline."""
    standings = (live or {}).get("standings") or {}
    tl = LIVE.tournament_team_leaders(standings) if LIVE is not None else {}
    pl = LIVE.tournament_player_leaders() if LIVE is not None else {}
    rows = tourn_row_data(scope, tab, tl, pl, standings)
    return rows, tourn_columns(scope, tab)
```

- [ ] **Step 3c: app.py — pin toggle, open drawer, tabs, grid callbacks**

Add a pin-visibility callback next to `toggle_filter_pin`:

```python
@callback(
    Output("tournament-pin-layer", "children"),
    Input("mode-toggle", "checked"),
)
def toggle_tournament_pin(team_mode):
    from src.components.map_view import tournament_pin
    return [] if team_mode else [tournament_pin()]
```

Add an open-drawer callback (opens the tournament drawer, closes the other drawers):

```python
@callback(
    Output("tournament-drawer", "opened"),
    Output("filter-drawer", "opened", allow_duplicate=True),
    Output("stadium-drawer", "opened", allow_duplicate=True),
    Input("tournament-pin", "n_clicks"),
    prevent_initial_call=True,
)
def open_tournament_drawer(n_clicks):
    if not n_clicks:
        return no_update, no_update, no_update
    return True, False, False
```

To close the tournament drawer when the other pins open, add an extra output to the two existing callbacks:
- In `open_filter_drawer`, add `Output("tournament-drawer", "opened", allow_duplicate=True)` and return `False` for it (so its return becomes `True, False, False` for filter/stadium/tournament respectively — keep the existing two and append the new one).
- In `open_stadium_drawer`, add `Output("tournament-drawer", "opened", allow_duplicate=True)` and return `False` (append to the existing return tuple).

Add the scope→tabs callback and the grid callback near `update_leaders_panel`:

```python
@callback(
    Output("tourn-tabs", "data"),
    Output("tourn-tabs", "value"),
    Input("tourn-scope", "value"),
)
def set_tournament_tabs(scope):
    opts = tab_options(scope)
    return opts, opts[0]


@callback(
    Output("tourn-grid", "rowData"),
    Output("tourn-grid", "columnDefs"),
    Input("tourn-scope", "value"),
    Input("tourn-tabs", "value"),
    Input("live-store", "data"),
)
def update_tournament_grid(scope, tab, live):
    return tournament_grid_payload(scope, tab, live)
```

- [ ] **Step 3d: app.py — feed the team-stats cache**

Rename `_backfill_player_stats` to `_backfill_live_stats` and have it update both stores:

```python
def _backfill_live_stats():
    """Refresh both per-match caches from past scheduled dates, once per process
    start. Cheaply idempotent: updaters skip finished matches already on disk."""
    today = date.today()
    now = time.monotonic()
    for d in sorted({m.date for m in MATCHES if m.date <= today}):
        day = LIVE.matches_on(d.isoformat(), now)
        LIVE.update_player_stats(day, now)
        LIVE.update_team_stats(day, now)
```

In `live_feed`, update the backfill call and add the per-poll team-stats update:

```python
    await asyncio.to_thread(_backfill_live_stats)
    while not ws.is_shutdown:
        now = asyncio.get_running_loop().time()
        snap = await asyncio.to_thread(LIVE.snapshot, date.today().isoformat(), now)
        set_props("live-store", {"data": snap})
        await asyncio.to_thread(LIVE.update_player_stats, snap["matches"], now)
        await asyncio.to_thread(LIVE.update_team_stats, snap["matches"], now)
        await asyncio.sleep(next_delay(snap))
```

- [ ] **Step 4: Run the new tests, then the full suite**

Run: `conda run -n wc2026-live pytest tests/test_app.py -k tournament -v`
Expected: PASS (3 tests)

Run: `conda run -n wc2026-live pytest tests/ -q`
Expected: all pass (was 362 + the new tests).

- [ ] **Step 5: Gitignore the cache**

Add to `.gitignore` (next to the player-stats cache line):

```
assets/data/live_team_stats.csv
```

- [ ] **Step 6: Commit**

```bash
git add app.py src/components/layout.py .gitignore tests/test_app.py
git commit -m "feat: wire tournament stats drawer (pin, drawer, callbacks, team-stats feed)"
```

---

## Notes for the implementer

- **No pandas in `src/data/live/`** — plain dataclasses/dicts + stdlib `csv`, matching `player_store`/`models`.
- **The two aggregators intentionally don't share code with `team_leaders`** (which filters to one team and is part of the already-merged leaders card). Duplication here keeps that feature untouched; do not refactor it.
- **Drawer coordination:** the tournament drawer and the filter drawer are both right-side and overlay-less, so they must be mutually exclusive — that's why opening one closes the other (and the left stadium drawer).
- **Offline/no-key is the test baseline:** `LIVE is None` → both aggregators return `{}` and `tournament_grid_payload` returns empty rows with valid columns; the whole suite runs without a key.
- **Caches are gitignored** and rebuilt by the backfill on next run; deleting them is safe.
- **Branch discipline:** stay on `feat/tournament-stats-drawer`; do not merge to main without user validation.
```
