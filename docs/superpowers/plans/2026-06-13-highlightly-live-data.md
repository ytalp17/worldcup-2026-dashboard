# Highlightly Live Data Integration — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Overlay live World Cup 2026 data (scores, standings, events, confirmed lineups) from the Highlightly API onto the existing static dashboard, pushed to the browser via Dash 4.2 WebSocket callbacks.

**Architecture:** All network IO is isolated in a synchronous `src/data/live/` package (client → models → service, plus venue/team reconciliation). A persistent async WebSocket callback polls the service on an adaptive cadence and pushes a JSON snapshot to a `dcc.Store`; ordinary HTTP callbacks render the map markers, live strip, drawer, modal, and group tables off that Store. Static CSV/JSON data is the floor — on any API failure the UI falls back to it.

**Tech Stack:** Python 3 (conda base), Dash 4.2 (`backend="fastapi"`, `websocket_callbacks=True`), uvicorn, dash-mantine-components, dash-leaflet, pandas, requests, pytest.

**Branch:** All work on `feat/highlightly-live-data`. **Do NOT merge to main — ask the user to validate first.**

**Reference:** [docs/references/dash-websocket-callbacks.md](../../references/dash-websocket-callbacks.md) — Dash 4.2 WebSocket API.

---

## Conventions (match existing code)

- Data entities are frozen `@dataclass` objects; loaders/services are classes (see `src/data/matches.py`).
- Tests live in `tests/test_<topic>.py`, run with `pytest tests/ -v` on the conda base env.
- All `src/` files start with `from __future__ import annotations`.
- Secrets come from env vars; never commit the API key. `.env` is gitignored.
- DMC component APIs are fetched via the context7 MCP **before** building any new DMC component (per CLAUDE.md).

---

## Phase 1 — Dash 4.2 migration (the gate: fail fast before any live work)

### Task 1: Upgrade dependencies and verify the app still boots

**Files:**
- Modify: `requirements.txt`
- Modify: `requirements-dev.txt`

- [ ] **Step 1: Pin the new dependencies**

In `requirements.txt`, replace the `dash==2.18.1` line and add the server:

```text
dash[fastapi]>=4.2,<5
uvicorn[standard]
dash-leaflet==1.0.11
dash-mantine-components==2.4.0
dash-iconify==0.1.2
pandas==2.2.3
pytest==8.3.4
certifi
requests
```

In `requirements-dev.txt` add async-test support under the existing entries:

```text
pytest-asyncio
```

- [ ] **Step 2: Install into conda base**

Run: `pip install -r requirements.txt -r requirements-dev.txt`
Expected: dash 4.2.x, fastapi, uvicorn installed without dependency conflicts. If DMC 2.4.0 or dash-leaflet 1.0.11 reports an incompatibility with dash 4.2, STOP and report the exact conflict — this is the fail-fast gate.

- [ ] **Step 3: Commit**

```bash
git add requirements.txt requirements-dev.txt
git commit -m "build: upgrade to Dash 4.2 (fastapi backend) + uvicorn"
```

### Task 2: Switch the app to the FastAPI backend and remove the React-version hack

**Files:**
- Modify: `app.py:35-40` (the `dash._dash_renderer._set_react_version` block and the `Dash(...)` constructor)

- [ ] **Step 1: Locate the current constructor**

Find in `app.py` the block:

```python
dash._dash_renderer._set_react_version("18.2.0")
```

and the `app = Dash(...)` / `app = dash.Dash(...)` call (search `Dash(`).

- [ ] **Step 2: Replace with the FastAPI + WebSocket constructor**

Remove the `_set_react_version` line (Dash 4 defaults to React 18). Change the constructor to:

```python
app = Dash(
    __name__,
    backend="fastapi",
    websocket_callbacks=True,
    suppress_callback_exceptions=True,
)
```

Keep the existing `external_stylesheets` / `assets` args if present.

- [ ] **Step 3: Run the app in dev mode and confirm the map renders**

Run: `python app.py` (dev server). Open the printed URL.
Expected: the Leaflet map (USA/Mexico/Canada), DMC components, and the dark/light switch all render with no console error. If the map or DMC fails, STOP and report — this is still the gate. (Map rendering is the heart of the app; it must survive the upgrade.)

- [ ] **Step 4: Run the existing test suite**

Run: `pytest tests/ -v`
Expected: all currently-passing tests still pass. Fix any import/API breakage caused by the Dash 4.2 upgrade before continuing.

- [ ] **Step 5: Commit**

```bash
git add app.py
git commit -m "feat: run app on FastAPI backend with websocket callbacks enabled"
```

### Task 3: Document the production run command

**Files:**
- Modify: `app.py` (the `if __name__ == "__main__":` block)

- [ ] **Step 1: Confirm the dev entrypoint**

Ensure the bottom of `app.py` is:

```python
if __name__ == "__main__":
    app.run(debug=True)
```

- [ ] **Step 2: Add a Procfile for production**

**Files:** Create `Procfile`

```text
web: uvicorn app:app.server --host 0.0.0.0 --port $PORT
```

- [ ] **Step 3: Commit**

```bash
git add app.py Procfile
git commit -m "build: add uvicorn production entrypoint"
```

---

## Phase 2 — Live data layer (synchronous, fully offline-testable)

> ### ⚠️ REVISION after Task 5 fixture capture (authoritative — overrides Tasks 6–8 below)
>
> Real API responses (committed under `tests/fixtures/live/`) differ from the documented
> assumptions. Tasks 6–8 implementers MUST follow these corrections:
>
> 1. **Matches list** is `{"data": [...]}`. Each match has `.id`, `.homeTeam.name`,
>    `.awayTeam.name`, `.state.description` (`"Not started"` | `"Finished"` | live strings),
>    `.state.clock` (int minutes or null), `.state.score.current` (string `"4 - 1"` or null).
>    **There is NO venue on list matches** — venue only exists on the single-match detail.
> 2. **Venue strategy CHANGED:** do not reconcile venue *names*. Instead **join each live match
>    to the static schedule (`MATCHES` from `wc2026_matches.csv`) by team pair** and take that
>    match's `stadium`. Group-stage pairings are unique, so `(home, away)` is a safe key.
>    Live names seen (Brazil, Morocco, USA, Paraguay, Mexico) match our static names exactly;
>    use normalization + a small alias map for FIFA spelling diffs, and return `None` (no map
>    badge, graceful) when no static match is found.
> 3. **Standings** is `{"groups": [...]}`. Each group `.name`; rows at `.standings[]`; per row:
>    team `.team.name`, `.points`, played `.total.games`, won `.total.wins`, drawn
>    `.total.draws`, lost `.total.loses`; goal-diff = `.total.scoredGoals - .total.receivedGoals`
>    (no stored GD). **Skip the rollup group** whose name is `"Group Stage"` (keep only `Group A`…`Group L`).
> 4. **Events** endpoint returns a **bare list** (not `{"events": [...]}`); was empty for the
>    unplayed sample, so event field names are confirmed later when building the modal (Task 14).
> 5. **Single match detail** (`/matches/{id}`) returns a **bare list of one**; venue at
>    `.venue.name`/`.venue.city`, plus `.events`, `.statistics`, `.predictions`, `.lineups`.

### Task 4: HighlightlyClient — the only HTTP boundary

**Files:**
- Create: `src/data/live/__init__.py` (empty)
- Create: `src/data/live/client.py`
- Test: `tests/test_live_client.py`

- [ ] **Step 1: Write the failing test**

```python
from __future__ import annotations

import pytest

from src.data.live.client import HighlightlyClient, RateLimitError


class _FakeResponse:
    def __init__(self, status, payload, headers=None):
        self.status_code = status
        self._payload = payload
        self.headers = headers or {}

    def json(self):
        return self._payload


def test_matches_calls_correct_url_and_headers(monkeypatch):
    captured = {}

    def fake_get(url, headers=None, params=None, timeout=None):
        captured["url"] = url
        captured["headers"] = headers
        captured["params"] = params
        return _FakeResponse(200, {"data": [{"id": 1}]},
                             {"x-ratelimit-requests-remaining": "99"})

    monkeypatch.setattr("src.data.live.client.requests.get", fake_get)
    client = HighlightlyClient(api_key="KEY")
    out = client.matches(date="2026-06-13", league_id=1635)

    assert captured["url"] == "https://soccer.highlightly.net/matches"
    assert captured["headers"]["x-rapidapi-key"] == "KEY"
    assert captured["params"] == {"date": "2026-06-13", "leagueId": 1635}
    assert out == {"data": [{"id": 1}]}
    assert client.requests_remaining == 99


def test_rate_limit_raises(monkeypatch):
    def fake_get(url, headers=None, params=None, timeout=None):
        return _FakeResponse(429, {}, {})
    monkeypatch.setattr("src.data.live.client.requests.get", fake_get)
    client = HighlightlyClient(api_key="KEY")
    with pytest.raises(RateLimitError):
        client.matches(date="2026-06-13", league_id=1635)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_live_client.py -v`
Expected: FAIL — `ModuleNotFoundError: src.data.live.client`.

- [ ] **Step 3: Write minimal implementation**

```python
from __future__ import annotations

import requests

BASE_URL = "https://soccer.highlightly.net"
_TIMEOUT = 10


class HighlightlyError(Exception):
    """Base error for the Highlightly client."""


class RateLimitError(HighlightlyError):
    """Raised on HTTP 429 (quota exhausted)."""


class HighlightlyClient:
    """Thin synchronous wrapper over the Highlightly football API.

    This is the ONLY component that performs network IO. Returns raw dicts;
    parsing into domain models happens in models.py.
    """

    def __init__(self, api_key: str, base_url: str = BASE_URL) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self.requests_remaining: int | None = None

    def _get(self, path: str, params: dict) -> dict:
        resp = requests.get(
            f"{self._base_url}{path}",
            headers={"x-rapidapi-key": self._api_key},
            params=params,
            timeout=_TIMEOUT,
        )
        remaining = resp.headers.get("x-ratelimit-requests-remaining")
        if remaining is not None:
            self.requests_remaining = int(remaining)
        if resp.status_code == 429:
            raise RateLimitError("Highlightly quota exhausted")
        if resp.status_code != 200:
            raise HighlightlyError(f"HTTP {resp.status_code} for {path}")
        return resp.json()

    def matches(self, date: str, league_id: int) -> dict:
        return self._get("/matches", {"date": date, "leagueId": league_id})

    def match(self, match_id: int) -> dict:
        return self._get(f"/matches/{match_id}", {})

    def events(self, match_id: int) -> dict:
        return self._get(f"/events/{match_id}", {})

    def lineups(self, match_id: int) -> dict:
        return self._get(f"/lineups/{match_id}", {})

    def standings(self, league_id: int, season: int) -> dict:
        return self._get("/standings", {"leagueId": league_id, "season": season})
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_live_client.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add src/data/live/__init__.py src/data/live/client.py tests/test_live_client.py
git commit -m "feat: HighlightlyClient HTTP boundary with rate-limit handling"
```

### Task 5: Capture real API fixtures and confirm league id / season

**Files:**
- Create: `scripts/capture_live_fixtures.py`
- Create: `tests/fixtures/live/` (holds the captured JSON)

> This task hits the real API once to pin the response schema and confirm `leagueId=1635` / `season=2026`. Subsequent parsing tasks (Task 6) are validated against these fixtures. Requires `HIGHLIGHTLY_API_KEY` in the environment.

- [ ] **Step 1: Write the capture script**

```python
"""Capture real Highlightly responses into tests/fixtures/live/ so model
parsing can be developed and tested offline. Run once:
    HIGHLIGHTLY_API_KEY=... python scripts/capture_live_fixtures.py
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from src.data.live.client import HighlightlyClient

LEAGUE_ID = 1635
SEASON = 2026
OUT = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "live"


def main() -> None:
    key = os.environ["HIGHLIGHTLY_API_KEY"]
    client = HighlightlyClient(api_key=key)
    OUT.mkdir(parents=True, exist_ok=True)

    today = client.matches(date="2026-06-13", league_id=LEAGUE_ID)
    (OUT / "matches.json").write_text(json.dumps(today, indent=2))
    print(f"matches: {len(today.get('data', today))} rows; "
          f"remaining={client.requests_remaining}")

    standings = client.standings(league_id=LEAGUE_ID, season=SEASON)
    (OUT / "standings.json").write_text(json.dumps(standings, indent=2))

    rows = today.get("data", today)
    if rows:
        mid = rows[0]["id"]
        (OUT / "match.json").write_text(json.dumps(client.match(mid), indent=2))
        (OUT / "events.json").write_text(json.dumps(client.events(mid), indent=2))
        (OUT / "lineups.json").write_text(json.dumps(client.lineups(mid), indent=2))


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run it and inspect the JSON**

Run: `HIGHLIGHTLY_API_KEY=$HIGHLIGHTLY_API_KEY python scripts/capture_live_fixtures.py`
Expected: files written under `tests/fixtures/live/`. Open `matches.json` and note the EXACT field paths for: match id, home/away team names, venue/stadium name, `state.description`, `state.clock`, `state.score.current`. If a field path differs from what Task 6 assumes, update Task 6's parsing to match the real keys (this is the one place the real schema overrides the documented assumption).

- [ ] **Step 3: Commit the fixtures**

```bash
git add scripts/capture_live_fixtures.py tests/fixtures/live/
git commit -m "test: capture real Highlightly fixtures; confirm league 1635 / season 2026"
```

### Task 6: Domain models parsed from raw JSON

**Files:**
- Create: `src/data/live/models.py`
- Test: `tests/test_live_models.py`

> Field paths below follow the documented API shape (state.description, state.clock,
> state.score.current, events array). If Task 5's fixtures revealed different keys, use the
> real keys and adjust the test fixture inline.

- [ ] **Step 1: Write the failing test**

```python
from __future__ import annotations

from src.data.live.models import (
    LiveMatch, MatchState, parse_match, parse_events, parse_standings, MatchEvent,
)

_RAW_MATCH = {
    "id": 42,
    "homeTeam": {"name": "Brazil"},
    "awayTeam": {"name": "Mexico"},
    "venue": {"name": "Dallas Stadium"},
    "state": {"description": "Second Half", "clock": 67,
              "score": {"current": "2 - 1"}},
}


def test_parse_match_live():
    m = parse_match(_RAW_MATCH)
    assert isinstance(m, LiveMatch)
    assert m.match_id == 42
    assert m.home == "Brazil"
    assert m.away == "Mexico"
    assert m.venue == "Dallas Stadium"
    assert m.state is MatchState.LIVE
    assert m.clock == 67
    assert m.home_score == 2
    assert m.away_score == 1
    assert m.is_live is True


def test_parse_match_scheduled():
    raw = {**_RAW_MATCH, "state": {"description": "Not started", "clock": None,
                                    "score": {"current": None}}}
    m = parse_match(raw)
    assert m.state is MatchState.SCHEDULED
    assert m.is_live is False
    assert m.home_score is None


def test_parse_events_sorted_by_minute():
    raw = {"events": [
        {"type": "Goal", "minute": 67, "player": "Neymar", "team": "Brazil"},
        {"type": "Yellow Card", "minute": 12, "player": "Alvarez", "team": "Mexico"},
    ]}
    events = parse_events(raw)
    assert [e.minute for e in events] == [12, 67]
    assert isinstance(events[0], MatchEvent)


def test_parse_standings():
    raw = {"groups": [{"name": "Group A", "standings": [
        {"team": {"name": "Brazil"}, "points": 6, "played": 2,
         "won": 2, "drawn": 0, "lost": 0, "goalDifference": 4},
    ]}]}
    table = parse_standings(raw)
    assert table["Group A"][0].team == "Brazil"
    assert table["Group A"][0].points == 6
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_live_models.py -v`
Expected: FAIL — `ModuleNotFoundError: src.data.live.models`.

- [ ] **Step 3: Write minimal implementation**

```python
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

_LIVE_STATES = {"first half", "second half", "extra time", "halftime",
                "penalties", "in progress"}
_FINISHED_STATES = {"finished", "full time", "ft", "after extra time",
                    "after penalties"}


class MatchState(str, Enum):
    SCHEDULED = "scheduled"
    LIVE = "live"
    HALF_TIME = "half_time"
    FINISHED = "finished"
    OTHER = "other"


def _classify(description: str | None) -> MatchState:
    text = (description or "").strip().lower()
    if text in {"halftime", "half time", "ht"}:
        return MatchState.HALF_TIME
    if text in _LIVE_STATES:
        return MatchState.LIVE
    if text in _FINISHED_STATES:
        return MatchState.FINISHED
    if text in {"not started", "scheduled", "ns", ""}:
        return MatchState.SCHEDULED
    return MatchState.OTHER


def _split_score(current: str | None) -> tuple[int | None, int | None]:
    if not current or "-" not in current:
        return None, None
    home, _, away = current.partition("-")
    try:
        return int(home.strip()), int(away.strip())
    except ValueError:
        return None, None


@dataclass(frozen=True)
class LiveMatch:
    match_id: int
    home: str
    away: str
    venue: str
    state: MatchState
    clock: int | None
    home_score: int | None
    away_score: int | None

    @property
    def is_live(self) -> bool:
        return self.state in (MatchState.LIVE, MatchState.HALF_TIME)


@dataclass(frozen=True)
class MatchEvent:
    minute: int
    type: str
    player: str
    team: str


@dataclass(frozen=True)
class Standing:
    team: str
    played: int
    won: int
    drawn: int
    lost: int
    goal_diff: int
    points: int


def parse_match(raw: dict) -> LiveMatch:
    state = raw.get("state", {})
    home_score, away_score = _split_score(state.get("score", {}).get("current"))
    return LiveMatch(
        match_id=int(raw["id"]),
        home=raw.get("homeTeam", {}).get("name", ""),
        away=raw.get("awayTeam", {}).get("name", ""),
        venue=raw.get("venue", {}).get("name", ""),
        state=_classify(state.get("description")),
        clock=state.get("clock"),
        home_score=home_score,
        away_score=away_score,
    )


def parse_events(raw: dict) -> list[MatchEvent]:
    events = [
        MatchEvent(
            minute=int(e.get("minute", 0)),
            type=str(e.get("type", "")),
            player=str(e.get("player", "")),
            team=str(e.get("team", "")),
        )
        for e in raw.get("events", [])
    ]
    return sorted(events, key=lambda e: e.minute)


def parse_standings(raw: dict) -> dict[str, list[Standing]]:
    table: dict[str, list[Standing]] = {}
    for group in raw.get("groups", []):
        rows = [
            Standing(
                team=s.get("team", {}).get("name", ""),
                played=int(s.get("played", 0)),
                won=int(s.get("won", 0)),
                drawn=int(s.get("drawn", 0)),
                lost=int(s.get("lost", 0)),
                goal_diff=int(s.get("goalDifference", 0)),
                points=int(s.get("points", 0)),
            )
            for s in group.get("standings", [])
        ]
        table[group.get("name", "")] = rows
    return table
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_live_models.py -v`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add src/data/live/models.py tests/test_live_models.py
git commit -m "feat: parse Highlightly JSON into LiveMatch/MatchEvent/Standing models"
```

### Task 7: Venue/team reconciliation (Highlightly names → our static names)

**Files:**
- Create: `src/data/live/reconcile.py`
- Test: `tests/test_live_reconcile.py`

- [ ] **Step 1: Write the failing test**

```python
from __future__ import annotations

from src.data.live.reconcile import normalize, match_venue


def test_normalize_strips_and_lowercases():
    assert normalize("  Dallas  Stadium ") == "dallas stadium"


def test_match_venue_exact():
    known = ["Dallas Stadium", "Los Angeles Stadium"]
    assert match_venue("dallas stadium", known) == "Dallas Stadium"


def test_match_venue_unknown_returns_none():
    assert match_venue("Wembley", ["Dallas Stadium"]) is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_live_reconcile.py -v`
Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Write minimal implementation**

```python
from __future__ import annotations


def normalize(name: str) -> str:
    """Lowercase and collapse internal whitespace for stable matching."""
    return " ".join(name.strip().lower().split())


def match_venue(api_venue: str, known_venues: list[str]) -> str | None:
    """Map a Highlightly venue name to one of our static stadium names.

    Exact (normalized) match only; returns None when there is no match so the
    caller falls back to static data rather than guessing.
    """
    target = normalize(api_venue)
    for known in known_venues:
        if normalize(known) == target:
            return known
    return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_live_reconcile.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add src/data/live/reconcile.py tests/test_live_reconcile.py
git commit -m "feat: venue name reconciliation between Highlightly and static data"
```

### Task 8: LiveDataService — caching, adaptive cadence, snapshot, static fallback

**Files:**
- Create: `src/data/live/service.py`
- Test: `tests/test_live_service.py`

- [ ] **Step 1: Write the failing test**

```python
from __future__ import annotations

from src.data.live.models import LiveMatch, MatchState
from src.data.live.service import LiveDataService


class _FakeClient:
    def __init__(self):
        self.match_calls = 0

    def matches(self, date, league_id):
        self.match_calls += 1
        return {"data": [{
            "id": 1, "homeTeam": {"name": "Brazil"}, "awayTeam": {"name": "Mexico"},
            "venue": {"name": "Dallas Stadium"},
            "state": {"description": "Second Half", "clock": 67,
                      "score": {"current": "2 - 1"}},
        }]}

    def standings(self, league_id, season):
        return {"groups": []}


class _BoomClient:
    def matches(self, date, league_id):
        raise RuntimeError("network down")

    def standings(self, league_id, season):
        raise RuntimeError("network down")


def test_snapshot_marks_any_live_and_shapes_matches():
    svc = LiveDataService(_FakeClient(), known_venues=["Dallas Stadium"])
    snap = svc.snapshot(date="2026-06-13", now=0.0)
    assert snap["any_live"] is True
    assert snap["matches"][0]["home"] == "Brazil"
    assert snap["matches"][0]["venue"] == "Dallas Stadium"
    assert snap["matches"][0]["state"] == MatchState.LIVE.value


def test_matches_are_cached_within_ttl():
    client = _FakeClient()
    svc = LiveDataService(client, known_venues=["Dallas Stadium"])
    svc.snapshot(date="2026-06-13", now=0.0)
    svc.snapshot(date="2026-06-13", now=30.0)   # within 60s TTL
    assert client.match_calls == 1
    svc.snapshot(date="2026-06-13", now=90.0)   # past TTL
    assert client.match_calls == 2


def test_snapshot_falls_back_on_error():
    svc = LiveDataService(_BoomClient(), known_venues=[])
    snap = svc.snapshot(date="2026-06-13", now=0.0)
    assert snap["any_live"] is False
    assert snap["matches"] == []
    assert snap["ok"] is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_live_service.py -v`
Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Write minimal implementation**

```python
from __future__ import annotations

from src.data.live import models
from src.data.live.reconcile import match_venue

LEAGUE_ID = 1635
SEASON = 2026
_MATCHES_TTL = 60.0
_STANDINGS_TTL = 3600.0


class LiveDataService:
    """Caches Highlightly responses and builds a JSON-serializable snapshot.

    On any client error the snapshot reports ok=False with empty payloads, so
    UI callbacks fall back to static data.
    """

    def __init__(self, client, known_venues: list[str],
                 league_id: int = LEAGUE_ID, season: int = SEASON) -> None:
        self._client = client
        self._known_venues = known_venues
        self._league_id = league_id
        self._season = season
        self._cache: dict[str, tuple[float, object]] = {}
        self._last_good: dict | None = None

    def _cached(self, key: str, ttl: float, now: float, fetch):
        hit = self._cache.get(key)
        if hit and (now - hit[0]) < ttl:
            return hit[1]
        value = fetch()
        self._cache[key] = (now, value)
        return value

    def snapshot(self, date: str, now: float) -> dict:
        try:
            raw_matches = self._cached(
                "matches", _MATCHES_TTL, now,
                lambda: self._client.matches(date=date, league_id=self._league_id),
            )
            raw_standings = self._cached(
                "standings", _STANDINGS_TTL, now,
                lambda: self._client.standings(
                    league_id=self._league_id, season=self._season),
            )
            rows = raw_matches.get("data", raw_matches)
            matches = [models.parse_match(r) for r in rows]
            payload = {
                "ok": True,
                "any_live": any(m.is_live for m in matches),
                "matches": [self._match_dict(m) for m in matches],
                "standings": {
                    name: [vars(s) for s in table]
                    for name, table in models.parse_standings(raw_standings).items()
                },
            }
            self._last_good = payload
            return payload
        except Exception:
            if self._last_good is not None:
                return {**self._last_good, "ok": False}
            return {"ok": False, "any_live": False, "matches": [], "standings": {}}

    def _match_dict(self, m: models.LiveMatch) -> dict:
        venue = match_venue(m.venue, self._known_venues) or m.venue
        return {
            "match_id": m.match_id,
            "home": m.home,
            "away": m.away,
            "venue": venue,
            "state": m.state.value,
            "clock": m.clock,
            "home_score": m.home_score,
            "away_score": m.away_score,
            "is_live": m.is_live,
        }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_live_service.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add src/data/live/service.py tests/test_live_service.py
git commit -m "feat: LiveDataService with TTL cache, adaptive any_live flag, static fallback"
```

---

## Phase 3 — WebSocket feed wiring

### Task 9: Live store + service instantiation + no-key mode

**Files:**
- Modify: `app.py` (after the existing repository instantiation block, ~line 55)

- [ ] **Step 1: Instantiate the service from the environment**

Add near the other repository setup in `app.py`:

```python
import os
from src.data.live.client import HighlightlyClient
from src.data.live.service import LiveDataService

_API_KEY = os.environ.get("HIGHLIGHTLY_API_KEY")
KNOWN_VENUES = [v.stadium for v in VENUES]  # generic FIFA stadium names
LIVE = (
    LiveDataService(HighlightlyClient(api_key=_API_KEY), known_venues=KNOWN_VENUES)
    if _API_KEY else None
)
```

> If `LIVE` is `None` (no key) the app runs in pure-static mode. Confirm the `.stadium`
> attribute name against `build_venues` output; adjust if the venue object uses a different
> field for the FIFA stadium name.

- [ ] **Step 2: Add the live store to the layout**

In `src/components/layout.py`, add a `dcc.Store(id="live-store", data={"ok": False, "any_live": False, "matches": [], "standings": {}})` to the top-level layout container (alongside any existing stores). If `layout.py` builds the layout via a function, add the store to the returned children list.

- [ ] **Step 3: Smoke-test boot with and without the key**

Run: `python app.py` (no key set) → app boots, static mode, no error.
Run: `HIGHLIGHTLY_API_KEY=$HIGHLIGHTLY_API_KEY python app.py` → app boots, `LIVE` is a service.
Expected: both boot; the `live-store` is present in the DOM.

- [ ] **Step 4: Commit**

```bash
git add app.py src/components/layout.py
git commit -m "feat: instantiate LiveDataService + live-store, with no-key static mode"
```

### Task 10: Persistent WebSocket callback that pushes snapshots

**Files:**
- Modify: `app.py` (with the other callbacks)
- Test: `tests/test_live_feed.py`

- [ ] **Step 1: Write the failing test for the cadence helper**

> The async loop itself is integration-tested by running the app; the testable unit is the
> pure cadence decision. Put it in `service.py` and test it.

```python
from __future__ import annotations

from src.data.live.service import next_delay


def test_next_delay_fast_when_live():
    assert next_delay({"any_live": True}) == 60


def test_next_delay_slow_when_idle():
    assert next_delay({"any_live": False}) == 1800
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_live_feed.py -v`
Expected: FAIL — `ImportError: cannot import name 'next_delay'`.

- [ ] **Step 3: Add the cadence helper to `service.py`**

```python
def next_delay(snapshot: dict) -> int:
    """Adaptive poll cadence: fast while any match is live, slow when idle."""
    return 60 if snapshot.get("any_live") else 1800
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_live_feed.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Add the persistent callback to `app.py`**

```python
import asyncio
from datetime import date as _date
from dash import callback, ctx, set_props
from src.data.live.service import next_delay

if LIVE is not None:
    @callback(persistent=True)
    async def live_feed():
        ws = ctx.websocket
        if ws is None:
            return
        while not ws.is_shutdown:
            try:
                snap = await asyncio.to_thread(
                    LIVE.snapshot, _date.today().isoformat(), asyncio.get_event_loop().time()
                )
            except Exception:
                snap = {"ok": False, "any_live": False, "matches": [], "standings": {}}
            set_props("live-store", {"data": snap})
            await asyncio.sleep(next_delay(snap))
```

- [ ] **Step 6: Integration-check the push**

Run: `HIGHLIGHTLY_API_KEY=$HIGHLIGHTLY_API_KEY python app.py`, open the app, open browser devtools → confirm a websocket connection is established and `live-store` data updates (inspect via a temporary `html.Pre(id=...)` bound to the store, or the Dash callback graph).
Expected: store populates within a few seconds; no "No supported WebSocket library detected" in server logs (that message means `uvicorn[standard]` is missing).

- [ ] **Step 7: Commit**

```bash
git add app.py src/data/live/service.py tests/test_live_feed.py
git commit -m "feat: persistent websocket callback pushes live snapshot to store"
```

---

## Phase 4 — UI surfaces (all render from live-store via ordinary HTTP callbacks)

### Task 11: Group tables read live standings, fall back to static

**Files:**
- Modify: `src/components/group_table.py` (the `build_group_panel` / `group_rows` functions)
- Test: `tests/test_group_table.py` (extend)

- [ ] **Step 1: Write the failing test**

```python
def test_group_rows_prefer_live_standings():
    from src.components.group_table import group_rows
    live = {"Group A": [
        {"team": "Brazil", "played": 2, "won": 2, "drawn": 0, "lost": 0,
         "goal_diff": 4, "points": 6}]}
    rows = group_rows("Group A", groups=None, live_standings=live)
    assert rows[0]["team"] == "Brazil"
    assert rows[0]["points"] == 6
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_group_table.py::test_group_rows_prefer_live_standings -v`
Expected: FAIL — `group_rows` does not accept `live_standings`.

- [ ] **Step 3: Add the live-standings branch**

Update `group_rows` to accept `live_standings: dict | None = None`; when it contains the requested group, build rows from it; otherwise use the existing static `groups` path. Keep the existing static behavior unchanged when `live_standings` is `None` or empty.

- [ ] **Step 4: Add the callback in `app.py`**

```python
@callback(
    Output("group-panel", "children"),
    Input("live-store", "data"),
    Input("selected-group", "data"),   # existing selection signal
)
def render_group_panel(live, selected):
    standings = (live or {}).get("standings") or None
    return build_group_panel(selected, GROUPS, live_standings=standings)
```

> Match the real Output/Input ids to those already in `app.py`; this shows the wiring shape.

- [ ] **Step 5: Run tests**

Run: `pytest tests/test_group_table.py -v`
Expected: PASS (new + existing).

- [ ] **Step 6: Commit**

```bash
git add src/components/group_table.py tests/test_group_table.py app.py
git commit -m "feat: group tables overlay live standings with static fallback"
```

### Task 12: Map markers show LIVE badge + score

**Files:**
- Modify: `src/components/map_view.py` (the `pulse_markers` / `filter_pin` functions)
- Test: `tests/test_map_view.py` (extend)

- [ ] **Step 1: Write the failing test**

```python
def test_live_match_for_venue_returns_score():
    from src.components.map_view import live_match_for_venue
    live = {"matches": [{"venue": "Dallas Stadium", "is_live": True,
                         "home": "Brazil", "away": "Mexico",
                         "home_score": 2, "away_score": 1, "match_id": 42}]}
    m = live_match_for_venue("Dallas Stadium", live)
    assert m["match_id"] == 42
    assert m["home_score"] == 2


def test_live_match_for_venue_none_when_absent():
    from src.components.map_view import live_match_for_venue
    assert live_match_for_venue("Dallas Stadium", {"matches": []}) is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_map_view.py -k live_match_for_venue -v`
Expected: FAIL — function not defined.

- [ ] **Step 3: Implement the helper + marker enrichment**

```python
def live_match_for_venue(venue: str, live: dict | None) -> dict | None:
    """The live match at this venue, or None. Pure lookup for testability."""
    for m in (live or {}).get("matches", []):
        if m.get("venue") == venue and m.get("is_live"):
            return m
    return None
```

Then in `pulse_markers` (or wherever markers are built), accept an optional `live` dict and, when `live_match_for_venue` returns a match, add a LIVE badge + `"{home_score}-{away_score}"` to the marker tooltip/icon and tag the marker id with the `match_id` so it is clickable.

- [ ] **Step 4: Add/extend the callback in `app.py`**

Make the existing marker-rendering callback take `Input("live-store", "data")` and pass it to `pulse_markers(..., live=live)`.

- [ ] **Step 5: Run tests**

Run: `pytest tests/test_map_view.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/components/map_view.py tests/test_map_view.py app.py
git commit -m "feat: live LIVE badge + score on map markers"
```

### Task 13: Bottom live strip component

**Files:**
- Create: `src/components/live_strip.py`
- Test: `tests/test_live_strip.py`
- Modify: `src/components/layout.py` (mount the strip at the bottom), `app.py` (callback)

- [ ] **Step 1: Fetch the DMC API for the components used**

Use context7 (`resolve-library-id` → `query-docs` for `dash-mantine-components`) to confirm the current API of the components you'll use (e.g. `dmc.Group`, `dmc.Paper`, `dmc.Badge`, `dmc.Text`). Do this before writing the component.

- [ ] **Step 2: Write the failing test**

```python
from __future__ import annotations

from src.components.live_strip import strip_items


def test_strip_items_one_per_match():
    live = {"matches": [
        {"match_id": 1, "home": "Brazil", "away": "Mexico",
         "home_score": 2, "away_score": 1, "state": "live", "is_live": True},
        {"match_id": 2, "home": "USA", "away": "Canada",
         "home_score": None, "away_score": None, "state": "scheduled",
         "is_live": False},
    ]}
    items = strip_items(live)
    assert len(items) == 2
    # Each clickable item carries its match_id for the modal trigger.
    ids = [it["props"]["id"]["index"] for it in items]
    assert ids == [1, 2]


def test_strip_items_empty_when_no_matches():
    assert strip_items({"matches": []}) == []
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/test_live_strip.py -v`
Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 4: Implement `strip_items` + `build_live_strip`**

```python
from __future__ import annotations

import dash_mantine_components as dmc
from dash import html


def _score(m: dict) -> str:
    if m.get("home_score") is None:
        return "vs"
    return f"{m['home_score']} - {m['away_score']}"


def strip_items(live: dict | None) -> list:
    """One clickable item per match. Pattern-matching id carries match_id."""
    items = []
    for m in (live or {}).get("matches", []):
        items.append(
            html.Div(
                id={"type": "live-strip-item", "index": m["match_id"]},
                n_clicks=0,
                children=dmc.Paper(
                    dmc.Group([
                        dmc.Badge("LIVE", color="red") if m.get("is_live")
                        else dmc.Badge(m.get("state", ""), color="gray"),
                        dmc.Text(f"{m['home']} {_score(m)} {m['away']}", size="sm"),
                    ]),
                    withBorder=True, p="xs",
                ),
                style={"cursor": "pointer"},
            )
        )
    return items


def build_live_strip(live: dict | None):
    return dmc.Group(strip_items(live), id="live-strip", wrap="nowrap",
                     style={"overflowX": "auto"})
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_live_strip.py -v`
Expected: PASS (2 passed).

- [ ] **Step 6: Mount + wire**

Add `build_live_strip(None)` to the bottom of the layout in `layout.py`. In `app.py`:

```python
@callback(Output("live-strip", "children"), Input("live-store", "data"))
def render_live_strip(live):
    return strip_items(live)
```

- [ ] **Step 7: Commit**

```bash
git add src/components/live_strip.py tests/test_live_strip.py src/components/layout.py app.py
git commit -m "feat: bottom live strip of today's matches"
```

### Task 14: Live-match detail modal

**Files:**
- Create: `src/components/live_match_modal.py`
- Test: `tests/test_live_match_modal.py`
- Modify: `app.py` (open-on-click callback)

- [ ] **Step 1: Fetch the DMC Modal API via context7**

Confirm the current `dmc.Modal` props (`opened`, `title`, `size`, children) before building.

- [ ] **Step 2: Write the failing test**

```python
from __future__ import annotations

from src.components.live_match_modal import modal_body


def test_modal_body_renders_score_and_state():
    m = {"home": "Brazil", "away": "Mexico", "home_score": 2, "away_score": 1,
         "state": "live", "clock": 67}
    body = modal_body(m, events=[{"minute": 67, "type": "Goal",
                                  "player": "Neymar", "team": "Brazil"}])
    text = str(body)
    assert "Brazil" in text and "Mexico" in text
    assert "2" in text and "1" in text


def test_modal_body_handles_missing_match():
    assert modal_body(None, events=[]) is not None
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/test_live_match_modal.py -v`
Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 4: Implement `modal_body` + `build_modal`**

```python
from __future__ import annotations

import dash_mantine_components as dmc
from dash import html


def modal_body(match: dict | None, events: list[dict]):
    if not match:
        return dmc.Text("No match selected.")
    header = dmc.Group([
        dmc.Title(f"{match['home']} {match.get('home_score', '')} - "
                  f"{match.get('away_score', '')} {match['away']}", order=3),
        dmc.Badge(match.get("state", ""), color="red"
                  if match.get("state") == "live" else "gray"),
    ])
    timeline = dmc.Stack([
        dmc.Text(f"{e['minute']}' {e['type']} — {e['player']} ({e['team']})",
                 size="sm")
        for e in events
    ]) if events else dmc.Text("No events yet.", size="sm")
    return html.Div([header, dmc.Divider(my="sm"), timeline])


def build_modal():
    return dmc.Modal(id="live-match-modal", opened=False, size="lg",
                     children=modal_body(None, []))
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_live_match_modal.py -v`
Expected: PASS (2 passed).

- [ ] **Step 6: Wire the open-on-click callback in `app.py`**

```python
from dash import ALL, Output, Input, State, ctx, no_update

app.layout ...  # ensure build_modal() is mounted in layout.py

@callback(
    Output("live-match-modal", "opened"),
    Output("live-match-modal", "children"),
    Input({"type": "live-strip-item", "index": ALL}, "n_clicks"),
    Input({"type": "live-marker", "index": ALL}, "n_clicks"),
    State("live-store", "data"),
    prevent_initial_call=True,
)
def open_live_modal(strip_clicks, marker_clicks, live):
    triggered = ctx.triggered_id
    if not triggered or not any((strip_clicks or []) + (marker_clicks or [])):
        return no_update, no_update
    match_id = triggered["index"]
    match = next((m for m in (live or {}).get("matches", [])
                  if m["match_id"] == match_id), None)
    return True, modal_body(match, events=[])
```

> Events for the modal can be fetched on demand in a later iteration; the body already
> renders an empty timeline cleanly. Keep the marker id `{"type": "live-marker", "index": match_id}`
> consistent with Task 12.

- [ ] **Step 7: Mount + commit**

Add `build_modal()` to `layout.py`. Then:

```bash
git add src/components/live_match_modal.py tests/test_live_match_modal.py src/components/layout.py app.py
git commit -m "feat: live-match detail modal opened from strip + map markers"
```

### Task 15: Stadium detail drawer shows the venue's live match

**Files:**
- Modify: `src/components/detail_panel.py` (the `stadium_detail` function)
- Test: `tests/test_detail_panel.py` (extend)

- [ ] **Step 1: Write the failing test**

```python
def test_stadium_detail_includes_live_score(monkeypatch):
    from src.components.detail_panel import stadium_detail
    live = {"matches": [{"venue": "Dallas Stadium", "is_live": True,
                         "home": "Brazil", "away": "Mexico",
                         "home_score": 2, "away_score": 1, "match_id": 42}]}
    # Build with whatever venue object stadium_detail expects; assert the live
    # score string appears in the rendered output.
    out = stadium_detail(venue=_dallas_venue_fixture(), live=live)
    assert "2 - 1" in str(out)
```

> Reuse the existing test's venue fixture helper; if none exists, construct the venue object
> the way the current `stadium_detail` tests do.

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_detail_panel.py -k live_score -v`
Expected: FAIL — `stadium_detail` does not accept `live` / no score shown.

- [ ] **Step 3: Add an optional `live` arg to `stadium_detail`**

Give `stadium_detail(..., live: dict | None = None)` a section that, when `live_match_for_venue` (imported from `map_view`) finds a live match for this venue, renders the score + a button with id `{"type": "live-marker", "index": match_id}` so the drawer can also open the modal. When there is no live match, render the existing static content unchanged.

- [ ] **Step 4: Pass the store into the drawer callback in `app.py`**

Add `Input("live-store", "data")` to the existing stadium-detail callback and forward it as `live=` to `stadium_detail`.

- [ ] **Step 5: Run tests**

Run: `pytest tests/test_detail_panel.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/components/detail_panel.py tests/test_detail_panel.py app.py
git commit -m "feat: stadium drawer shows live match score + modal trigger"
```

---

## Phase 5 — Final verification

### Task 16: Full suite + manual live check

- [ ] **Step 1: Run the entire test suite**

Run: `pytest tests/ -v`
Expected: all green. No network calls in tests (everything uses fakes/fixtures).

- [ ] **Step 2: Manual live verification**

Run: `HIGHLIGHTLY_API_KEY=$HIGHLIGHTLY_API_KEY python app.py`
Confirm: map LIVE badges appear for in-play venues, the bottom strip lists today's matches, clicking a strip item or a live marker opens the modal, the drawer shows the venue's live match, and group tables reflect live standings. With the key unset, the app runs cleanly in static mode.

- [ ] **Step 3: Stop — do NOT merge**

Per the user's instruction, do not merge `feat/highlightly-live-data` into main. Summarize what was built and ask the user to validate before any merge.

---

## Self-review notes

- **Spec coverage:** scores+state (Tasks 6, 12, 13, 14), standings (Tasks 6, 8, 11), events timeline (Tasks 6, 14), confirmed lineups — see note below; adaptive cadence (Tasks 8, 10); static fallback (Tasks 8, 11–15); WebSocket transport (Tasks 2, 10); placement on markers/strip/drawer/modal/group tables (Tasks 11–15); secrets + no-key mode (Task 9); Dash 4.2 migration (Phase 1).
- **Deferred within scope:** Confirmed-lineups *into the formation pitch* and match *statistics/predictions in the modal* are wired structurally (the modal body and store carry the shapes) but their detailed rendering is intentionally left as a fast follow once Task 5 fixtures confirm the exact lineup/statistics JSON. If you want these fully specified now, extend Tasks 6/14 after capturing fixtures. This is called out rather than hidden.
- **Type consistency:** marker click id `{"type": "live-marker", "index": match_id}` is used in Tasks 12, 14, 15; strip id `{"type": "live-strip-item", "index": match_id}` in Tasks 13, 14; `live-store` data shape `{ok, any_live, matches[], standings{}}` is consistent across Tasks 8–15.
