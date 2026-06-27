# Tournament Stats Group-Stage Filter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an All / Group Stage toggle to the Tournament Stats drawer that narrows team/player leaders to group-stage matches.

**Architecture:** Each stored stat row gains a `stage` tag (`group`/`knockout`) classified at write time from the match's kickoff against a cutoff derived from `matches.csv`. Read-time aggregation skips knockout-tagged rows when the toggle is on "Group Stage". The drawer gets a third `SegmentedControl` wired through the existing tournament-grid callback.

**Tech Stack:** Python, pandas, Plotly Dash, dash-mantine-components, dash-ag-grid, pytest.

## Global Constraints

- UI components: `dash-mantine-components` only (no Bootstrap / raw html.* widgets). This change reuses `dmc.SegmentedControl`, already in the drawer — no new DMC component.
- Data wrangling: `pandas`.
- TDD: write the failing test first; run `pytest tests/ -v`.
- Dark/light mode always present; full-screen, no scrollbars; responsive/mobile with no horizontal overflow.
- Preserve design coherence: reuse existing drawer styling/classes; introduce no new colours or CSS for this feature.
- All work stays on local `main` — never pushed to origin. Commit messages end with: `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.
- Default toggle state is **All**. Stage values stored on rows are the lowercase strings `"group"` and `"knockout"`. The safe default for any unknown/missing classification is `"group"`.

---

### Task 1: Stage classifier

**Files:**
- Modify: `src/data/live/reconcile.py` (add `classify_stage` + `_as_dt`)
- Test: `tests/test_live_reconcile.py`

**Interfaces:**
- Consumes: nothing from other tasks.
- Produces: `classify_stage(kickoff, knockout_start) -> str` returning `"group"` or `"knockout"`. `kickoff` may be a `datetime`, an ISO-8601 string (e.g. `"2026-06-28T19:00:00+00:00"`), or `None`. `knockout_start` is a tz-aware `datetime` cutoff or `None`. Returns `"knockout"` iff `knockout_start` is set and the parsed kickoff is `>= knockout_start`; otherwise `"group"`.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_live_reconcile.py`:

```python
from datetime import datetime, timezone

from src.data.live.reconcile import classify_stage

_KO = datetime(2026, 6, 28, 19, 0, tzinfo=timezone.utc)


def test_classify_stage_before_cutoff_is_group():
    assert classify_stage("2026-06-27T19:00:00+00:00", _KO) == "group"


def test_classify_stage_at_or_after_cutoff_is_knockout():
    assert classify_stage("2026-06-28T19:00:00+00:00", _KO) == "knockout"
    assert classify_stage("2026-07-01T19:00:00+00:00", _KO) == "knockout"


def test_classify_stage_accepts_datetime():
    dt = datetime(2026, 6, 28, 20, 0, tzinfo=timezone.utc)
    assert classify_stage(dt, _KO) == "knockout"


def test_classify_stage_missing_kickoff_defaults_group():
    assert classify_stage(None, _KO) == "group"
    assert classify_stage("not-a-date", _KO) == "group"


def test_classify_stage_no_cutoff_defaults_group():
    assert classify_stage("2026-08-01T19:00:00+00:00", None) == "group"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_live_reconcile.py -k classify_stage -v`
Expected: FAIL — `ImportError: cannot import name 'classify_stage'`.

- [ ] **Step 3: Implement the classifier**

Add to the top of `src/data/live/reconcile.py`, just under `from __future__ import annotations`:

```python
from datetime import datetime
```

Append to the end of `src/data/live/reconcile.py`:

```python
def _as_dt(value):
    """Coerce a datetime / ISO-8601 string / None to a datetime, or None."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def classify_stage(kickoff, knockout_start) -> str:
    """'knockout' if kickoff is at/after the knockout cutoff, else 'group'.

    Missing kickoff, unparseable kickoff, or missing cutoff all fall back to
    'group' — the safe default that never hides a match from Group-Stage view.
    """
    if knockout_start is None:
        return "group"
    ko = _as_dt(kickoff)
    if ko is None:
        return "group"
    return "knockout" if ko >= knockout_start else "group"
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_live_reconcile.py -k classify_stage -v`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add src/data/live/reconcile.py tests/test_live_reconcile.py
git commit -m "feat: classify_stage helper for group/knockout split

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: Team-stats store `stage` column

**Files:**
- Modify: `src/data/live/team_match_stats.py:42-46` (add `stage` field to `TeamMatchStat`)
- Modify: `src/data/live/team_stats_store.py` (FIELDS, `load`, `upsert`)
- Test: `tests/test_team_stats_store.py`

**Interfaces:**
- Consumes: nothing from other tasks.
- Produces: `TeamMatchStat` gains `stage: str = "group"`. `team_stats_store.upsert(path, match_id, state, rows, stage="group")` writes the tag on every row. `team_stats_store.load(path)` returns `TeamMatchStat` objects whose `.stage` is the stored value, defaulting to `"group"` when the column is absent/blank.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_team_stats_store.py`:

```python
def test_upsert_stores_stage_and_load_roundtrips(tmp_path):
    path = tmp_path / "ts.csv"
    team_stats_store.upsert(path, 1, "finished", [_row(1, "USA", xg=1.0)],
                            stage="knockout")
    loaded = team_stats_store.load(path)
    assert loaded[1][0].stage == "knockout"


def test_upsert_stage_defaults_to_group(tmp_path):
    path = tmp_path / "ts.csv"
    team_stats_store.upsert(path, 1, "finished", [_row(1, "USA", xg=1.0)])
    assert team_stats_store.load(path)[1][0].stage == "group"


def test_load_legacy_row_without_stage_defaults_group(tmp_path):
    path = tmp_path / "ts.csv"
    # A legacy file written before the stage column existed.
    path.write_text(
        "match_id,team,state," + ",".join(STAT_KEYS) + "\n"
        + "1,USA,finished," + ",".join(["0.0"] * len(STAT_KEYS)) + "\n"
    )
    assert team_stats_store.load(path)[1][0].stage == "group"


def test_upsert_preserves_other_matches_stage(tmp_path):
    path = tmp_path / "ts.csv"
    team_stats_store.upsert(path, 1, "finished", [_row(1, "USA", xg=1.0)],
                            stage="knockout")
    team_stats_store.upsert(path, 2, "finished", [_row(2, "Brazil", xg=2.0)],
                            stage="group")
    loaded = team_stats_store.load(path)
    assert loaded[1][0].stage == "knockout"
    assert loaded[2][0].stage == "group"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_team_stats_store.py -k stage -v`
Expected: FAIL — `TypeError: __init__() got an unexpected keyword argument 'stage'` (upsert) / `AttributeError: 'TeamMatchStat' object has no attribute 'stage'`.

- [ ] **Step 3: Add the `stage` field to the dataclass**

In `src/data/live/team_match_stats.py`, change the `TeamMatchStat` dataclass:

```python
@dataclass(frozen=True)
class TeamMatchStat:
    match_id: int
    team: str
    stats: dict   # every key in STAT_KEYS -> float (missing -> 0.0)
    stage: str = "group"
```

- [ ] **Step 4: Update the store FIELDS, load, and upsert**

In `src/data/live/team_stats_store.py`:

Change FIELDS (line 11):

```python
FIELDS = ["match_id", "team", "state", "stage"] + STAT_KEYS
```

In `load`, change the `TeamMatchStat(...)` construction (lines 24-25):

```python
            out.setdefault(mid, []).append(
                TeamMatchStat(match_id=mid, team=row["team"], stats=stats,
                              stage=row.get("stage") or "group"))
```

Change `upsert`'s signature (line 41) and body:

```python
def upsert(path, match_id: int, state: str, rows, stage: str = "group") -> None:
    """Atomically replace all rows for `match_id` with `rows` (tagged `state`
    and `stage`)."""
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
            out_row = {k: r.get(k, "") for k in FIELDS}
            out_row["stage"] = r.get("stage") or "group"
            w.writerow(out_row)
        for s in rows:
            base = {"match_id": s.match_id, "team": s.team, "state": state,
                    "stage": stage}
            base.update({k: s.stats.get(k, 0.0) for k in STAT_KEYS})
            w.writerow(base)
    os.replace(tmp, p)
```

- [ ] **Step 5: Run the store tests to verify they pass**

Run: `pytest tests/test_team_stats_store.py -v`
Expected: PASS (all existing tests plus the 4 new ones).

- [ ] **Step 6: Commit**

```bash
git add src/data/live/team_match_stats.py src/data/live/team_stats_store.py tests/test_team_stats_store.py
git commit -m "feat: persist stage tag on team-stats rows

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: Player store `stage` column

**Files:**
- Modify: `src/data/live/player_stats.py:13-22` (add `stage` field to `PlayerMatchStat`)
- Modify: `src/data/live/player_store.py` (FIELDS, `load`, `upsert`)
- Test: `tests/test_player_store.py`

**Interfaces:**
- Consumes: nothing from other tasks.
- Produces: `PlayerMatchStat` gains `stage: str = "group"`. `player_store.upsert(path, match_id, state, rows, stage="group")` writes the tag on every row. `player_store.load(path)` returns `PlayerMatchStat` objects whose `.stage` defaults to `"group"` when the column is absent/blank.

- [ ] **Step 1: Write the failing tests**

Open `tests/test_player_store.py`, note its existing row-builder helper (it constructs `PlayerMatchStat`). Add these tests, reusing that helper if present; otherwise use the inline builder shown here:

```python
from src.data.live.player_stats import PlayerMatchStat


def _pstat(mid, team, player, pid, goals=0, assists=0, yellow=0, red=0):
    return PlayerMatchStat(match_id=mid, team=team, player=player, player_id=pid,
                           goals=goals, assists=assists, yellow=yellow, red=red)


def test_upsert_stores_stage_and_load_roundtrips(tmp_path):
    path = tmp_path / "ps.csv"
    player_store.upsert(path, 1, "finished",
                        [_pstat(1, "USA", "F. Balogun", 100, goals=1)],
                        stage="knockout")
    assert player_store.load(path)[1][0].stage == "knockout"


def test_upsert_stage_defaults_to_group(tmp_path):
    path = tmp_path / "ps.csv"
    player_store.upsert(path, 1, "finished",
                        [_pstat(1, "USA", "F. Balogun", 100, goals=1)])
    assert player_store.load(path)[1][0].stage == "group"


def test_load_legacy_row_without_stage_defaults_group(tmp_path):
    path = tmp_path / "ps.csv"
    path.write_text(
        "match_id,team,player,player_id,goals,assists,yellow,red,state\n"
        "1,USA,F. Balogun,100,1,0,0,0,finished\n"
    )
    assert player_store.load(path)[1][0].stage == "group"
```

If `tests/test_player_store.py` already imports `player_store`, do not duplicate the import. Confirm the module import line at the top of the file (`from src.data.live import player_store`).

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_player_store.py -k stage -v`
Expected: FAIL — `TypeError: upsert() got an unexpected keyword argument 'stage'` / `AttributeError: ... has no attribute 'stage'`.

- [ ] **Step 3: Add the `stage` field to the dataclass**

In `src/data/live/player_stats.py`, change `PlayerMatchStat`:

```python
@dataclass(frozen=True)
class PlayerMatchStat:
    match_id: int
    team: str
    player: str
    player_id: int | None
    goals: int
    assists: int
    yellow: int
    red: int
    stage: str = "group"
```

- [ ] **Step 4: Update the store FIELDS, load, and upsert**

In `src/data/live/player_store.py`:

Change FIELDS (lines 11-12):

```python
FIELDS = ["match_id", "team", "player", "player_id",
          "goals", "assists", "yellow", "red", "state", "stage"]
```

In `load`, add `stage` to the `PlayerMatchStat(...)` construction (lines 24-33):

```python
            out.setdefault(mid, []).append(PlayerMatchStat(
                match_id=mid,
                team=row["team"],
                player=row["player"],
                player_id=int(row["player_id"]) if row["player_id"] else None,
                goals=int(row["goals"]),
                assists=int(row["assists"]),
                yellow=int(row["yellow"]),
                red=int(row["red"]),
                stage=row.get("stage") or "group",
            ))
```

Change `upsert`'s signature (line 49) and body:

```python
def upsert(path, match_id: int, state: str, rows, stage: str = "group") -> None:
    """Atomically replace all rows for `match_id` with `rows` (tagged `state`
    and `stage`)."""
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
            out_row = {k: r.get(k, "") for k in FIELDS}
            out_row["stage"] = r.get("stage") or "group"
            w.writerow(out_row)
        for s in rows:
            w.writerow({
                "match_id": s.match_id, "team": s.team, "player": s.player,
                "player_id": s.player_id if s.player_id is not None else "",
                "goals": s.goals, "assists": s.assists,
                "yellow": s.yellow, "red": s.red,
                "state": state, "stage": stage,
            })
    os.replace(tmp, p)
```

- [ ] **Step 5: Run the store tests to verify they pass**

Run: `pytest tests/test_player_store.py -v`
Expected: PASS (existing tests plus the 3 new ones).

- [ ] **Step 6: Commit**

```bash
git add src/data/live/player_stats.py src/data/live/player_store.py tests/test_player_store.py
git commit -m "feat: persist stage tag on player-stats rows

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: Service read-path `group_only` filter

**Files:**
- Modify: `src/data/live/service.py` (`tournament_player_leaders`, `tournament_team_leaders`)
- Test: `tests/test_live_service.py`

**Interfaces:**
- Consumes: `TeamMatchStat.stage` and `PlayerMatchStat.stage` from Tasks 2 & 3; stores write the tag (Tasks 2 & 3 give the upsert `stage=` kwarg).
- Produces: `tournament_player_leaders(self, group_only=False)` and `tournament_team_leaders(self, standings=None, group_only=False)`. When `group_only` is True, rows whose `stage != "group"` are excluded from aggregation. Defaults preserve current behaviour.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_live_service.py` (the `_pstat`/`_tstat` helpers and `player_store`/`team_stats_store` imports already exist in this file — reuse them; note `_pstat`/`_tstat` do not set `stage`, so call `upsert` with an explicit `stage=` to tag a match):

```python
def test_tournament_player_leaders_group_only_excludes_knockout(tmp_path):
    path = tmp_path / "ps.csv"
    player_store.upsert(path, 1, "finished",
                        [_pstat(1, "USA", "F. Balogun", 100, goals=2)],
                        stage="group")
    player_store.upsert(path, 2, "finished",
                        [_pstat(2, "USA", "F. Balogun", 100, goals=5)],
                        stage="knockout")
    svc = LiveDataService(_FakeClient(), _index(), player_store=path)
    all_goals = svc.tournament_player_leaders()["goals"][0]
    grp_goals = svc.tournament_player_leaders(group_only=True)["goals"][0]
    assert all_goals["value"] == 7      # 2 + 5 across both stages
    assert grp_goals["value"] == 2      # group stage only
    assert grp_goals["apps"] == 1


def test_tournament_team_leaders_group_only_excludes_knockout(tmp_path):
    path = tmp_path / "ts.csv"
    team_stats_store.upsert(path, 1, "finished",
                            [_tstat(1, "USA", shots_on=4)], stage="group")
    team_stats_store.upsert(path, 2, "finished",
                            [_tstat(2, "USA", shots_on=10)], stage="knockout")
    svc = LiveDataService(_FakeClient(), _index(), team_store=path)
    all_atk = next(r for r in svc.tournament_team_leaders()["attack"]
                   if r["team"] == "USA")
    grp_atk = next(r for r in
                   svc.tournament_team_leaders(group_only=True)["attack"]
                   if r["team"] == "USA")
    assert all_atk["shots"] == 14       # 4 + 10
    assert grp_atk["shots"] == 4        # group stage only
    assert grp_atk["apps"] == 1
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_live_service.py -k "group_only" -v`
Expected: FAIL — `TypeError: tournament_player_leaders() got an unexpected keyword argument 'group_only'`.

- [ ] **Step 3: Add `group_only` to `tournament_player_leaders`**

In `src/data/live/service.py`, change the method signature (line 265) and the aggregation loop (lines 272-273). The loop currently reads:

```python
        for rows in by_match.values():
            for r in rows:
```

Replace the signature line and that loop header:

```python
    def tournament_player_leaders(self, group_only: bool = False) -> dict:
```

```python
        for rows in by_match.values():
            for r in rows:
                if group_only and r.stage != "group":
                    continue
```

- [ ] **Step 4: Add `group_only` to `tournament_team_leaders`**

In `src/data/live/service.py`, change the method signature (line 309) and the aggregation loop (lines 318-319). The loop currently reads:

```python
        for rows in by_match.values():
            for r in rows:
```

Replace the signature line and that loop header:

```python
    def tournament_team_leaders(self, standings=None, group_only: bool = False) -> dict:
```

```python
        for rows in by_match.values():
            for r in rows:
                if group_only and r.stage != "group":
                    continue
```

- [ ] **Step 5: Run the service tests to verify they pass**

Run: `pytest tests/test_live_service.py -k "tournament" -v`
Expected: PASS (existing tournament tests plus the 2 new ones).

- [ ] **Step 6: Commit**

```bash
git add src/data/live/service.py tests/test_live_service.py
git commit -m "feat: group_only filter on tournament leader aggregations

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: Service write-path tags stage

**Files:**
- Modify: `src/data/live/service.py` (`__init__`, `update_player_stats`, `update_team_stats`, import)
- Test: `tests/test_live_service.py`

**Interfaces:**
- Consumes: `classify_stage` (Task 1); store `upsert(..., stage=)` (Tasks 2 & 3).
- Produces: `LiveDataService(__init__)` gains `knockout_start=None`, stored as `self._knockout_start`. `update_player_stats` and `update_team_stats` classify each match's `kickoff` against `self._knockout_start` and pass the resulting stage to `upsert`. Match dicts already carry `"kickoff"` (ISO string) via `_match_dict`.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_live_service.py`. These drive the public updaters with match dicts that carry a `kickoff`, then read back the stored stage. Inspect the file's existing `_StatsClient` / `_TeamStatsClient` fakes (used by the `update_*_stats` tests around lines 320-440) and reuse them; the snippet below shows the shape to follow — adapt the client/fake names to those already in the file:

```python
from datetime import datetime, timezone
from src.data.live import player_store, team_stats_store  # already imported above
from src.data.live.models import MatchState  # already imported in this file

_KO_START = datetime(2026, 6, 28, 19, 0, tzinfo=timezone.utc)


def _match(mid, kickoff):
    return {"match_id": mid, "state": MatchState.FINISHED.value, "kickoff": kickoff,
            "home": "USA", "away": "Brazil"}


def test_update_player_stats_tags_stage_from_kickoff(tmp_path):
    path = tmp_path / "ps.csv"
    client = _StatsClient()   # the fake already used by player-stat update tests
    svc = LiveDataService(client, _index(), player_store=path,
                          knockout_start=_KO_START)
    svc.update_player_stats([_match(1, "2026-06-20T19:00:00+00:00"),
                             _match(2, "2026-06-29T19:00:00+00:00")], 0.0)
    loaded = player_store.load(path)
    assert loaded[1][0].stage == "group"
    assert loaded[2][0].stage == "knockout"


def test_update_team_stats_tags_stage_from_kickoff(tmp_path):
    path = tmp_path / "ts.csv"
    client = _TeamStatsClient()   # the fake already used by team-stat update tests
    svc = LiveDataService(client, _index(), team_store=path,
                          knockout_start=_KO_START)
    svc.update_team_stats([_match(1, "2026-06-20T19:00:00+00:00"),
                           _match(2, "2026-06-29T19:00:00+00:00")], 0.0)
    loaded = team_stats_store.load(path)
    assert loaded[1][0].stage == "group"
    assert loaded[2][0].stage == "knockout"
```

Note: the existing fakes must return at least one stat row for a given `match_id` so a row is written. If `_StatsClient`/`_TeamStatsClient` return rows keyed to a specific match id, adjust the `_match` ids in the test to match what the fake produces, or extend the fake to return rows for ids 1 and 2. Keep the two matches' kickoffs straddling `_KO_START`.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_live_service.py -k "tags_stage" -v`
Expected: FAIL — `TypeError: __init__() got an unexpected keyword argument 'knockout_start'`.

- [ ] **Step 3: Add the import and constructor parameter**

In `src/data/live/service.py`, add `classify_stage` to the existing reconcile import. The current line (line 11) is:

```python
from src.data.live.reconcile import canonical_team, find_stadium, normalize
```

Change it to:

```python
from src.data.live.reconcile import (
    canonical_team, classify_stage, find_stadium, normalize)
```

Change `__init__` (lines 33-42) to accept and store the cutoff:

```python
    def __init__(self, client, stadium_index, league_id=LEAGUE_ID, season=SEASON,
                 player_store=None, team_store=None, knockout_start=None):
        self._client = client
        self._stadium_index = stadium_index
        self._league_id = league_id
        self._season = season
        self._player_store = Path(player_store) if player_store else None
        self._team_store = Path(team_store) if team_store else None
        self._knockout_start = knockout_start
        self._cache: dict[str, tuple[float, object]] = {}
        self._last_good: dict | None = None
```

- [ ] **Step 4: Tag stage in the updaters**

In `update_player_stats`, inside the `for m in matches:` loop, the body currently fetches and upserts (lines 182-184):

```python
            try:
                rows = parse_player_stats(mid, self._client.events(mid))
                player_store.upsert(self._player_store, mid, state, rows)
            except Exception:
                logger.exception("player stats update failed for match %s", mid)
```

Replace with:

```python
            try:
                rows = parse_player_stats(mid, self._client.events(mid))
                stage = classify_stage(m.get("kickoff"), self._knockout_start)
                player_store.upsert(self._player_store, mid, state, rows, stage)
            except Exception:
                logger.exception("player stats update failed for match %s", mid)
```

In `update_team_stats`, the body currently reads (lines 206-211):

```python
            try:
                parsed = models.parse_statistics(self._client.statistics(mid))
                rows = parse_team_match_stats(mid, parsed)
                team_stats_store.upsert(self._team_store, mid, state, rows)
            except Exception:
                logger.exception("team stats update failed for match %s", mid)
```

Replace with:

```python
            try:
                parsed = models.parse_statistics(self._client.statistics(mid))
                rows = parse_team_match_stats(mid, parsed)
                stage = classify_stage(m.get("kickoff"), self._knockout_start)
                team_stats_store.upsert(self._team_store, mid, state, rows, stage)
            except Exception:
                logger.exception("team stats update failed for match %s", mid)
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `pytest tests/test_live_service.py -k "tags_stage or update_player or update_team" -v`
Expected: PASS (existing updater tests still pass — they construct the service without `knockout_start`, so stage defaults to `"group"` — plus the 2 new ones).

- [ ] **Step 6: Commit**

```bash
git add src/data/live/service.py tests/test_live_service.py
git commit -m "feat: tag stored stats with stage at write time

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 6: Drawer toggle control + `group_only` helper

**Files:**
- Modify: `src/components/tournament_stats.py` (`group_only` helper, `build_tournament_drawer` body)
- Test: `tests/test_tournament_stats.py`

**Interfaces:**
- Consumes: nothing from other tasks.
- Produces: `group_only(stage_value: str) -> bool` returning `True` only for `"Group Stage"`. `build_tournament_drawer()` renders a `dmc.SegmentedControl` with `id="tourn-stage"`, `data=["All", "Group Stage"]`, `value="All"`, stacked between the scope switch and the tabs.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_tournament_stats.py` (the `_walk` helper already exists in this file):

```python
from src.components.tournament_stats import group_only


def test_group_only_helper():
    assert group_only("Group Stage") is True
    assert group_only("All") is False


def test_drawer_has_stage_toggle_defaulting_all():
    drawer = build_tournament_drawer()
    stage = next(n for n in _walk(drawer)
                 if getattr(n, "id", None) == "tourn-stage")
    assert isinstance(stage, dmc.SegmentedControl)
    assert list(stage.data) == ["All", "Group Stage"]
    assert stage.value == "All"


def test_drawer_stage_toggle_sits_above_tabs():
    drawer = build_tournament_drawer()
    seg_ids = [n.id for n in _walk(drawer)
               if isinstance(n, dmc.SegmentedControl)]
    assert seg_ids.index("tourn-scope") < seg_ids.index("tourn-stage") \
        < seg_ids.index("tourn-tabs")
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_tournament_stats.py -k "stage or group_only" -v`
Expected: FAIL — `ImportError: cannot import name 'group_only'`.

- [ ] **Step 3: Add the `group_only` helper**

In `src/components/tournament_stats.py`, add after the `tab_options` function (after line 74):

```python
def group_only(stage_value: str) -> bool:
    """True when the stage toggle is narrowing to the group stage."""
    return stage_value == "Group Stage"
```

- [ ] **Step 4: Add the toggle to the drawer body**

In `build_tournament_drawer` (lines 90-105), add the stage control and place it in the Stack between `scope` and `tabs`. Change the body section:

```python
    scope = dmc.SegmentedControl(id="tourn-scope", value="Team",
                                 data=["Team", "Players"], size="xs", fullWidth=True)
    stage = dmc.SegmentedControl(id="tourn-stage", value="All",
                                 data=["All", "Group Stage"], size="xs", fullWidth=True)
    tabs = dmc.SegmentedControl(id="tourn-tabs", value="Attack & xG",
                                data=TEAM_TABS, size="xs", fullWidth=True)
    grid = dag.AgGrid(
        id="tourn-grid",
        columnDefs=tourn_columns("Team", "Attack & xG"),
        rowData=[],
        className="ag-theme-quartz-dark tourn-grid",
        dashGridOptions=_GRID_OPTIONS,
        style={"height": "70vh", "width": "100%"},
    )
    body = dmc.Stack([scope, stage, tabs, grid], gap="xs")
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `pytest tests/test_tournament_stats.py -v`
Expected: PASS (existing tests plus the 3 new ones).

- [ ] **Step 6: Commit**

```bash
git add src/components/tournament_stats.py tests/test_tournament_stats.py
git commit -m "feat: All/Group Stage toggle in tournament stats drawer

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 7: App wiring — cutoff, payload flag, callback input

**Files:**
- Modify: `app.py` (LiveDataService construction, `tournament_grid_payload`, `update_tournament_grid`, import)
- Test: `tests/test_app_smoke.py` (or the existing app-level test file; see Step 1)

**Interfaces:**
- Consumes: `classify_stage` cutoff feeds `LiveDataService(knockout_start=...)` (Task 5); `tournament_team_leaders(..., group_only=)` / `tournament_player_leaders(group_only=)` (Task 4); `group_only` helper (Task 6).
- Produces: `tournament_grid_payload(scope, tab, live, group_only=False)`; `update_tournament_grid(scope, tab, stage_value, live)` reads `Input("tourn-stage", "value")` and passes `group_only(stage_value)` to the payload.

- [ ] **Step 1: Write the failing test**

The app-level test file is `tests/test_app.py`. Add the new tests there, or create `tests/test_app_tournament_wiring.py` if you prefer to keep them isolated. Add a test that calls the payload with `group_only` and asserts the flag reaches the service. Because `app.py` builds a module-level `LIVE` (None without an API key), the cleanest unit test monkeypatches `app.LIVE`:

```python
import app


class _FakeLive:
    def __init__(self):
        self.calls = []

    def tournament_team_leaders(self, standings=None, group_only=False):
        self.calls.append(("team", group_only))
        return {}

    def tournament_player_leaders(self, group_only=False):
        self.calls.append(("player", group_only))
        return {}


def test_tournament_grid_payload_passes_group_only(monkeypatch):
    fake = _FakeLive()
    monkeypatch.setattr(app, "LIVE", fake)
    app.tournament_grid_payload("Team", "Attack & xG", {"standings": {}},
                                group_only=True)
    assert ("team", True) in fake.calls
    assert ("player", True) in fake.calls


def test_tournament_grid_payload_defaults_group_only_false(monkeypatch):
    fake = _FakeLive()
    monkeypatch.setattr(app, "LIVE", fake)
    app.tournament_grid_payload("Team", "Attack & xG", {"standings": {}})
    assert ("team", False) in fake.calls
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/test_app_tournament_wiring.py -v` (or the chosen file)
Expected: FAIL — `TypeError: tournament_grid_payload() got an unexpected keyword argument 'group_only'`.

- [ ] **Step 3: Thread `group_only` through the payload**

In `app.py`, import the helper. Find the existing import (line 36):

```python
from src.components.tournament_stats import tab_options, tourn_columns, tourn_row_data
```

Change it to:

```python
from src.components.tournament_stats import (
    group_only, tab_options, tourn_columns, tourn_row_data)
```

Change `tournament_grid_payload` (lines 244-250):

```python
def tournament_grid_payload(scope, tab, live, group_only=False):
    """(rowData, columnDefs) for the tournament grid. Empty rows when offline."""
    standings = (live or {}).get("standings") or {}
    tl = (LIVE.tournament_team_leaders(standings, group_only=group_only)
          if LIVE is not None else {})
    pl = (LIVE.tournament_player_leaders(group_only=group_only)
          if LIVE is not None else {})
    rows = attach_team_flags(tourn_row_data(scope, tab, tl, pl))
    return rows, tourn_columns(scope, tab)
```

- [ ] **Step 4: Add the `tourn-stage` input to the grid callback**

In `app.py`, change the `update_tournament_grid` callback (lines 889-897). Add the new input between the tabs input and the live-store input so positional args line up:

```python
@callback(
    Output("tourn-grid", "rowData"),
    Output("tourn-grid", "columnDefs"),
    Input("tourn-scope", "value"),
    Input("tourn-tabs", "value"),
    Input("tourn-stage", "value"),
    Input("live-store", "data"),
)
def update_tournament_grid(scope, tab, stage_value, live):
    return tournament_grid_payload(scope, tab, live, group_only(stage_value))
```

- [ ] **Step 5: Pass the knockout cutoff into LiveDataService**

In `app.py`, just above the `LIVE = (...)` construction (line 111), derive the cutoff from the already-existing `KO_MATCHES` (defined at line 74). Add:

```python
KNOCKOUT_START = min((m.kickoff_utc for m in KO_MATCHES), default=None)
```

Then change the construction (lines 111-115) to pass it:

```python
LIVE = (
    LiveDataService(HighlightlyClient(api_key=_API_KEY), STADIUM_INDEX,
                    player_store=PLAYER_STORE_PATH, team_store=TEAM_STATS_PATH,
                    knockout_start=KNOCKOUT_START)
    if _API_KEY else None
)
```

- [ ] **Step 6: Run the test to verify it passes**

Run: `pytest tests/test_app_tournament_wiring.py -v` (or the chosen file)
Expected: PASS (2 tests).

- [ ] **Step 7: Run the full suite**

Run: `pytest tests/ -q`
Expected: PASS — all tests green (the new tests plus every pre-existing test; existing `tournament_grid_payload`/`update_tournament_grid` callers continue to work because `group_only` defaults to `False`).

- [ ] **Step 8: Commit**

```bash
git add app.py tests/
git commit -m "feat: wire stage filter through tournament grid callback

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Manual verification (after all tasks)

With an API key configured and the app running:

1. Open the Tournament Stats drawer. The new **All / Group Stage** toggle sits between the Team/Players switch and the tab row, defaulting to **All**.
2. Flip to **Group Stage** — the grid re-renders showing only group-stage contributions (team/player totals drop to group-stage-only where knockout data exists).
3. Flip back to **All** — totals include knockout matches again.
4. Toggle dark/light: the control follows the theme (it reuses the existing SegmentedControl styling).
5. At phone width (~390px) the drawer has no horizontal overflow; the three stacked full-width controls remain usable.

Without an API key the drawer still opens with an empty grid and the toggle present (no data to filter) — unchanged offline behaviour.
