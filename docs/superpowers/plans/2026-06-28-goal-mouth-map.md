# Goal-mouth Map Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a per-team "Goal-mouth map" bento box to the per-team view, visualizing where the carousel-selected team's shots finished (2×3 on-target grid + near-miss margins + off-target tally), aggregated across matches played, with a click-to-open left drawer listing each zone's shots.

**Architecture:** A new live-data path (shot parsing → gitignored CSV store → per-team aggregation) mirrors the existing `team_stats_store`/`update_team_stats` conventions exactly. A pure aggregation function feeds both a Plotly `dcc.Graph` component and an app-level left `dmc.Drawer`. The group table narrows from 2 grid columns to 1; the freed cell holds the new box.

**Tech Stack:** Python, Dash (FastAPI backend), Plotly (`graph_objects`), dash-mantine-components, pandas-free plain dataclasses, pytest.

## Global Constraints

- UI components: dash-mantine-components ONLY (no Bootstrap, no raw `html.Button`). Verify each DMC component's current API via context7 MCP before use.
- Map/figures: Plotly via `graph_objects`; reuse `src/components/analysis/theme.py` (`plotly_layout`). No new charting library.
- Dark/light safe: no hardcoded black text; backgrounds transparent (`paper_bgcolor`/`plot_bgcolor` = `rgba(0,0,0,0)`).
- Full-screen, no scrollbars; responsive/mobile with NO horizontal overflow.
- Title is **"Goal-mouth map"**; never "shot map".
- On-target grid is 2×3: rows {High (top), Low (bottom)} × cols {Left, Centre, Right}. No vertical middle row.
- `goalTarget` is parsed ONLY through an explicit lookup (`ZONE_MAP`), never string-split. `CloseLeft` (no space) and `Close Right And High` (compound) map correctly; unknown strings → a visible `other` bucket, never dropped.
- `null` goalTarget → `off_target` tally beside the diagram, never a frame zone.
- Outcome color enum (consistent everywhere): Goal `#1D9E75`, Saved `#378ADD`, Blocked `#888780`, near-miss/Close family `#EF9F27`, Post/woodwork `#D85A30`. Pair color with text label everywhere (never color alone).
- Reconciliation invariant: on_target + near_miss + off_target + other = total shots.
- Box follows the header carousel team — NO per-box team dropdown.
- Data caches go in `assets/data/` (gitignored).
- TDD: failing test first, then implement. Run tests with `python -m pytest`.
- Env: conda base (or `wc2026-live`); the app runs offline with no API key (`LIVE is None`), so all unit tests must pass without network.
- All work stays on local `main`; never push. Commit messages end with the Co-Authored-By trailer (see below).

**Commit trailer (every commit):**
```
Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
```

---

## File Structure

| File | Responsibility |
|------|----------------|
| `src/data/live/goal_mouth_zones.py` (create) | Pure domain constants + helpers: `ON_TARGET`, `MARGINS`, `ZONE_MAP`, `classify_target`, `parse_shot_minute`. |
| `src/data/live/shots.py` (create) | `ShotRecord` dataclass + `parse_shots(match_id, detail)` reading match-detail `homeTeam.shots[]`/`awayTeam.shots[]`. |
| `src/data/live/goal_mouth.py` (create) | `aggregate_goal_mouth(records, group_only=False)` — the pure aggregation used by the service AND the probe. |
| `src/data/live/shots_store.py` (create) | Gitignored CSV persistence: `load` / `stored_match_states` / `upsert`. |
| `src/data/live/service.py` (modify) | `shots_store` ctor param; `update_shot_stats`; `team_goal_mouth`. |
| `src/components/goal_mouth.py` (create) | UI: color constants, geometry, pure builders (`cell_fill_colors`, `zone_hover_text`, `build_goal_mouth_figure`, `drawer_body`) + `build_goal_mouth_panel`, `build_goal_mouth_drawer`. |
| `src/components/layout.py` (modify) | Mount the panel, drawer, and `dcc.Store`. |
| `assets/styles.css` (modify) | Narrow group table to 1 col; add `goalmouth` grid area + mobile rule. |
| `app.py` (modify) | `SHOTS_STORE_PATH`, ctor wiring, `update_shot_stats` in backfill+feed, three callbacks + thin payload helpers. |
| `scratchpad/probe_shots.py` (modify) | Emit zone×outcome and zone×shooter cross-tabs (verification only). |
| `tests/test_goal_mouth_zones.py`, `tests/test_shots.py`, `tests/test_goal_mouth_agg.py`, `tests/test_shots_store.py`, `tests/test_service_shots.py`, `tests/test_goal_mouth_component.py`, `tests/test_layout_goal_mouth.py`, `tests/test_app.py` (modify) | Tests per task. |

---

## Task 1: Zone model & time parsing (`goal_mouth_zones.py`)

**Files:**
- Create: `src/data/live/goal_mouth_zones.py`
- Test: `tests/test_goal_mouth_zones.py`

**Interfaces:**
- Produces:
  - `ON_TARGET: list[str]` = `["high_left","high_centre","high_right","low_left","low_centre","low_right"]`
  - `MARGINS: list[str]` = `["close_high","close_left","close_right","close_right_high"]`
  - `ZONE_MAP: dict[str, str]`
  - `classify_target(goal_target: str | None) -> str` — returns a region id, `"off_target"`, or `"other"`.
  - `parse_shot_minute(time_str: str | None) -> tuple[int, int]` — `(base, extra)` for sorting.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_goal_mouth_zones.py
from src.data.live.goal_mouth_zones import (
    ON_TARGET, MARGINS, ZONE_MAP, classify_target, parse_shot_minute,
)


def test_all_six_grid_cells_map():
    assert classify_target("High Left") == "high_left"
    assert classify_target("High Centre") == "high_centre"
    assert classify_target("High Right") == "high_right"
    assert classify_target("Low Left") == "low_left"
    assert classify_target("Low Centre") == "low_centre"
    assert classify_target("Low Right") == "low_right"
    assert set(ON_TARGET) == {
        "high_left", "high_centre", "high_right",
        "low_left", "low_centre", "low_right",
    }


def test_near_miss_margins_including_quirks():
    assert classify_target("Close High") == "close_high"
    assert classify_target("CloseLeft") == "close_left"        # no space
    assert classify_target("Close Right") == "close_right"
    assert classify_target("Close Right And High") == "close_right_high"  # compound
    assert set(MARGINS) == {"close_high", "close_left",
                            "close_right", "close_right_high"}


def test_null_is_off_target():
    assert classify_target(None) == "off_target"


def test_unknown_is_other_never_dropped():
    assert classify_target("Top Bins") == "other"
    assert classify_target("") == "other"


def test_zone_map_has_no_string_split_dependency():
    # The compound value is a single key, not two tokens.
    assert ZONE_MAP["Close Right And High"] == "close_right_high"


def test_parse_shot_minute_orders_stoppage():
    assert parse_shot_minute("15'") == (15, 0)
    assert parse_shot_minute("45+1") == (45, 1)
    assert parse_shot_minute("90+3'") == (90, 3)
    assert parse_shot_minute(None) == (0, 0)
    assert parse_shot_minute("45'") < parse_shot_minute("45+1")
    assert parse_shot_minute("45+1") < parse_shot_minute("46'")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_goal_mouth_zones.py -v`
Expected: FAIL with `ModuleNotFoundError: src.data.live.goal_mouth_zones`.

- [ ] **Step 3: Write minimal implementation**

```python
# src/data/live/goal_mouth_zones.py
"""Pure domain model for the goal-mouth map: the explicit goalTarget→region
lookup and a sortable minute parser. No I/O, no Plotly, no Dash."""
from __future__ import annotations

# On-target grid is 2x3: rows {High, Low} x cols {Left, Centre, Right}.
ON_TARGET = ["high_left", "high_centre", "high_right",
             "low_left", "low_centre", "low_right"]

# Near-miss margins outside the frame (only these four ever occur).
MARGINS = ["close_high", "close_left", "close_right", "close_right_high"]

# The ONLY place goalTarget strings are interpreted. Never string-split — the
# compound "Close Right And High" and the space-less "CloseLeft" are explicit keys.
ZONE_MAP = {
    "High Left": "high_left", "High Centre": "high_centre", "High Right": "high_right",
    "Low Left": "low_left", "Low Centre": "low_centre", "Low Right": "low_right",
    "Close High": "close_high", "CloseLeft": "close_left",
    "Close Right": "close_right", "Close Right And High": "close_right_high",
}


def classify_target(goal_target: str | None) -> str:
    """None -> 'off_target'; a known string -> its region id; anything else ->
    'other' (a visible bucket, never silently dropped)."""
    if goal_target is None:
        return "off_target"
    return ZONE_MAP.get(goal_target, "other")


def parse_shot_minute(time_str: str | None) -> tuple[int, int]:
    """'15'' -> (15, 0); '45+1' -> (45, 1). Returns (base, extra) so stoppage
    time sorts after its base minute. Defensive: bad input -> (0, 0)."""
    if not time_str:
        return (0, 0)
    s = time_str.strip().rstrip("'").strip()
    base, _, extra = s.partition("+")
    try:
        return (int(base or 0), int(extra or 0))
    except ValueError:
        return (0, 0)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_goal_mouth_zones.py -v`
Expected: PASS (6 tests).

- [ ] **Step 5: Commit**

```bash
git add src/data/live/goal_mouth_zones.py tests/test_goal_mouth_zones.py
git commit -m "feat: goal-mouth zone model + minute parser

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: Shot parsing (`shots.py`)

**Files:**
- Create: `src/data/live/shots.py`
- Test: `tests/test_shots.py`

**Interfaces:**
- Produces:
  - `ShotRecord` dataclass: `match_id:int, team:str, player:str, time:str, outcome:str, goal_target:str|None, stage:str="group"`.
  - `parse_shots(match_id: int, detail) -> list[ShotRecord]` — `detail` is the raw match-detail (a 1-element list OR a dict) carrying `homeTeam`/`awayTeam`, each with `name` and `shots[]`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_shots.py
from src.data.live.shots import ShotRecord, parse_shots


def _detail():
    return {
        "homeTeam": {"name": "England", "shots": [
            {"playerName": "K. Bowie", "time": "15'", "outcome": "Blocked",
             "goalTarget": "Low Centre"},
            {"playerName": "M. Olise", "time": "45+1", "outcome": "Missed",
             "goalTarget": None},
        ]},
        "awayTeam": {"name": "Wales", "shots": [
            {"playerName": "D. James", "time": "70'", "outcome": "Saved",
             "goalTarget": "High Right"},
        ]},
    }


def test_parses_both_sides_with_team_names():
    rows = parse_shots(42, _detail())
    assert len(rows) == 3
    eng = [r for r in rows if r.team == "England"]
    assert len(eng) == 2
    assert rows[0] == ShotRecord(42, "England", "K. Bowie", "15'",
                                 "Blocked", "Low Centre")
    assert any(r.goal_target is None and r.team == "England" for r in rows)


def test_accepts_one_element_list_detail():
    rows = parse_shots(7, [_detail()])
    assert len(rows) == 3


def test_skips_malformed_shots_and_missing_sides():
    detail = {"homeTeam": {"name": "X", "shots": ["junk", None,
              {"playerName": "P", "time": "5'", "outcome": "Goal",
               "goalTarget": "Low Left"}]}}
    rows = parse_shots(1, detail)
    assert len(rows) == 1
    assert rows[0].outcome == "Goal"


def test_empty_or_bad_detail_returns_empty():
    assert parse_shots(1, None) == []
    assert parse_shots(1, []) == []
    assert parse_shots(1, {"homeTeam": {}, "awayTeam": {}}) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_shots.py -v`
Expected: FAIL with `ModuleNotFoundError: src.data.live.shots`.

- [ ] **Step 3: Write minimal implementation**

```python
# src/data/live/shots.py
"""Parse per-shot rows from the Highlightly match-detail endpoint
(homeTeam.shots[]/awayTeam.shots[]). Stage is assigned later at store-write
time (mirrors team_match_stats), so ShotRecord defaults stage='group'."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ShotRecord:
    match_id: int
    team: str
    player: str
    time: str
    outcome: str
    goal_target: str | None
    stage: str = "group"


def _detail_obj(detail):
    if isinstance(detail, list):
        return detail[0] if detail else None
    return detail if isinstance(detail, dict) else None


def parse_shots(match_id: int, detail) -> list[ShotRecord]:
    obj = _detail_obj(detail)
    if not isinstance(obj, dict):
        return []
    rows: list[ShotRecord] = []
    for side in ("homeTeam", "awayTeam"):
        team_obj = obj.get(side)
        if not isinstance(team_obj, dict):
            continue
        team = str(team_obj.get("name") or "")
        shots = team_obj.get("shots")
        if not isinstance(shots, list):
            continue
        for shot in shots:
            if not isinstance(shot, dict):
                continue
            gt = shot.get("goalTarget")
            rows.append(ShotRecord(
                match_id=match_id,
                team=team,
                player=str(shot.get("playerName") or ""),
                time=str(shot.get("time") or ""),
                outcome=str(shot.get("outcome") or ""),
                goal_target=gt if gt is None else str(gt),
            ))
    return rows
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_shots.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add src/data/live/shots.py tests/test_shots.py
git commit -m "feat: parse per-shot rows from match detail

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: Aggregation (`goal_mouth.py`)

**Files:**
- Create: `src/data/live/goal_mouth.py`
- Test: `tests/test_goal_mouth_agg.py`

**Interfaces:**
- Consumes: `ShotRecord` (Task 2); `ON_TARGET`, `classify_target`, `parse_shot_minute` (Task 1).
- Produces: `aggregate_goal_mouth(records: list[ShotRecord], group_only: bool = False) -> dict` with shape:
  ```python
  {"zones": {zone_id: {"count": int, "outcomes": {outcome: int},
                       "shooters": [{"time","player","outcome"}, ...]}},
   "off_target": {"count": int, "outcomes": {outcome: int}},
   "other":      {"count": int, "outcomes": {outcome: int}},
   "totals": {"on_target","near_miss","woodwork","off_target","other","total"}}
  ```
  All six grid cells always present; margins present only when count > 0; shooters sorted by `parse_shot_minute` ascending.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_goal_mouth_agg.py
from src.data.live.shots import ShotRecord
from src.data.live.goal_mouth import aggregate_goal_mouth


def _r(target, outcome="Saved", time="10'", player="P", stage="group"):
    return ShotRecord(1, "England", player, time, outcome, target, stage)


def test_empty_gives_valid_empty_structure():
    agg = aggregate_goal_mouth([])
    assert set(agg["zones"]) == {"high_left", "high_centre", "high_right",
                                 "low_left", "low_centre", "low_right"}
    assert all(z["count"] == 0 for z in agg["zones"].values())
    assert agg["totals"]["total"] == 0
    assert agg["off_target"]["count"] == 0


def test_counts_and_outcome_breakdown():
    recs = [_r("Low Centre", "Goal"), _r("Low Centre", "Saved"),
            _r("Low Centre", "Blocked")]
    agg = aggregate_goal_mouth(recs)
    lc = agg["zones"]["low_centre"]
    assert lc["count"] == 3
    assert lc["outcomes"] == {"Goal": 1, "Saved": 1, "Blocked": 1}


def test_margins_present_only_when_data():
    agg = aggregate_goal_mouth([_r("CloseLeft", "Missed")])
    assert "close_left" in agg["zones"]
    assert "close_high" not in agg["zones"]          # no empty margin
    assert agg["totals"]["near_miss"] == 1


def test_null_to_off_target_unknown_to_other():
    agg = aggregate_goal_mouth([_r(None, "Missed"), _r("Top Bins", "Saved")])
    assert agg["off_target"]["count"] == 1
    assert agg["other"]["count"] == 1


def test_woodwork_counts_post_outcomes():
    agg = aggregate_goal_mouth([_r("Low Left", "Post"), _r(None, "Post")])
    assert agg["totals"]["woodwork"] == 2


def test_reconciliation_invariant():
    recs = [_r("Low Centre", "Goal"), _r("CloseLeft", "Missed"),
            _r(None, "Missed"), _r("Top Bins", "Saved"), _r("High Right", "Saved")]
    t = aggregate_goal_mouth(recs)["totals"]
    assert t["on_target"] + t["near_miss"] + t["off_target"] + t["other"] == t["total"]


def test_group_only_filters_knockout():
    recs = [_r("Low Centre", stage="group"), _r("Low Centre", stage="knockout")]
    assert aggregate_goal_mouth(recs, group_only=False)["totals"]["total"] == 2
    assert aggregate_goal_mouth(recs, group_only=True)["totals"]["total"] == 1


def test_shooters_sorted_by_minute():
    recs = [_r("Low Centre", time="45+1", player="B"),
            _r("Low Centre", time="45'", player="A"),
            _r("Low Centre", time="46'", player="C")]
    names = [s["player"] for s in aggregate_goal_mouth(recs)["zones"]["low_centre"]["shooters"]]
    assert names == ["A", "B", "C"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_goal_mouth_agg.py -v`
Expected: FAIL with `ModuleNotFoundError: src.data.live.goal_mouth`.

- [ ] **Step 3: Write minimal implementation**

```python
# src/data/live/goal_mouth.py
"""Pure per-team aggregation of shot records into the goal-mouth structure.
Shared by LiveDataService.team_goal_mouth and the probe script."""
from __future__ import annotations

from src.data.live.goal_mouth_zones import (
    ON_TARGET, classify_target, parse_shot_minute,
)


def _bump(bucket: dict, outcome: str) -> None:
    bucket["count"] += 1
    bucket["outcomes"][outcome] = bucket["outcomes"].get(outcome, 0) + 1


def aggregate_goal_mouth(records, group_only: bool = False) -> dict:
    recs = [r for r in records
            if not (group_only and getattr(r, "stage", "group") != "group")]

    zones = {z: {"count": 0, "outcomes": {}, "shooters": []} for z in ON_TARGET}
    margins: dict[str, dict] = {}
    off = {"count": 0, "outcomes": {}}
    other = {"count": 0, "outcomes": {}}
    woodwork = 0

    for r in recs:
        if r.outcome == "Post":
            woodwork += 1
        region = classify_target(r.goal_target)
        if region == "off_target":
            _bump(off, r.outcome)
            continue
        if region == "other":
            _bump(other, r.outcome)
            continue
        if region in zones:
            bucket = zones[region]
        else:  # a near-miss margin — created on first occurrence only
            bucket = margins.setdefault(region,
                                        {"count": 0, "outcomes": {}, "shooters": []})
        _bump(bucket, r.outcome)
        bucket["shooters"].append(
            {"time": r.time, "player": r.player, "outcome": r.outcome})

    for bucket in list(zones.values()) + list(margins.values()):
        bucket["shooters"].sort(key=lambda s: parse_shot_minute(s["time"]))

    on_target = sum(zones[z]["count"] for z in ON_TARGET)
    near_miss = sum(m["count"] for m in margins.values())
    return {
        "zones": {**zones, **margins},
        "off_target": off,
        "other": other,
        "totals": {
            "on_target": on_target, "near_miss": near_miss, "woodwork": woodwork,
            "off_target": off["count"], "other": other["count"], "total": len(recs),
        },
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_goal_mouth_agg.py -v`
Expected: PASS (8 tests).

- [ ] **Step 5: Commit**

```bash
git add src/data/live/goal_mouth.py tests/test_goal_mouth_agg.py
git commit -m "feat: aggregate shots into per-team goal-mouth structure

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 4: Shot store (`shots_store.py`)

**Files:**
- Create: `src/data/live/shots_store.py`
- Test: `tests/test_shots_store.py`

**Interfaces:**
- Consumes: `ShotRecord` (Task 2).
- Produces (mirrors `team_stats_store`):
  - `FIELDS = ["match_id","team","state","stage","player","time","outcome","goal_target"]`
  - `load(path) -> dict[int, list[ShotRecord]]`
  - `stored_match_states(path) -> dict[int, str]`
  - `upsert(path, match_id: int, state: str, rows, stage: str = "group") -> None`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_shots_store.py
from src.data.live.shots import ShotRecord
from src.data.live import shots_store


def test_roundtrip_upsert_and_load(tmp_path):
    p = tmp_path / "live_shots.csv"
    rows = [ShotRecord(1, "England", "K. Bowie", "15'", "Blocked", "Low Centre"),
            ShotRecord(1, "England", "M. Olise", "45+1", "Missed", None)]
    shots_store.upsert(p, 1, "finished", rows, stage="group")
    loaded = shots_store.load(p)
    assert set(loaded) == {1}
    assert len(loaded[1]) == 2
    r0 = loaded[1][0]
    assert r0.team == "England" and r0.goal_target == "Low Centre"
    assert r0.stage == "group"
    # null goal_target round-trips as None, not the string "None"
    assert any(r.goal_target is None for r in loaded[1])


def test_missing_file_is_empty():
    assert shots_store.load("/no/such/file.csv") == {}
    assert shots_store.stored_match_states("/no/such/file.csv") == {}


def test_stored_states_and_replace_by_match(tmp_path):
    p = tmp_path / "live_shots.csv"
    shots_store.upsert(p, 1, "live",
                       [ShotRecord(1, "A", "P", "5'", "Saved", "Low Left")])
    shots_store.upsert(p, 2, "finished",
                       [ShotRecord(2, "B", "Q", "9'", "Goal", "Low Right")], "knockout")
    assert shots_store.stored_match_states(p) == {1: "live", 2: "finished"}
    # re-upsert match 1 replaces only its rows, leaves match 2 intact
    shots_store.upsert(p, 1, "finished",
                       [ShotRecord(1, "A", "P", "5'", "Goal", "High Left")])
    loaded = shots_store.load(p)
    assert len(loaded[1]) == 1 and loaded[1][0].outcome == "Goal"
    assert loaded[2][0].stage == "knockout"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_shots_store.py -v`
Expected: FAIL with `ModuleNotFoundError: src.data.live.shots_store`.

- [ ] **Step 3: Write minimal implementation**

```python
# src/data/live/shots_store.py
"""Gitignored per-match shot cache (mirrors team_stats_store). `state` records
the match state at write time so the updater can skip finished-and-stored
matches; `stage` tags group vs knockout for the group-only filter."""
from __future__ import annotations

import csv
import os
from pathlib import Path

from src.data.live.shots import ShotRecord

FIELDS = ["match_id", "team", "state", "stage",
          "player", "time", "outcome", "goal_target"]


def load(path) -> dict[int, list[ShotRecord]]:
    p = Path(path)
    if not p.exists():
        return {}
    out: dict[int, list[ShotRecord]] = {}
    with p.open(newline="") as f:
        for row in csv.DictReader(f):
            mid = int(row["match_id"])
            gt = row.get("goal_target")
            out.setdefault(mid, []).append(ShotRecord(
                match_id=mid, team=row["team"], player=row.get("player", ""),
                time=row.get("time", ""), outcome=row.get("outcome", ""),
                goal_target=(gt if gt else None),
                stage=row.get("stage") or "group"))
    return out


def stored_match_states(path) -> dict[int, str]:
    p = Path(path)
    if not p.exists():
        return {}
    out: dict[int, str] = {}
    with p.open(newline="") as f:
        for row in csv.DictReader(f):
            out[int(row["match_id"])] = row["state"]
    return out


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
                "match_id": s.match_id, "team": s.team, "state": state,
                "stage": stage, "player": s.player, "time": s.time,
                "outcome": s.outcome,
                "goal_target": "" if s.goal_target is None else s.goal_target,
            })
    os.replace(tmp, p)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_shots_store.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Gitignore the cache path**

`.gitignore` lists the live CSVs explicitly (no wildcard), so the new cache is NOT yet ignored. Add a line after `assets/data/live_team_stats.csv` (line 12):
```
assets/data/live_shots.csv
```
Verify: `git check-ignore assets/data/live_shots.csv`
Expected: prints `assets/data/live_shots.csv`. Include `.gitignore` in this task's commit.

- [ ] **Step 6: Commit**

```bash
git add src/data/live/shots_store.py tests/test_shots_store.py .gitignore
git commit -m "feat: gitignored per-match shot store

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 5: Service integration (`service.py`)

**Files:**
- Modify: `src/data/live/service.py` (constructor ~34-42; add methods near `update_team_stats` ~191-215 and near `team_leaders` ~217)
- Test: `tests/test_service_shots.py`

**Interfaces:**
- Consumes: `parse_shots` (Task 2), `aggregate_goal_mouth` (Task 3), `shots_store` (Task 4), existing `classify_stage`, `canonical_team`, `models.MatchState`.
- Produces:
  - `LiveDataService(..., shots_store=None)` — stored as `self._shots_store = Path(shots_store) if shots_store else None`.
  - `update_shot_stats(self, matches, now: float) -> None` (mirrors `update_team_stats`, fetches `self._client.match(mid)`).
  - `team_goal_mouth(self, team: str, group_only: bool = False) -> dict` — empty store / no store → `aggregate_goal_mouth([])`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_service_shots.py
from src.data.live.service import LiveDataService
from src.data.live import models


class _Client:
    """Returns one match-detail object; records which match ids were fetched."""
    def __init__(self):
        self.fetched = []
        self.requests_remaining = 100

    def match(self, match_id):
        self.fetched.append(match_id)
        return [{
            "homeTeam": {"name": "England", "shots": [
                {"playerName": "A", "time": "10'", "outcome": "Goal",
                 "goalTarget": "Low Centre"},
                {"playerName": "B", "time": "20'", "outcome": "Missed",
                 "goalTarget": None}]},
            "awayTeam": {"name": "Wales", "shots": [
                {"playerName": "C", "time": "30'", "outcome": "Saved",
                 "goalTarget": "High Right"}]},
        }]


def _svc(tmp_path):
    return LiveDataService(_Client(), stadium_index={},
                           shots_store=tmp_path / "live_shots.csv")


def test_update_then_aggregate_for_team(tmp_path):
    svc = _svc(tmp_path)
    matches = [{"match_id": 5, "state": models.MatchState.FINISHED.value,
                "kickoff": "2026-06-15T18:00:00+00:00"}]
    svc.update_shot_stats(matches, now=1.0)
    agg = svc.team_goal_mouth("England")
    assert agg["zones"]["low_centre"]["count"] == 1
    assert agg["off_target"]["count"] == 1
    assert agg["totals"]["total"] == 2          # England's two shots only


def test_finished_and_stored_is_skipped(tmp_path):
    svc = _svc(tmp_path)
    matches = [{"match_id": 5, "state": models.MatchState.FINISHED.value,
                "kickoff": "2026-06-15T18:00:00+00:00"}]
    svc.update_shot_stats(matches, now=1.0)
    svc.update_shot_stats(matches, now=2.0)     # already finished+stored
    assert svc._client.fetched == [5]           # fetched once, not twice


def test_no_store_returns_empty_structure():
    svc = LiveDataService(_Client(), stadium_index={})   # shots_store=None
    agg = svc.team_goal_mouth("England")
    assert agg["totals"]["total"] == 0
    assert set(agg["zones"]) >= {"low_centre", "high_left"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_service_shots.py -v`
Expected: FAIL (`TypeError: ... unexpected keyword argument 'shots_store'` or `AttributeError: ... 'update_shot_stats'`).

- [ ] **Step 3: Write minimal implementation**

In `src/data/live/service.py`, extend the imports near the top (the existing import line is `from src.data.live import models, player_store` and `from src.data.live import team_stats_store`):

```python
from src.data.live import models, player_store, shots_store
from src.data.live import team_stats_store
from src.data.live.shots import parse_shots
from src.data.live.goal_mouth import aggregate_goal_mouth
```

In `__init__`, add the parameter and the stored path (place beside `self._team_store`):

```python
    def __init__(self, client, stadium_index, league_id=LEAGUE_ID, season=SEASON,
                 player_store=None, team_store=None, knockout_start=None,
                 shots_store=None):
        ...
        self._team_store = Path(team_store) if team_store else None
        self._shots_store = Path(shots_store) if shots_store else None
```

Add the two methods after `update_team_stats` (and before `team_leaders`):

```python
    def update_shot_stats(self, matches, now: float) -> None:
        """Refresh the shot cache from today's matches (mirrors
        update_team_stats). Finished & already stored -> skip; finished-new or
        live -> fetch /matches/{id} detail once and overwrite that match's rows.
        Each match is independent: a failure is logged and skipped."""
        if self._shots_store is None:
            return
        stored = shots_store.stored_match_states(self._shots_store)
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
                rows = parse_shots(mid, self._client.match(mid))
                stage = classify_stage(m.get("kickoff"), self._knockout_start)
                shots_store.upsert(self._shots_store, mid, state, rows, stage)
            except Exception:
                logger.exception("shot stats update failed for match %s", mid)

    def team_goal_mouth(self, team: str, group_only: bool = False) -> dict:
        """Aggregate goal-mouth structure for `team` across stored matches.
        No store / no shots -> a valid empty structure."""
        if self._shots_store is None:
            return aggregate_goal_mouth([])
        by_match = shots_store.load(self._shots_store)
        target = canonical_team(team)
        records = [r for rows in by_match.values() for r in rows
                   if canonical_team(r.team) == target]
        return aggregate_goal_mouth(records, group_only=group_only)
```

(`classify_stage` and `canonical_team` are already imported in service.py from `src.data.live.reconcile` — confirm the existing import line includes them; it does.)

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_service_shots.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Run the existing service tests to confirm no regression**

Run: `python -m pytest tests/ -k "service or live" -q`
Expected: PASS (no regressions from the new ctor param / imports).

- [ ] **Step 6: Commit**

```bash
git add src/data/live/service.py tests/test_service_shots.py
git commit -m "feat: LiveDataService shot fetch + per-team goal-mouth aggregation

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 6: Component pure builders (`goal_mouth.py` figure/hover/colors/drawer body)

**Files:**
- Create: `src/components/goal_mouth.py`
- Test: `tests/test_goal_mouth_component.py`

**Interfaces:**
- Consumes: `ON_TARGET`, `MARGINS`, `parse_shot_minute` (Task 1); the aggregate dict shape (Task 3).
- Produces:
  - `OUTCOME_COLORS: dict[str,str]`, `NEAR_MISS_COLOR: str`, `VOLUME_HUE: str`.
  - `ZONE_LABEL: dict[str,str]` (region id → human label, e.g. `"low_centre"`→`"Low Centre"`).
  - `cell_fill_colors(agg: dict, mode: str, theme: str = "dark") -> dict[str,str]` — region id → rgba fill. `mode` ∈ {`"volume"`,`"dominant"`}.
  - `zone_hover_text(zone_id: str, zinfo: dict) -> str` — multi-line summary + "click to see all {n}" when count > 6.
  - `build_goal_mouth_figure(agg: dict, mode: str = "volume", theme: str = "dark") -> go.Figure`.
  - `drawer_body(zone_id: str, agg: dict) -> list` — DMC components: header summary + scrollable shot list.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_goal_mouth_component.py
import plotly.graph_objects as go
import dash_mantine_components as dmc

from src.data.live.shots import ShotRecord
from src.data.live.goal_mouth import aggregate_goal_mouth
from src.components.goal_mouth import (
    OUTCOME_COLORS, ZONE_LABEL, cell_fill_colors, zone_hover_text,
    build_goal_mouth_figure, drawer_body,
)


def _agg():
    recs = [ShotRecord(1, "X", "A", "10'", "Goal", "Low Centre"),
            ShotRecord(1, "X", "B", "20'", "Saved", "Low Centre"),
            ShotRecord(1, "X", "C", "30'", "Missed", "CloseLeft"),
            ShotRecord(1, "X", "D", "40'", "Missed", None)]
    return aggregate_goal_mouth(recs)


def test_outcome_colors_enum():
    assert OUTCOME_COLORS["Goal"] == "#1D9E75"
    assert OUTCOME_COLORS["Saved"] == "#378ADD"
    assert OUTCOME_COLORS["Blocked"] == "#888780"
    assert OUTCOME_COLORS["Post"] == "#D85A30"


def test_dominant_mode_colors_cell_by_top_outcome():
    colors = cell_fill_colors(_agg(), mode="dominant")
    # low_centre has Goal+Saved (tie broken deterministically); a non-empty cell
    # gets a color, an empty cell stays faint/transparent-ish.
    assert colors["low_centre"] != colors["high_left"]


def test_volume_mode_single_hue_varies_by_count():
    colors = cell_fill_colors(_agg(), mode="volume")
    assert colors["low_centre"] != colors["high_right"]   # count 2 vs 0


def test_hover_text_has_breakdown_and_click_prompt():
    agg = aggregate_goal_mouth(
        [ShotRecord(1, "X", "P", "5'", "Saved", "Low Centre")] * 7)
    txt = zone_hover_text("low_centre", agg["zones"]["low_centre"])
    assert "Low Centre" in txt
    assert "7" in txt
    assert "click to see all 7" in txt


def test_hover_text_no_click_prompt_when_few():
    agg = _agg()
    txt = zone_hover_text("low_centre", agg["zones"]["low_centre"])  # 2 shots
    assert "click to see all" not in txt


def test_figure_has_six_grid_traces_plus_present_margins():
    fig = build_goal_mouth_figure(_agg())
    assert isinstance(fig, go.Figure)
    zids = [t.customdata[0] for t in fig.data if t.customdata is not None]
    assert set(z for z in zids if z in ZONE_LABEL) >= set(
        ["high_left", "high_centre", "high_right",
         "low_left", "low_centre", "low_right", "close_left"])
    assert "close_high" not in zids                # absent margin not drawn


def test_empty_figure_still_has_six_grid_cells():
    fig = build_goal_mouth_figure(aggregate_goal_mouth([]))
    zids = [t.customdata[0] for t in fig.data if t.customdata is not None]
    assert sum(z in ("high_left", "high_centre", "high_right",
                     "low_left", "low_centre", "low_right") for z in zids) == 6


def test_drawer_body_lists_shots_sorted_with_color():
    agg = aggregate_goal_mouth([
        ShotRecord(1, "X", "Late", "80'", "Goal", "Low Centre"),
        ShotRecord(1, "X", "Early", "10'", "Saved", "Low Centre")])
    body = drawer_body("low_centre", agg)
    assert isinstance(body, list) and body
    # flatten text content to confirm order + presence
    import json
    blob = json.dumps([c.to_plotly_json() for c in body])
    assert blob.index("Early") < blob.index("Late")
    assert "Low Centre" in blob
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_goal_mouth_component.py -v`
Expected: FAIL with `ModuleNotFoundError: src.components.goal_mouth`.

- [ ] **Step 3: Write minimal implementation**

```python
# src/components/goal_mouth.py
"""Goal-mouth map UI: pure figure/hover/color/drawer-body builders plus the
panel and left-drawer constructors. Plotly + dash-mantine-components only."""
from __future__ import annotations

import dash_mantine_components as dmc
import plotly.graph_objects as go
from dash import dcc

from src.data.live.goal_mouth_zones import ON_TARGET, parse_shot_minute

# --- color enum (consistent everywhere; pair with text labels, never alone) ---
OUTCOME_COLORS = {
    "Goal": "#1D9E75", "Saved": "#378ADD", "Blocked": "#888780",
    "Post": "#D85A30", "Missed": "#EF9F27",
}
NEAR_MISS_COLOR = "#EF9F27"          # the Close* family
VOLUME_HUE = "#534AB7"               # neutral single hue for volume mode
# Deterministic dominant-outcome tie-break order.
_DOMINANT_ORDER = ["Goal", "Saved", "Blocked", "Post", "Missed"]

ZONE_LABEL = {
    "high_left": "High Left", "high_centre": "High Centre", "high_right": "High Right",
    "low_left": "Low Left", "low_centre": "Low Centre", "low_right": "Low Right",
    "close_high": "Close High", "close_left": "Close Left",
    "close_right": "Close Right", "close_right_high": "Close Right & High",
}

# Rectangle geometry: (x0, y0, x1, y1). Inside the posts x∈[0,3], y∈[0,2];
# rows High (top, y 1-2) / Low (bottom, y 0-1); cols Left/Centre/Right.
ZONE_BOX = {
    "high_left": (0, 1, 1, 2), "high_centre": (1, 1, 2, 2), "high_right": (2, 1, 3, 2),
    "low_left": (0, 0, 1, 1), "low_centre": (1, 0, 2, 1), "low_right": (2, 0, 3, 1),
    "close_high": (0, 2, 3, 2.6), "close_left": (-0.6, 0, 0, 2),
    "close_right": (3, 0, 3.6, 2), "close_right_high": (3, 2, 3.6, 2.6),
}


def _rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{round(alpha, 3)})"


def _dominant_outcome(outcomes: dict) -> str | None:
    if not outcomes:
        return None
    best = max(outcomes.values())
    for o in _DOMINANT_ORDER:                       # deterministic tie-break
        if outcomes.get(o, 0) == best:
            return o
    return next(iter(outcomes))


def cell_fill_colors(agg: dict, mode: str, theme: str = "dark") -> dict[str, str]:
    """region id -> rgba fill. Volume: single hue, opacity by count (margins use
    the near-miss hue). Dominant: grid cells colored by top outcome, margins
    always the near-miss color."""
    zones = agg["zones"]
    max_count = max((z["count"] for z in zones.values()), default=0) or 1
    out: dict[str, str] = {}
    for zid, z in zones.items():
        is_margin = zid not in ON_TARGET
        if z["count"] == 0:
            out[zid] = _rgba(NEAR_MISS_COLOR if is_margin else VOLUME_HUE, 0.05)
            continue
        if mode == "dominant" and not is_margin:
            out[zid] = _rgba(OUTCOME_COLORS.get(_dominant_outcome(z["outcomes"]),
                                                VOLUME_HUE), 0.85)
        else:
            hue = NEAR_MISS_COLOR if is_margin else VOLUME_HUE
            out[zid] = _rgba(hue, 0.15 + 0.85 * (z["count"] / max_count))
    return out


def zone_hover_text(zone_id: str, zinfo: dict) -> str:
    label = ZONE_LABEL.get(zone_id, zone_id)
    n = zinfo["count"]
    if n == 0:
        return f"<b>{label}</b><br>no shots"
    parts = ", ".join(f"{c} {o.lower()}"
                      for o, c in sorted(zinfo["outcomes"].items(),
                                         key=lambda kv: -kv[1]))
    lines = [f"<b>{label}</b> — {n} shots", parts]
    if zinfo.get("shooters"):
        top = zinfo["shooters"][0]
        lines.append(f"top: {top['player']}")
    if n > 6:
        lines.append(f"<i>click to see all {n}</i>")
    return "<br>".join(lines)


def build_goal_mouth_figure(agg: dict, mode: str = "volume",
                            theme: str = "dark") -> go.Figure:
    """A goal frame: filled, hoverable, clickable rectangles per zone (grid +
    present margins), posts/crossbar lines, and a side readout."""
    dark = theme != "light"
    fills = cell_fill_colors(agg, mode, theme)
    line_color = "rgba(255,255,255,0.35)" if dark else "rgba(0,0,0,0.35)"
    fg = "#E9ECEF" if dark else "#1A1B1E"

    fig = go.Figure()
    # Draw grid cells always; margins only when present in agg["zones"].
    order = [z for z in ON_TARGET] + [z for z in agg["zones"] if z not in ON_TARGET]
    for zid in order:
        x0, y0, x1, y1 = ZONE_BOX[zid]
        fig.add_trace(go.Scatter(
            x=[x0, x1, x1, x0, x0], y=[y0, y0, y1, y1, y0],
            fill="toself", fillcolor=fills[zid], mode="lines",
            line=dict(color=line_color, width=1), hoveron="fills",
            hovertemplate=zone_hover_text(zid, agg["zones"][zid]) + "<extra></extra>",
            customdata=[zid] * 5, showlegend=False, name=ZONE_LABEL.get(zid, zid),
        ))

    # Posts + crossbar (the on-target / near-miss divider).
    post = dict(type="line", line=dict(color=fg, width=3), layer="above")
    shapes = [
        {**post, "x0": 0, "y0": 0, "x1": 0, "y1": 2},
        {**post, "x0": 3, "y0": 0, "x1": 3, "y1": 2},
        {**post, "x0": 0, "y0": 2, "x1": 3, "y1": 2},
    ]

    t = agg["totals"]
    readout = (f"On target {t['on_target']}<br>Near miss {t['near_miss']}<br>"
               f"Woodwork {t['woodwork']}<br>Off target {t['off_target']}<br>"
               f"<b>Total {t['total']}</b>")
    annotations = [dict(
        xref="paper", yref="paper", x=1.0, y=1.0, xanchor="right", yanchor="top",
        align="right", showarrow=False, font=dict(color=fg, size=11), text=readout)]

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=8, r=8, t=8, b=8), showlegend=False, autosize=True,
        shapes=shapes, annotations=annotations,
        hoverlabel=dict(bgcolor="#23262B" if dark else "#FFFFFF", font_color=fg),
        xaxis=dict(visible=False, range=[-0.9, 5.4], fixedrange=True),
        yaxis=dict(visible=False, range=[-0.3, 2.8], fixedrange=True,
                   scaleanchor="x", scaleratio=1),
    )
    return fig


def drawer_body(zone_id: str, agg: dict) -> list:
    """Self-contained left-drawer contents for one zone: summary header + a
    scrollable, time-sorted shot list (minute · shooter · outcome)."""
    z = agg["zones"].get(zone_id, {"count": 0, "outcomes": {}, "shooters": []})
    label = ZONE_LABEL.get(zone_id, zone_id)
    breakdown = ", ".join(f"{c} {o}" for o, c in
                          sorted(z["outcomes"].items(), key=lambda kv: -kv[1]))
    header = dmc.Stack([
        dmc.Text(label, fw=700, size="lg"),
        dmc.Text(f"{z['count']} shots — {breakdown}" if z["count"] else "No shots",
                 size="sm", c="dimmed"),
    ], gap=2)

    rows = [
        dmc.Group([
            dmc.Text(s["time"], size="sm", w=52, c="dimmed"),
            dmc.Text(s["player"], size="sm", style={"flex": 1, "minWidth": 0}),
            dmc.Text(s["outcome"], size="sm", fw=600,
                     c=OUTCOME_COLORS.get(s["outcome"], "gray")),
        ], gap="xs", wrap="nowrap")
        for s in sorted(z["shooters"], key=lambda s: parse_shot_minute(s["time"]))
    ]
    body = dmc.ScrollArea(dmc.Stack(rows, gap=4), style={"height": "70vh"})
    return [dmc.Stack([header, body], gap="sm")]
```

(Panel + drawer constructors are added in Task 7; this task delivers the pure builders only.)

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_goal_mouth_component.py -v`
Expected: PASS (8 tests).

- [ ] **Step 5: Commit**

```bash
git add src/components/goal_mouth.py tests/test_goal_mouth_component.py
git commit -m "feat: goal-mouth figure, hover, color and drawer-body builders

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 7: Panel + drawer constructors (`goal_mouth.py`)

**Files:**
- Modify: `src/components/goal_mouth.py` (append constructors)
- Test: `tests/test_goal_mouth_component.py` (append)

**Interfaces:**
- Consumes: the builders from Task 6.
- Produces:
  - `build_goal_mouth_panel() -> dmc.Box` — card with `.bento-card__header` (title "Goal-mouth map", subtitle, a `SegmentedControl#goal-mouth-mode` with `["Volume","Dominant"]` default `"Volume"`), a `dcc.Graph#goal-mouth-graph`, and a one-line caption + honest-limitation note.
  - `build_goal_mouth_drawer() -> dmc.Drawer` — left drawer `id="goal-mouth-drawer"`.

**Before coding:** confirm the current `dmc.SegmentedControl`, `dmc.Drawer`, `dmc.Box`, `dmc.Text`, `dmc.Group` APIs via context7 MCP (`resolve-library-id` → `dash-mantine-components`, then `query-docs`). The repo pins DMC 2.x; props used here (`data`, `value`, `size`, `fullWidth`, `position`, `opened`, `withCloseButton`, `zIndex`, `classNames`) match the existing `build_tournament_drawer`/`build_leaders_card`.

- [ ] **Step 1: Write the failing test (append)**

```python
# tests/test_goal_mouth_component.py  (append)
import dash_ag_grid as dag  # noqa: F401  (not used; keep imports tidy if linted)
from dash import dcc
from src.components.goal_mouth import (
    build_goal_mouth_panel, build_goal_mouth_drawer,
)


def _walk(node):
    yield node
    children = getattr(node, "children", None)
    if isinstance(children, (list, tuple)):
        for c in children:
            yield from _walk(c)
    elif children is not None:
        yield from _walk(children)


def test_panel_has_header_title_mode_control_and_graph():
    panel = build_goal_mouth_panel()
    ids = {getattr(n, "id", None) for n in _walk(panel)}
    assert "goal-mouth-graph" in ids
    assert "goal-mouth-mode" in ids
    texts = [n.children for n in _walk(panel) if isinstance(n, dmc.Text)]
    assert any("Goal-mouth map" == t for t in texts)
    # never call it a "shot map"
    assert not any(isinstance(t, str) and "shot map" in t.lower() for t in texts)
    # honest-limitation note present
    assert any(isinstance(t, str) and "placement" in t.lower() for t in texts)
    graph = next(n for n in _walk(panel) if isinstance(n, dcc.Graph))
    assert graph.config.get("displayModeBar") is False


def test_drawer_is_left_positioned():
    drawer = build_goal_mouth_drawer()
    assert isinstance(drawer, dmc.Drawer)
    assert drawer.id == "goal-mouth-drawer"
    assert drawer.position == "left"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_goal_mouth_component.py -k "panel or drawer_is_left" -v`
Expected: FAIL (`cannot import name 'build_goal_mouth_panel'`).

- [ ] **Step 3: Write minimal implementation (append to `src/components/goal_mouth.py`)**

```python
_GRAPH_CONFIG = {"displayModeBar": False, "responsive": True}


def build_goal_mouth_panel() -> dmc.Box:
    """Goal-mouth map card: header (title + subtitle + fill-mode control) over a
    Plotly graph, with a caption and the honest-limitation note."""
    header = dmc.Group(
        [
            dmc.Stack([
                dmc.Text("Goal-mouth map", fw=700, size="sm"),
                dmc.Text("where each team's shots finished", size="xs", c="dimmed"),
            ], gap=0),
            dmc.SegmentedControl(id="goal-mouth-mode", value="Volume",
                                 data=["Volume", "Dominant"], size="xs"),
        ],
        justify="space-between", align="center", wrap="nowrap",
        className="bento-card__header",
    )
    graph = dcc.Graph(id="goal-mouth-graph", figure=build_goal_mouth_figure(
        {"zones": {z: {"count": 0, "outcomes": {}, "shooters": []}
                   for z in ON_TARGET},
         "off_target": {"count": 0, "outcomes": {}},
         "other": {"count": 0, "outcomes": {}},
         "totals": {"on_target": 0, "near_miss": 0, "woodwork": 0,
                    "off_target": 0, "other": 0, "total": 0}}),
        config=_GRAPH_CONFIG, style={"width": "100%", "flex": "1 1 auto",
                                     "minHeight": 0})
    caption = dmc.Stack([
        dmc.Text("inside the posts = on target · outer band = near miss",
                 size="xs", c="dimmed"),
        dmc.Text("placement map (where shots finished), not pitch coordinates — "
                 "the API gives goal-target zones, not x/y.",
                 size="xs", c="dimmed"),
    ], gap=0)
    body = dmc.Box([graph, caption], className="goal-mouth-panel__body")
    return dmc.Box([header, body], className="goal-mouth-panel")


def build_goal_mouth_drawer() -> dmc.Drawer:
    """App-level LEFT drawer holding the clicked zone's full shot list."""
    return dmc.Drawer(
        id="goal-mouth-drawer",
        position="left", size="md", padding="md", opened=False,
        withCloseButton=True, zIndex=2500,
        classNames={"content": "filter-drawer-frosted",
                    "header": "filter-drawer-frosted-header"},
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_goal_mouth_component.py -v`
Expected: PASS (all component tests, ~10).

- [ ] **Step 5: Commit**

```bash
git add src/components/goal_mouth.py tests/test_goal_mouth_component.py
git commit -m "feat: goal-mouth panel and left-drawer constructors

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 8: Layout & CSS integration

**Files:**
- Modify: `src/components/layout.py` (imports; `build_layout` params + body; mount drawer + store)
- Modify: `assets/styles.css` (`.main-split--team` grid ~260-289; mobile `@media (max-width:768px)` ~782-820; add panel body rules)
- Test: `tests/test_layout_goal_mouth.py`

**Interfaces:**
- Consumes: `build_goal_mouth_panel`, `build_goal_mouth_drawer` (Task 7).
- Produces: `build_layout(..., goal_mouth_panel=None)` mounting the card (class `bento-card bento-card--goalmouth`), the drawer, and `dcc.Store(id="goal-mouth-zone")`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_layout_goal_mouth.py
import dash_mantine_components as dmc
from dash import dcc

from src.components.layout import build_layout


def _walk(node):
    yield node
    children = getattr(node, "children", None)
    if isinstance(children, (list, tuple)):
        for c in children:
            yield from _walk(c)
    elif children is not None:
        yield from _walk(children)


def _layout():
    return build_layout(venues=[], goal_mouth_panel=dmc.Box(id="gm-stub"))


def test_goal_mouth_card_mounted():
    classes = [getattr(n, "className", "") for n in _walk(_layout())]
    assert any("bento-card--goalmouth" in (c or "") for c in classes)
    # the group table card is still present (narrowed, not removed)
    assert any("bento-card--table" in (c or "") for c in classes)


def test_goal_mouth_drawer_and_store_present():
    ids = {getattr(n, "id", None) for n in _walk(_layout())}
    assert "goal-mouth-drawer" in ids
    assert "goal-mouth-zone" in ids


def test_store_default_is_none():
    store = next(n for n in _walk(_layout())
                if isinstance(n, dcc.Store) and n.id == "goal-mouth-zone")
    assert store.data is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_layout_goal_mouth.py -v`
Expected: FAIL (`build_layout` has no `goal_mouth_panel` param / card not found).

- [ ] **Step 3: Implement layout changes**

In `src/components/layout.py`:

Add the import near the other component imports (after line 11/12):
```python
from src.components.goal_mouth import build_goal_mouth_drawer
```

Add the parameter to `build_layout` (after `leaders_panel=None,`):
```python
    leaders_panel=None,
    goal_mouth_panel=None,
    asset_url=None,
```

Add the card next to the other card wrappers (after `leaders_card = ...`, line ~113):
```python
    goalmouth_card = dmc.Box(goal_mouth_panel,
                             className="bento-card bento-card--goalmouth")
```

Add it to the `main-split` children list (line ~116) — order does not affect the grid (areas place each card), append it:
```python
        dmc.Box(
            [kpi_strip, leaders_card, table_card, formation_card, map_card,
             squad_card, goalmouth_card],
            id="main-split",
            className="main-split",
        )
```

Mount the drawer + store in the `MantineProvider` children (after `build_tournament_drawer(),` ~146 and beside the other `dcc.Store`s ~152):
```python
            build_tournament_drawer(),
            build_goal_mouth_drawer(),
            ...
            dcc.Store(id="carousel-index", data=0, storage_type="local"),
            dcc.Store(id="goal-mouth-zone", data=None),
```

- [ ] **Step 4: Implement CSS changes in `assets/styles.css`**

Replace the `.main-split--team` grid template (the block at ~260-272) with the narrowed group column + new `goalmouth` area:
```css
.main-split--team {
    grid-template-columns: 1.0fr 1.0fr 0.85fr 1.2fr;
    grid-template-rows: auto 1fr 1.3fr;
    grid-template-areas:
        "kpi      kpi        kpi        kpi"
        "table    goalmouth  formation  squad"
        "leaders  map        map        squad";
    gap: 12px;
    padding: 12px;
}
```

Add the grid-area binding alongside the other `.main-split--team .bento-card--*` rules (~283-288):
```css
.main-split--team .bento-card--goalmouth { grid-area: goalmouth; }
```

Add panel body rules near the other `*-panel` blocks (e.g. after `.leaders-panel__body`):
```css
.goal-mouth-panel {
    display: flex;
    flex-direction: column;
    height: 100%;
    overflow: hidden;
}
.goal-mouth-panel__body {
    flex: 1 1 auto;
    min-height: 0;
    display: flex;
    flex-direction: column;
    gap: 6px;
    padding: 10px 14px;
    overflow: hidden;
}
```

In the mobile `@media (max-width: 768px)` block, insert `goalmouth` into the single-column stack right after `table`, and give the card a sensible height:
```css
    .main-split--team {
        grid-template-columns: 1fr;
        grid-template-rows: auto;
        grid-template-areas:
            "kpi"
            "table"
            "goalmouth"
            "formation"
            "map"
            "leaders"
            "squad";
        overflow-y: auto;
    }
    .main-split--team .bento-card--goalmouth {
        height: 44vh;
    }
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests/test_layout_goal_mouth.py -v`
Expected: PASS (3 tests).

- [ ] **Step 6: Commit**

```bash
git add src/components/layout.py assets/styles.css tests/test_layout_goal_mouth.py
git commit -m "feat: mount goal-mouth box (narrow group table) + left drawer + store

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 9: App wiring (callbacks + data path)

**Files:**
- Modify: `app.py` — `SHOTS_STORE_PATH` + ctor wiring (~108-118); `build_layout(...)` call site (pass `goal_mouth_panel`); `_backfill_live_stats` (~1097-1098) and `live_feed` (~1120-1121); three new callbacks + thin payload helpers.
- Test: `tests/test_app.py` (append)

**Interfaces:**
- Consumes: `build_goal_mouth_panel` (Task 7); `LiveDataService.team_goal_mouth`, `update_shot_stats` (Task 5); `build_goal_mouth_figure`, `drawer_body`, `ZONE_LABEL` (Task 6); `center_team`, `TEAM_NAMES` (existing).
- Produces (module-level in `app.py`, testable by monkeypatching `app.LIVE`):
  - `goal_mouth_figure_payload(index, live, dark, mode) -> go.Figure`
  - `goal_mouth_drawer_payload(zone_id, index, live) -> tuple[str, list]` → `(title, children)`

- [ ] **Step 1: Write the failing test (append to `tests/test_app.py`)**

```python
# tests/test_app.py  (append)
import plotly.graph_objects as go


class _FakeGMLive:
    """Stand-in LIVE exposing team_goal_mouth with a fixed aggregate."""
    def __init__(self):
        from src.data.live.shots import ShotRecord
        from src.data.live.goal_mouth import aggregate_goal_mouth
        self._agg = aggregate_goal_mouth([
            ShotRecord(1, "England", "A", "10'", "Goal", "Low Centre"),
            ShotRecord(1, "England", "B", "20'", "Saved", "Low Centre")])
        self.calls = []

    def team_goal_mouth(self, team, group_only=False):
        self.calls.append((team, group_only))
        return self._agg


def test_goal_mouth_figure_payload_builds_figure(monkeypatch):
    import app
    monkeypatch.setattr(app, "LIVE", _FakeGMLive())
    fig = app.goal_mouth_figure_payload(0, {"ok": True}, dark=True, mode="Volume")
    assert isinstance(fig, go.Figure)
    assert app.LIVE.calls and isinstance(app.LIVE.calls[0][0], str)


def test_goal_mouth_figure_payload_no_live_is_empty(monkeypatch):
    import app
    monkeypatch.setattr(app, "LIVE", None)
    fig = app.goal_mouth_figure_payload(0, None, dark=True, mode="Volume")
    assert isinstance(fig, go.Figure)          # empty-but-valid frame


def test_goal_mouth_drawer_payload_lists_zone(monkeypatch):
    import app
    monkeypatch.setattr(app, "LIVE", _FakeGMLive())
    title, children = app.goal_mouth_drawer_payload("low_centre", 0, {"ok": True})
    assert "Low Centre" in title
    assert isinstance(children, list) and children
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_app.py -k goal_mouth -v`
Expected: FAIL (`module 'app' has no attribute 'goal_mouth_figure_payload'`).

- [ ] **Step 3: Implement the data-path wiring**

Add the store path next to the others (~109):
```python
TEAM_STATS_PATH = DATA_DIR / "live_team_stats.csv"
SHOTS_STORE_PATH = DATA_DIR / "live_shots.csv"
```

Pass it to the service (~114-116):
```python
    LiveDataService(HighlightlyClient(api_key=_API_KEY), STADIUM_INDEX,
                    player_store=PLAYER_STORE_PATH, team_store=TEAM_STATS_PATH,
                    knockout_start=KNOCKOUT_START, shots_store=SHOTS_STORE_PATH)
```

Add the updater to `_backfill_live_stats` (after the two existing update calls, ~1098):
```python
        LIVE.update_player_stats(day, now)
        LIVE.update_team_stats(day, now)
        LIVE.update_shot_stats(day, now)
```

Add it to `live_feed` (after the two existing, ~1121):
```python
        await asyncio.to_thread(LIVE.update_team_stats, snap["matches"], now)
        await asyncio.to_thread(LIVE.update_shot_stats, snap["matches"], now)
```

- [ ] **Step 4: Implement panel mount + payload helpers + callbacks**

Add the import with the other component imports near the top of `app.py`:
```python
from src.components.goal_mouth import (
    build_goal_mouth_figure, build_goal_mouth_panel, drawer_body, ZONE_LABEL,
)
```

Pass the panel into the `build_layout(...)` call (find the existing call that passes `leaders_panel=...`; add `goal_mouth_panel=build_goal_mouth_panel()`).

Add the payload helpers (place them near the other `*_payload` helpers, e.g. after `tournament_grid_payload`):
```python
_EMPTY_GM = {
    "zones": {z: {"count": 0, "outcomes": {}, "shooters": []}
              for z in ["high_left", "high_centre", "high_right",
                        "low_left", "low_centre", "low_right"]},
    "off_target": {"count": 0, "outcomes": {}},
    "other": {"count": 0, "outcomes": {}},
    "totals": {"on_target": 0, "near_miss": 0, "woodwork": 0,
               "off_target": 0, "other": 0, "total": 0},
}


def goal_mouth_figure_payload(index, live, dark, mode):
    """Figure for the carousel-selected team. `live` is the trigger only; data
    comes from the shot store via LIVE."""
    if LIVE is None:
        agg = _EMPTY_GM
    else:
        team = center_team(TEAM_NAMES, index or 0)
        agg = LIVE.team_goal_mouth(team)
    theme = "dark" if (dark is None or dark) else "light"
    fig_mode = "dominant" if mode == "Dominant" else "volume"
    return build_goal_mouth_figure(agg, mode=fig_mode, theme=theme)


def goal_mouth_drawer_payload(zone_id, index, live):
    """(title, children) for the zone drawer. Title doubles the zone name."""
    agg = _EMPTY_GM if LIVE is None else LIVE.team_goal_mouth(
        center_team(TEAM_NAMES, index or 0))
    title = ZONE_LABEL.get(zone_id, zone_id)
    return title, drawer_body(zone_id, agg)
```

Add the three callbacks (place near the other per-team callbacks, ~850-927):
```python
@callback(
    Output("goal-mouth-graph", "figure"),
    Input("carousel-index", "data"),
    Input("goal-mouth-mode", "value"),
    Input("color-scheme-toggle", "checked"),
    Input("live-store", "data"),
)
def update_goal_mouth(index, mode, dark, live):
    return goal_mouth_figure_payload(index, live, dark, mode)


@callback(
    Output("goal-mouth-zone", "data"),
    Output("goal-mouth-drawer", "opened"),
    Output("goal-mouth-drawer", "title"),
    Output("goal-mouth-drawer", "children"),
    Input("goal-mouth-graph", "clickData"),
    Input("carousel-index", "data"),
    State("goal-mouth-zone", "data"),
    State("live-store", "data"),
    prevent_initial_call=True,
)
def open_goal_mouth_zone(click, index, current_zone, live):
    # Team change closes any open zone drawer.
    if ctx.triggered_id == "carousel-index":
        return None, False, no_update, no_update
    if not click or not click.get("points"):
        return no_update, no_update, no_update, no_update
    zid = click["points"][0].get("customdata")
    if isinstance(zid, list):           # customdata may arrive as a list
        zid = zid[0]
    if zid is None or zid == current_zone:   # re-click same zone -> close
        return None, False, no_update, no_update
    title, children = goal_mouth_drawer_payload(zid, index, live)
    return zid, True, title, children


@callback(
    Output("goal-mouth-zone", "data", allow_duplicate=True),
    Input("goal-mouth-drawer", "opened"),
    prevent_initial_call=True,
)
def clear_goal_mouth_zone(opened):
    # Closing via the X / overlay clears the stored zone so a re-click reopens.
    return None if not opened else no_update
```

(`no_update`, `ctx`, `State` are already imported in `app.py`.)

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests/test_app.py -k goal_mouth -v`
Expected: PASS (3 tests).

- [ ] **Step 6: Run the full suite**

Run: `python -m pytest tests/ -q`
Expected: PASS (all prior tests + the new ones; no regressions).

- [ ] **Step 7: Commit**

```bash
git add app.py tests/test_app.py
git commit -m "feat: wire goal-mouth box — shot updates, figure + zone-drawer callbacks

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 10: Widen the probe (verification only)

**Files:**
- Modify: `scratchpad/probe_shots.py`

**Interfaces:**
- Consumes: `parse_shots` (Task 2), `aggregate_goal_mouth` (Task 3) — reuse runtime logic; do NOT re-implement classification in the probe.

This task has no unit test (the probe is a network-bound scratch script). It is verification tooling: it must import the real runtime functions so the cross-tabs it prints match what the app computes.

- [ ] **Step 1: Edit the probe to emit cross-tabs**

Replace the per-shot counting loop and the report section so that, in addition to the existing distinct-value counters, it builds `ShotRecord`s per team and prints zone×outcome and zone×shooter cross-tabs via `aggregate_goal_mouth`. Add near the top:
```python
from src.data.live.shots import parse_shots               # noqa: E402
from src.data.live.goal_mouth import aggregate_goal_mouth  # noqa: E402
```
Accumulate records per team across sampled matches:
```python
    from collections import defaultdict
    per_team = defaultdict(list)
    ...
    for mid in match_ids:
        detail = client.match(mid)
        for rec in parse_shots(mid, detail):
            per_team[rec.team].append(rec)
        time.sleep(0.2)
```
And after the existing distinct-value report, print the cross-tabs:
```python
    print("\n--- per-team zone x outcome / zone x shooter ---")
    for team, recs in sorted(per_team.items()):
        agg = aggregate_goal_mouth(recs)
        print(f"\n{team}: {agg['totals']}")
        for zid, z in agg["zones"].items():
            if z["count"]:
                print(f"  {zid:>16}: {z['count']:>3}  {z['outcomes']}")
                for s in z["shooters"][:3]:
                    print(f"      {s['time']:>6}  {s['player']}  {s['outcome']}")
```
(Keep the existing distinct-`goalTarget`/`outcome`/null counters — they remain useful and confirm no new vocabulary appeared.)

- [ ] **Step 2: Run the probe (manual, requires API key)**

Run: `python scratchpad/probe_shots.py`
Expected: the existing distinct-value tables PLUS a per-team section printing each populated zone's count, outcome breakdown, and up to three shooters. Spot-check that the totals reconcile (on_target + near_miss + off_target + other = total) and that `CloseLeft`/`Close Right And High` land in `close_left`/`close_right_high`. If no API key is configured, note that this step is skipped (offline) and the cross-tab code is exercised by `tests/test_goal_mouth_agg.py` instead.

- [ ] **Step 3: Commit**

```bash
git add scratchpad/probe_shots.py
git commit -m "chore: widen shot probe to emit zone x outcome / shooter cross-tabs

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Final verification (after all tasks)

- [ ] Full suite green: `python -m pytest tests/ -q`
- [ ] Browser/e2e (Framework 3.11 python w/ Playwright, `channel="chrome"`): per-team view shows the Goal-mouth box to the right of a visibly narrower group table; no horizontal overflow at desktop and at 390px; dark AND light both render with no black-on-dark text; clicking a populated zone opens the LEFT drawer with the time-sorted shot list; the Volume/Dominant control switches the fill; empty-team state shows a clean empty frame.

---

## Self-Review (completed by plan author)

**Spec coverage:** every acceptance check in the design maps to a task — zone model/parsing (T1-T2), aggregation + reconciliation + group_only (T3), persistence (T4), fetch/aggregate service (T5), figure/hover/colors/fill-modes/readout/drawer-body (T6), title/subtitle/caption/limitation-note/mode control/left-drawer (T7), layout narrow-group + new box + mobile (T8), carousel-driven callbacks + data path + click→left-drawer (T9), probe cross-tabs (T10).

**Placeholder scan:** no TBD/“handle edge cases”/“similar to”; every code step carries complete code.

**Type consistency:** `aggregate_goal_mouth` shape is identical in T3 (producer), T5 (service), T6 (consumer), T9 (`_EMPTY_GM`). `ShotRecord` field order consistent T2/T4/T5/T6. Region ids consistent across `ZONE_MAP` (T1), `ZONE_BOX`/`ZONE_LABEL` (T6). Callback/element ids consistent: `goal-mouth-graph`, `goal-mouth-mode`, `goal-mouth-zone`, `goal-mouth-drawer`.
