# Player Leaders Card Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the placeholder Leaders card with player-level leader grids (Goals · Assists · Cards · Rating) for the carousel-selected team, aggregated across that team's matches from a per-match player-stats CSV the `live_feed` loop maintains.

**Architecture:** A pure parser turns one match's `/events` + `/matches/{id}` detail into `PlayerMatchStat` rows. A small `csv`-backed store persists those rows per match (a gitignored cache). `LiveDataService` gains `update_player_stats` (called by the WS loop, skipping already-stored finished matches) and `team_leaders` (groups stored rows by player and ranks them per stat). The `leaders_card` component renders a `dash-ag-grid` driven by a segmented control; an `app.py` callback feeds it.

**Tech Stack:** Python, `dash-ag-grid` (dag), `dash-mantine-components`, the existing `src/data/live/` subsystem (plain dataclasses + dicts — no pandas here, matching `models.py`/`reconcile.py`; the cache is serialization, not analytical wrangling), pytest.

**Environment:** Run tests with `conda run -n wc2026-live pytest tests/ -v`. The branch is `feat/highlightly-live-data` — **do NOT merge to main without explicit user validation.**

**Reference spec:** `docs/superpowers/specs/2026-06-14-player-leaders-card-design.md`

---

## File Structure

- **Create `src/data/live/player_stats.py`** — pure: `PlayerMatchStat` dataclass + `parse_player_stats(match_id, events, detail)`. No IO. Depends on `reconcile.normalize`.
- **Create `src/data/live/player_store.py`** — `csv`-backed persistence: `load`, `stored_match_states`, `upsert`. Depends on `player_stats.PlayerMatchStat`.
- **Modify `src/data/live/service.py`** — add `player_store` ctor arg, `update_player_stats(matches, now)`, `team_leaders(team)`.
- **Modify `src/components/leaders_card.py`** — add `leaders_columns(tab)` + `leaders_row_data(leaders, tab)` pure helpers; rebuild the card body as an AG grid + a Goals/Assists/Cards/Rating control.
- **Modify `app.py`** — store path constant, construct `LIVE` with it, add `leaders_payload` + `update_leaders_grid` callback, backfill past matches in `live_feed`.
- **Modify `.gitignore`** — ignore the cache CSV.
- **Create `tests/test_player_stats.py`**, **`tests/test_player_store.py`**; extend `tests/test_live_service.py`, `tests/test_leaders_card.py`, `tests/test_app.py`.

---

## Task 1: `PlayerMatchStat` + `parse_player_stats`

**Files:**
- Create: `src/data/live/player_stats.py`
- Test: `tests/test_player_stats.py`

Data shapes (verified against fixtures):
- `/events` item keys: `team` (`{"name": ...}`), `time`, `type`, `player`, `playerId`, `assist`, `assistingPlayerId`. Types seen: `Goal`, `Own Goal`, `Yellow Card`, `Red Card`, `Substitution`, `VAR Goal Cancelled - Offside`.
- Match detail `homeTeam`/`awayTeam` each have `name` and `topPlayers`: a list of `{"name", "position", "statistics": [{"name": "Goals"|"Rating"|"Assists", "value": ...}]}`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_player_stats.py`:

```python
from __future__ import annotations

from src.data.live.player_stats import PlayerMatchStat, parse_player_stats

EVENTS = [
    {"team": {"name": "USA"}, "type": "Own Goal", "player": "D. Bobadilla",
     "playerId": 31412381, "assist": None, "assistingPlayerId": None},
    {"team": {"name": "Paraguay"}, "type": "Yellow Card", "player": "J. Caceres",
     "playerId": 31554866, "assist": None, "assistingPlayerId": None},
    {"team": {"name": "USA"}, "type": "VAR Goal Cancelled - Offside",
     "player": "F. Balogun", "playerId": 22352589, "assist": None,
     "assistingPlayerId": None},
    {"team": {"name": "USA"}, "type": "Goal", "player": "F. Balogun",
     "playerId": 22352589, "assist": "C. Pulisic", "assistingPlayerId": 2891},
    {"team": {"name": "USA"}, "type": "Goal", "player": "F. Balogun",
     "playerId": 22352589, "assist": "M. Tillman", "assistingPlayerId": 26088111},
    {"team": {"name": "USA"}, "type": "Red Card", "player": "T. Adams",
     "playerId": 999, "assist": None, "assistingPlayerId": None},
]
DETAIL = {
    "homeTeam": {"name": "USA", "topPlayers": [
        {"name": "Folarin Balogun", "statistics": [
            {"name": "Goals", "value": 2}, {"name": "Rating", "value": 8.4}]},
    ]},
    "awayTeam": {"name": "Paraguay", "topPlayers": []},
}


def _by_player(rows):
    return {r.player: r for r in rows}


def test_goals_count_excludes_own_goal_and_cancelled():
    rows = parse_player_stats(7, EVENTS, DETAIL)
    balogun = next(r for r in rows if r.player_id == 22352589)
    assert balogun.goals == 2          # two Goal events; VAR-cancelled not counted
    bob = next(r for r in rows if r.player_id == 31412381)
    assert bob.goals == 0              # Own Goal not credited to scorer


def test_assists_tallied_to_assisting_player():
    rows = parse_player_stats(7, EVENTS, DETAIL)
    by_id = {r.player_id: r for r in rows}
    assert by_id[2891].assists == 1            # C. Pulisic
    assert by_id[26088111].assists == 1        # M. Tillman


def test_cards_tallied():
    rows = parse_player_stats(7, EVENTS, DETAIL)
    by_id = {r.player_id: r for r in rows}
    assert by_id[31554866].yellow == 1
    assert by_id[999].red == 1


def test_rating_from_top_players():
    rows = parse_player_stats(7, EVENTS, DETAIL)
    rated = [r for r in rows if r.rating is not None]
    assert len(rated) == 1
    assert rated[0].player == "Folarin Balogun"
    assert rated[0].rating == 8.4
    assert rated[0].team == "USA"


def test_returns_player_match_stat_with_match_id():
    rows = parse_player_stats(7, EVENTS, DETAIL)
    assert rows and all(isinstance(r, PlayerMatchStat) for r in rows)
    assert all(r.match_id == 7 for r in rows)


def test_handles_empty_inputs():
    assert parse_player_stats(7, [], {}) == []
    assert parse_player_stats(7, None, None) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `conda run -n wc2026-live pytest tests/test_player_stats.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.data.live.player_stats'`

- [ ] **Step 3: Write minimal implementation**

Create `src/data/live/player_stats.py`:

```python
from __future__ import annotations

from dataclasses import dataclass

from src.data.live.reconcile import normalize

# Only these exact event types count as a goal for the scorer. "Own Goal" is
# deliberately excluded (not credited to the scorer); "VAR Goal Cancelled - ..."
# and other types are ignored.
_GOAL_TYPES = {"Goal", "Penalty"}


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
    rating: float | None


def _team_name(raw) -> str:
    team = raw.get("team")
    if isinstance(team, dict):
        return team.get("name", "")
    return str(team or "")


def parse_player_stats(match_id: int, events, detail) -> list[PlayerMatchStat]:
    """One row per player who appears in events or topPlayers for this match.

    Events drive goals/assists/cards (keyed by playerId when present, else
    normalized name). topPlayers (no id) supply rating, keyed by normalized name.
    """
    agg: dict = {}

    def slot(team: str, player: str, pid) -> dict:
        key = pid if pid else normalize(player)
        cur = agg.get(key)
        if cur is None:
            cur = {"team": team, "player": player, "player_id": pid,
                   "goals": 0, "assists": 0, "yellow": 0, "red": 0, "rating": None}
            agg[key] = cur
        return cur

    for e in (events or []):
        etype = str(e.get("type", ""))
        team = _team_name(e)
        player = str(e.get("player", ""))
        pid = e.get("playerId")
        if etype in _GOAL_TYPES:
            slot(team, player, pid)["goals"] += 1
            aname = e.get("assist")
            if aname:
                slot(team, str(aname), e.get("assistingPlayerId"))["assists"] += 1
        elif etype == "Yellow Card":
            slot(team, player, pid)["yellow"] += 1
        elif etype == "Red Card":
            slot(team, player, pid)["red"] += 1
        elif etype == "Own Goal":
            slot(team, player, pid)   # scorer row exists but is NOT credited a goal

    for side in ("homeTeam", "awayTeam"):
        td = (detail or {}).get(side) or {}
        tname = td.get("name", "")
        for tp in (td.get("topPlayers") or []):
            stats = {s.get("name"): s.get("value") for s in (tp.get("statistics") or [])}
            rating = stats.get("Rating")
            cur = slot(tname, tp.get("name", ""), None)
            if rating is not None:
                cur["rating"] = rating

    return [PlayerMatchStat(match_id=match_id, **v) for v in agg.values()]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `conda run -n wc2026-live pytest tests/test_player_stats.py -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
git add src/data/live/player_stats.py tests/test_player_stats.py
git commit -m "feat: parse per-match player stats (events + topPlayers)"
```

---

## Task 2: Player store (CSV cache)

**Files:**
- Create: `src/data/live/player_store.py`
- Test: `tests/test_player_store.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_player_store.py`:

```python
from __future__ import annotations

from src.data.live import player_store
from src.data.live.player_stats import PlayerMatchStat


def _row(match_id, player, pid, goals=0, rating=None, team="USA"):
    return PlayerMatchStat(match_id=match_id, team=team, player=player,
                           player_id=pid, goals=goals, assists=0, yellow=0,
                           red=0, rating=rating)


def test_load_missing_file_returns_empty(tmp_path):
    assert player_store.load(tmp_path / "nope.csv") == {}
    assert player_store.stored_match_states(tmp_path / "nope.csv") == {}


def test_upsert_then_load_roundtrip(tmp_path):
    path = tmp_path / "ps.csv"
    player_store.upsert(path, 1, "finished",
                        [_row(1, "F. Balogun", 22352589, goals=2, rating=8.4)])
    loaded = player_store.load(path)
    assert set(loaded) == {1}
    row = loaded[1][0]
    assert row.player_id == 22352589
    assert row.goals == 2
    assert row.rating == 8.4
    assert player_store.stored_match_states(path) == {1: "finished"}


def test_upsert_replaces_only_target_match(tmp_path):
    path = tmp_path / "ps.csv"
    player_store.upsert(path, 1, "finished", [_row(1, "A", 1, goals=1)])
    player_store.upsert(path, 2, "live", [_row(2, "B", 2, goals=3, team="Brazil")])
    # Re-upsert match 1 with new rows; match 2 must survive untouched.
    player_store.upsert(path, 1, "finished", [_row(1, "A", 1, goals=5)])
    loaded = player_store.load(path)
    assert loaded[1][0].goals == 5
    assert loaded[2][0].goals == 3
    assert player_store.stored_match_states(path) == {1: "finished", 2: "live"}


def test_null_id_and_rating_roundtrip_as_none(tmp_path):
    path = tmp_path / "ps.csv"
    player_store.upsert(path, 1, "finished", [_row(1, "Top Player", None)])
    row = player_store.load(path)[1][0]
    assert row.player_id is None
    assert row.rating is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `conda run -n wc2026-live pytest tests/test_player_store.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.data.live.player_store'`

- [ ] **Step 3: Write minimal implementation**

Create `src/data/live/player_store.py`:

```python
from __future__ import annotations

import csv
import os
from pathlib import Path

from src.data.live.player_stats import PlayerMatchStat

# A gitignored cache of per-match player stats. `state` records the match state
# at write time so the updater can skip finished matches already on disk.
FIELDS = ["match_id", "team", "player", "player_id",
          "goals", "assists", "yellow", "red", "rating", "state"]


def load(path) -> dict[int, list[PlayerMatchStat]]:
    """match_id -> list[PlayerMatchStat]. Missing file -> {}."""
    p = Path(path)
    if not p.exists():
        return {}
    out: dict[int, list[PlayerMatchStat]] = {}
    with p.open(newline="") as f:
        for row in csv.DictReader(f):
            mid = int(row["match_id"])
            out.setdefault(mid, []).append(PlayerMatchStat(
                match_id=mid,
                team=row["team"],
                player=row["player"],
                player_id=int(row["player_id"]) if row["player_id"] else None,
                goals=int(row["goals"]),
                assists=int(row["assists"]),
                yellow=int(row["yellow"]),
                red=int(row["red"]),
                rating=float(row["rating"]) if row["rating"] else None,
            ))
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
            w.writerow({
                "match_id": s.match_id, "team": s.team, "player": s.player,
                "player_id": s.player_id if s.player_id is not None else "",
                "goals": s.goals, "assists": s.assists,
                "yellow": s.yellow, "red": s.red,
                "rating": s.rating if s.rating is not None else "",
                "state": state,
            })
    os.replace(tmp, p)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `conda run -n wc2026-live pytest tests/test_player_store.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add src/data/live/player_store.py tests/test_player_store.py
git commit -m "feat: csv-backed per-match player-stats store"
```

---

## Task 3: Service — `update_player_stats` + `team_leaders`

**Files:**
- Modify: `src/data/live/service.py`
- Test: `tests/test_live_service.py` (append)

`service.py` already has: `from src.data.live import models`, `from src.data.live.reconcile import find_stadium`, `logger`, and `LiveDataService.__init__(self, client, stadium_index, league_id=LEAGUE_ID, season=SEASON)`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_live_service.py`:

```python
# ---------------------------------------------------------------------------
# update_player_stats / team_leaders
# ---------------------------------------------------------------------------

from src.data.live import player_store  # noqa: E402


class _StatsClient(_FakeClient):
    def __init__(self):
        super().__init__()
        self.event_calls = {}
        self.detail_calls = {}

    def events(self, match_id):
        self.event_calls[match_id] = self.event_calls.get(match_id, 0) + 1
        return [
            {"team": {"name": "USA"}, "type": "Goal", "player": "F. Balogun",
             "playerId": 100, "assist": "C. Pulisic", "assistingPlayerId": 200},
            {"team": {"name": "USA"}, "type": "Yellow Card", "player": "T. Adams",
             "playerId": 300},
        ]

    def match(self, match_id):
        self.detail_calls[match_id] = self.detail_calls.get(match_id, 0) + 1
        return [{"id": match_id,
                 "homeTeam": {"name": "USA", "topPlayers": [
                     {"name": "Folarin Balogun",
                      "statistics": [{"name": "Rating", "value": 8.0}]}]},
                 "awayTeam": {"name": "Paraguay", "topPlayers": []}}]


def test_update_player_stats_fetches_and_stores_finished(tmp_path):
    path = tmp_path / "ps.csv"
    c = _StatsClient()
    svc = LiveDataService(c, _index(), player_store=path)
    matches = [{"match_id": 1, "state": MatchState.FINISHED.value}]
    svc.update_player_stats(matches, now=0.0)
    assert player_store.stored_match_states(path) == {1: MatchState.FINISHED.value}
    assert c.event_calls[1] == 1


def test_update_player_stats_skips_already_stored_finished(tmp_path):
    path = tmp_path / "ps.csv"
    c = _StatsClient()
    svc = LiveDataService(c, _index(), player_store=path)
    matches = [{"match_id": 1, "state": MatchState.FINISHED.value}]
    svc.update_player_stats(matches, now=0.0)
    svc.update_player_stats(matches, now=1.0)   # second pass must not re-fetch
    assert c.event_calls[1] == 1


def test_update_player_stats_overwrites_live(tmp_path):
    path = tmp_path / "ps.csv"
    c = _StatsClient()
    svc = LiveDataService(c, _index(), player_store=path)
    matches = [{"match_id": 2, "state": MatchState.LIVE.value}]
    svc.update_player_stats(matches, now=0.0)
    svc.update_player_stats(matches, now=1.0)   # live always re-fetched
    assert c.event_calls[2] == 2


def test_update_player_stats_noop_without_store():
    svc = LiveDataService(_StatsClient(), _index())   # no player_store
    svc.update_player_stats([{"match_id": 1, "state": "finished"}], now=0.0)  # no crash


def test_team_leaders_groups_and_ranks(tmp_path):
    path = tmp_path / "ps.csv"
    c = _StatsClient()
    svc = LiveDataService(c, _index(), player_store=path)
    # Two matches for USA so apps and sums accumulate.
    svc.update_player_stats([{"match_id": 1, "state": MatchState.FINISHED.value}], now=0.0)
    svc.update_player_stats([{"match_id": 2, "state": MatchState.FINISHED.value}], now=0.0)
    leaders = svc.team_leaders("USA")
    goals = leaders["goals"]
    assert goals[0]["player"] == "F. Balogun"
    assert goals[0]["value"] == 2          # one goal in each of two matches
    assert goals[0]["apps"] == 2
    assert leaders["assists"][0]["value"] == 2     # C. Pulisic, two assists
    assert leaders["cards"][0]["value"] == 2       # T. Adams, two yellows
    assert leaders["rating"][0]["value"] == 8.0    # avg of 8.0 and 8.0


def test_team_leaders_empty_without_store():
    svc = LiveDataService(_StatsClient(), _index())
    assert svc.team_leaders("USA") == {}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `conda run -n wc2026-live pytest tests/test_live_service.py -k "player_stats or team_leaders" -v`
Expected: FAIL with `TypeError: __init__() got an unexpected keyword argument 'player_store'`

- [ ] **Step 3: Write minimal implementation**

In `src/data/live/service.py`, update the imports near the top. The file currently has these two lines:

```python
from src.data.live import models
from src.data.live.reconcile import find_stadium
```

Replace **both** of them with (note `models` gains `player_store`; `reconcile` gains `canonical_team`; add `Path`):

```python
from pathlib import Path

from src.data.live import models, player_store
from src.data.live.player_stats import parse_player_stats
from src.data.live.reconcile import canonical_team, find_stadium
```

Keep the existing `import logging` and `logger = logging.getLogger(__name__)` lines as-is.

Change `__init__` to accept and store the cache path:

```python
    def __init__(self, client, stadium_index, league_id=LEAGUE_ID, season=SEASON,
                 player_store=None):
        self._client = client
        self._stadium_index = stadium_index
        self._league_id = league_id
        self._season = season
        self._player_store = Path(player_store) if player_store else None
        self._cache: dict[str, tuple[float, object]] = {}
        self._last_good: dict | None = None
```

Add these two methods to the class (e.g. after `match_summary`, before `_match_dict`):

```python
    def update_player_stats(self, matches, now: float) -> None:
        """Refresh the player-stats cache from today's matches.

        Finished & already stored -> skip (no fetch). Finished & new, or live ->
        fetch events + detail once and overwrite that match's rows. Each match is
        independent: a failure is logged and skipped, leaving the cache intact.
        """
        if self._player_store is None:
            return
        stored = player_store.stored_match_states(self._player_store)
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
                events = self._client.events(mid)
                detail = self._client.match(mid)
                detail_obj = detail[0] if isinstance(detail, list) and detail else detail
                rows = parse_player_stats(mid, events, detail_obj)
                player_store.upsert(self._player_store, mid, state, rows)
            except Exception:
                logger.exception("player stats update failed for match %s", mid)

    def team_leaders(self, team: str) -> dict:
        """Per-stat ranked leader rows for `team` aggregated across its matches.

        Returns {"goals"|"assists"|"cards"|"rating": [{player, value, apps}, ...]}.
        Players are grouped by playerId when present, else normalized name. Each
        list is filtered to players with a value for that stat and sorted desc.
        """
        if self._player_store is None:
            return {}
        by_match = player_store.load(self._player_store)
        target = canonical_team(team)
        groups: dict = {}
        for rows in by_match.values():
            for r in rows:
                if canonical_team(r.team) != target:
                    continue
                key = r.player_id if r.player_id else r.player.strip().lower()
                g = groups.get(key)
                if g is None:
                    g = {"player": r.player, "goals": 0, "assists": 0,
                         "yellow": 0, "red": 0, "ratings": [], "matches": set()}
                    groups[key] = g
                if len(r.player) > len(g["player"]):
                    g["player"] = r.player        # prefer the fuller name
                g["goals"] += r.goals
                g["assists"] += r.assists
                g["yellow"] += r.yellow
                g["red"] += r.red
                if r.rating is not None:
                    g["ratings"].append(r.rating)
                g["matches"].add(r.match_id)

        def ranked(value_fn, keep_fn):
            out = [{"player": g["player"], "value": value_fn(g), "apps": len(g["matches"])}
                   for g in groups.values() if keep_fn(g)]
            out.sort(key=lambda d: d["value"], reverse=True)
            return out

        return {
            "goals": ranked(lambda g: g["goals"], lambda g: g["goals"] > 0),
            "assists": ranked(lambda g: g["assists"], lambda g: g["assists"] > 0),
            "cards": ranked(lambda g: g["yellow"] + g["red"],
                            lambda g: (g["yellow"] + g["red"]) > 0),
            "rating": ranked(lambda g: round(sum(g["ratings"]) / len(g["ratings"]), 2),
                             lambda g: len(g["ratings"]) > 0),
        }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `conda run -n wc2026-live pytest tests/test_live_service.py -v`
Expected: PASS (all existing service tests + the 6 new ones)

- [ ] **Step 5: Commit**

```bash
git add src/data/live/service.py tests/test_live_service.py
git commit -m "feat: LiveDataService.update_player_stats + team_leaders"
```

---

## Task 4: Leaders card component

**Files:**
- Modify: `src/components/leaders_card.py`
- Test: `tests/test_leaders_card.py` (replace)

The card currently renders a `SegmentedControl` (`id="leaders-tabs"`, data `["Goals","Assists","Cards"]`) over an empty state. Replace the empty state with a `dash-ag-grid` (mirror `src/components/squad_table.py`: `dag.AgGrid`, `className="ag-theme-quartz-dark ..."`, `dashGridOptions`), add a `Rating` tab, and add pure column/row helpers. Give the header's right-hand `Text` an id so a callback can show the team name.

- [ ] **Step 1: Write the failing test**

Replace the contents of `tests/test_leaders_card.py`:

```python
import dash_ag_grid as dag
import dash_mantine_components as dmc

from src.components.leaders_card import (
    build_leaders_card,
    leaders_columns,
    leaders_row_data,
)


def _walk(node):
    yield node
    children = getattr(node, "children", None)
    if isinstance(children, (list, tuple)):
        for c in children:
            yield from _walk(c)
    elif children is not None:
        yield from _walk(children)


def test_leaders_card_has_header_and_four_tabs():
    card = build_leaders_card()
    assert card.className == "leaders-panel"
    texts = [n.children for n in _walk(card)
             if isinstance(n, dmc.Text) and isinstance(n.children, str)]
    assert "Leaders" in texts
    seg = next(n for n in _walk(card) if isinstance(n, dmc.SegmentedControl))
    values = [d["value"] if isinstance(d, dict) else d for d in seg.data]
    assert values == ["Goals", "Assists", "Cards", "Rating"]


def test_leaders_card_has_grid():
    card = build_leaders_card()
    grid = next(n for n in _walk(card) if isinstance(n, dag.AgGrid))
    assert grid.id == "leaders-grid"


def test_leaders_columns_header_reflects_tab():
    cols = leaders_columns("Assists")
    headers = [c["headerName"] for c in cols]
    assert headers == ["#", "Player", "Assists", "Apps"]
    fields = [c["field"] for c in cols]
    assert fields == ["rank", "player", "value", "apps"]


def test_leaders_row_data_picks_stat_and_adds_rank():
    leaders = {"goals": [{"player": "A", "value": 3, "apps": 2},
                         {"player": "B", "value": 1, "apps": 1}]}
    rows = leaders_row_data(leaders, "Goals")
    assert rows == [
        {"rank": 1, "player": "A", "value": 3, "apps": 2},
        {"rank": 2, "player": "B", "value": 1, "apps": 1},
    ]


def test_leaders_row_data_empty_when_no_data():
    assert leaders_row_data({}, "Goals") == []
    assert leaders_row_data(None, "Rating") == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `conda run -n wc2026-live pytest tests/test_leaders_card.py -v`
Expected: FAIL with `ImportError: cannot import name 'leaders_columns'`

- [ ] **Step 3: Write minimal implementation**

Replace the contents of `src/components/leaders_card.py`:

```python
from __future__ import annotations

import dash_ag_grid as dag
import dash_mantine_components as dmc

# Segmented-control label -> the stat key returned by LiveDataService.team_leaders.
_STAT_KEYS = {"Goals": "goals", "Assists": "assists",
              "Cards": "cards", "Rating": "rating"}

_GRID_OPTIONS = {
    "suppressCellFocus": True,
    "rowHeight": 34,
    "headerHeight": 34,
    "overlayNoRowsTemplate": "No player data yet",
}


def _stat_key(tab: str) -> str:
    return _STAT_KEYS.get(tab, "goals")


def leaders_columns(tab: str) -> list[dict]:
    """Column defs for the active tab. The stat column's header is the tab name;
    its field is always `value` so the grid need not be rebuilt on tab change."""
    return [
        {"headerName": "#", "field": "rank", "width": 52, "sortable": False,
         "cellClass": "leaders-grid__rank"},
        {"headerName": "Player", "field": "player", "flex": 1,
         "minWidth": 120, "sortable": True},
        {"headerName": tab, "field": "value", "width": 84, "sortable": True,
         "type": "rightAligned"},
        {"headerName": "Apps", "field": "apps", "width": 70, "sortable": True,
         "type": "rightAligned"},
    ]


def leaders_row_data(leaders: dict | None, tab: str) -> list[dict]:
    """Rows for the active tab, with a 1-based rank. Empty list when no data."""
    rows = (leaders or {}).get(_stat_key(tab), [])
    return [{"rank": i + 1, "player": r["player"], "value": r["value"],
             "apps": r["apps"]} for i, r in enumerate(rows)]


def build_leaders_card() -> dmc.Box:
    """Player-leaders card: a Goals/Assists/Cards/Rating control over an AG grid
    of the selected team's players, ranked by the active stat."""
    header = dmc.Group(
        [
            dmc.Text("Leaders", fw=700, size="sm"),
            dmc.Text("", id="leaders-table-title", size="sm", c="dimmed"),
        ],
        justify="space-between",
        align="center",
        wrap="nowrap",
        className="bento-card__header",
    )

    tabs = dmc.SegmentedControl(
        id="leaders-tabs",
        value="Goals",
        data=["Goals", "Assists", "Cards", "Rating"],
        size="xs",
        fullWidth=True,
    )

    grid = dag.AgGrid(
        id="leaders-grid",
        columnDefs=leaders_columns("Goals"),
        rowData=[],
        className="ag-theme-quartz-dark leaders-grid",
        dashGridOptions=_GRID_OPTIONS,
        style={"width": "100%", "height": "100%"},
    )

    body = dmc.Box([tabs, grid], className="leaders-panel__body")
    return dmc.Box([header, body], className="leaders-panel")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `conda run -n wc2026-live pytest tests/test_leaders_card.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add src/components/leaders_card.py tests/test_leaders_card.py
git commit -m "feat: leaders card renders AG grid with Goals/Assists/Cards/Rating"
```

---

## Task 5: Wire into app.py + gitignore the cache

**Files:**
- Modify: `app.py`
- Modify: `.gitignore`
- Test: `tests/test_app.py` (append)

Current `app.py` anchors:
- `DATA_DIR` is defined before the repositories (used as `DATA_DIR / "teams.csv"` at line ~55).
- `LIVE = (LiveDataService(HighlightlyClient(api_key=_API_KEY), STADIUM_INDEX) if _API_KEY else None)` (lines ~78-81).
- `from src.components.leaders_card import build_leaders_card` (line ~24).
- `MATCHES = MatchRepository(...).load()` (line ~57); each `Match` has a `.date` (a `date`).
- `center_team`, `TEAM_NAMES` already imported/defined.
- `update_squad_panel` callback (lines ~474-481) is the pattern to mirror.
- `live_feed` WS callback (lines ~636-645).

- [ ] **Step 1: Write the failing test**

Append to `tests/test_app.py`:

```python
def test_leaders_payload_columns_and_team():
    import app
    rows, cols, team = app.leaders_payload("Goals", 0)
    assert team == app.center_team(app.TEAM_NAMES, 0)
    assert [c["headerName"] for c in cols] == ["#", "Player", "Goals", "Apps"]
    assert isinstance(rows, list)   # empty in no-key test env, but well-formed


def test_leaders_payload_rating_tab_header():
    import app
    _rows, cols, _team = app.leaders_payload("Rating", 3)
    assert cols[2]["headerName"] == "Rating"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `conda run -n wc2026-live pytest tests/test_app.py -k leaders_payload -v`
Expected: FAIL with `AttributeError: module 'app' has no attribute 'leaders_payload'`

- [ ] **Step 3: Write minimal implementation**

In `app.py`, extend the leaders-card import (line ~24):

```python
from src.components.leaders_card import (
    build_leaders_card,
    leaders_columns,
    leaders_row_data,
)
```

Add the cache-path constant and pass it to `LIVE`. Replace the `LIVE = (...)` block (lines ~78-81) with:

```python
# Per-match player-stats cache (gitignored). The live_feed loop maintains it;
# team_leaders reads it for the leaders card.
PLAYER_STORE_PATH = DATA_DIR / "live_player_stats.csv"
LIVE = (
    LiveDataService(HighlightlyClient(api_key=_API_KEY), STADIUM_INDEX,
                    player_store=PLAYER_STORE_PATH)
    if _API_KEY else None
)
```

Add a payload helper next to the other `*_payload` helpers (e.g. after `squad_panel_payload`, ~line 116):

```python
def leaders_payload(stat, index):
    """(rowData, columnDefs, team_name) for the leaders grid: the centred team's
    player leaders for the active stat tab. Empty rows when there's no live data."""
    team = center_team(TEAM_NAMES, index or 0)
    leaders = LIVE.team_leaders(team) if LIVE is not None else {}
    return leaders_row_data(leaders, stat), leaders_columns(stat), team
```

Add the callback next to the other panel callbacks (e.g. after `update_squad_panel`, ~line 481):

```python
@callback(
    Output("leaders-grid", "rowData"),
    Output("leaders-grid", "columnDefs"),
    Output("leaders-table-title", "children"),
    Input("leaders-tabs", "value"),
    Input("carousel-index", "data"),
    Input("live-store", "data"),
)
def update_leaders_panel(stat, index, live):
    rows, cols, team = leaders_payload(stat, index)
    return rows, cols, team
```

Add a backfill helper above the `live_feed` callback (e.g. just before line ~636):

```python
def _backfill_player_stats():
    """One-time refresh of the player-stats cache from past scheduled dates.
    Idempotent: update_player_stats skips finished matches already on disk."""
    today = date.today()
    now = time.monotonic()
    for d in sorted({m.date for m in MATCHES if m.date <= today}):
        LIVE.update_player_stats(LIVE.matches_on(d.isoformat(), now), now)
```

Update the `live_feed` body to backfill once, then update per poll:

```python
@callback(persistent=True)
async def live_feed():
    ws = ctx.websocket
    if ws is None or LIVE is None:
        return
    await asyncio.to_thread(_backfill_player_stats)
    while not ws.is_shutdown:
        now = asyncio.get_running_loop().time()
        snap = await asyncio.to_thread(LIVE.snapshot, date.today().isoformat(), now)
        set_props("live-store", {"data": snap})
        await asyncio.to_thread(LIVE.update_player_stats, snap["matches"], now)
        await asyncio.sleep(next_delay(snap))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `conda run -n wc2026-live pytest tests/test_app.py -k leaders_payload -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Gitignore the cache file**

Add to `.gitignore` (after the `.env` lines):

```
assets/data/live_player_stats.csv
```

- [ ] **Step 6: Run the full suite**

Run: `conda run -n wc2026-live pytest tests/ -v`
Expected: PASS (all tests green, offline — no API key, leaders grids empty)

- [ ] **Step 7: Commit**

```bash
git add app.py .gitignore tests/test_app.py
git commit -m "feat: wire player leaders grid into app (callback + backfill)"
```

---

## Notes for the implementer

- **No pandas in this subsystem** — `src/data/live/` uses plain dataclasses and dicts (`models.py`, `reconcile.py`). The store is cache serialization, not analytical wrangling, so the `csv` module is the right fit and matches existing patterns.
- **Name reconciliation is intentionally shallow.** Events use abbreviated names ("F. Balogun") with a `playerId`; topPlayers use full names ("Folarin Balogun") with no id. They will usually land as separate rows — that's accepted (Rating is "partial" per the spec). Do not add fuzzy matching.
- **Offline/no-key is the test baseline.** `LIVE is None` when `HIGHLIGHTLY_API_KEY` is unset, so `team_leaders`/`leaders_payload` return empty and the whole suite runs without network.
- **Branch discipline:** stay on `feat/highlightly-live-data`; do not merge to main.
```
