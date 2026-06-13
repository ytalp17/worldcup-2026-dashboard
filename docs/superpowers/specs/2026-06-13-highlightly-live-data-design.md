# Highlightly Live Data Integration — Design

**Date:** 2026-06-13
**Status:** Approved, ready for implementation plan

## Goal

Bring live, up-to-date World Cup 2026 tournament data into the dashboard using the
[Highlightly Football API](http://highlightly.net/football-api/documentation/), layered on
top of the existing static CSV/JSON data without replacing it. Live data covers:

1. **Live scores & match state** (LIVE / HT / FT / ET / pens / scheduled)
2. **Group standings** (auto-update the existing group tables)
3. **Match events timeline** (goals, cards, subs, VAR)
4. **Confirmed lineups** (replace the estimated XI once published)

## Source API

- Base URL: `https://soccer.highlightly.net`
- World Cup 2026 league id: `1635`; season `2026` (both to be confirmed against the live API).
- Auth: API key in env var `HIGHLIGHTLY_API_KEY` (never hardcoded; `.env` gitignored).
- Endpoints used: `GET /matches`, `/matches/{id}`, `/events/{matchId}`, `/lineups/{matchId}`,
  `/standings`, `/statistics/{matchId}`.
- Refresh cadences (upstream): matches ~60s, events ~60s, standings ~1h, lineups ~10m,
  statistics ~5m. Rate limit surfaced via `x-ratelimit-requests-remaining` header.

## Decisions

| Topic | Decision |
|---|---|
| Scope | Live scores+state, standings, events timeline, confirmed lineups |
| Refresh model | Adaptive: poll 60s while any match is in-play, ~30 min when idle |
| Static vs live | **Static is the floor**; live overlays when available; on any failure/quota/empty → silently fall back to static or last-known snapshot |
| Transport | **Dash 4.2 native WebSocket callbacks** — a persistent callback pushes snapshots via `set_props` (see [reference](../../references/dash-websocket-callbacks.md)) |
| Placement | Map markers (live), bottom live strip, stadium detail drawer; live markers + strip items open a detailed live-match **modal**; standings feed group tables; confirmed XI feeds the formation pitch |
| Secrets | `HIGHLIGHTLY_API_KEY` env var; no-key mode runs pure-static so dev/tests work offline |

## Architecture

### Data layer — `src/data/live/` (all network IO isolated here)

- **`HighlightlyClient`** (`client.py`) — the only component doing HTTP. Synchronous (`requests`),
  one method per endpoint (`matches`, `match`, `events`, `lineups`, `standings`). Reads the API
  key from env, handles timeouts/non-200s, reads the rate-limit header. Returns raw dicts.
- **`models.py`** — dataclasses parsed from raw JSON: `LiveMatch`, `MatchState` (enum), `Score`,
  `MatchEvent`, `Standing`, `ConfirmedLineup`. Pure, fixture-tested.
- **`LiveDataService`** (`service.py`) — orchestration + caching. Per-endpoint TTL cache matching
  upstream cadence (matches 60s, events 60s, standings 1h, lineups 10m). Builds one
  JSON-serializable **snapshot** (`{any_live: bool, matches: [...], standings: [...], ...}`).
  On any exception/quota/empty → returns last-known snapshot or empty so callers fall back to
  static. This is the seam a future transport swap would touch.
- **`reconcile.py`** — maps Highlightly matches → static venues (by venue/city) and Highlightly
  team names → CSV team names. Explicit mapping table + normalization. Isolated and tested
  (the main integration risk).

### Transport — persistent WebSocket callback

App constructed as `Dash(backend="fastapi", websocket_callbacks=True)`. One persistent callback:

```python
@callback(persistent=True)
async def live_feed():
    ws = ctx.websocket
    while not ws.is_shutdown:
        snapshot = await asyncio.to_thread(LIVE.snapshot)   # blocking requests off the loop
        set_props("live-store", {"data": snapshot})
        await asyncio.sleep(60 if snapshot["any_live"] else 1800)
```

- Service stays synchronous; the loop wraps it in `asyncio.to_thread`.
- Pushes to `dcc.Store(id="live-store")`. **All rendering stays in ordinary HTTP callbacks**
  that read the Store — keeps views unit-testable; only the feed is WebSocket.

### UI surfaces (all read from `live-store`)

- **Map markers** — pulsing LIVE badge + score for stadiums hosting a live match (extends
  `map_view.py`).
- **Bottom live strip** — new `src/components/live_strip.py`, cycles today's matches, clickable.
- **Stadium detail drawer** — `detail_panel.py` extended with the venue's live/next/recent match
  + events timeline.
- **Live-match modal** — new `src/components/live_match_modal.py` (DMC Modal): score, clock/state,
  events timeline, statistics, confirmed XI, predictions. Opened by clicking a live marker or a
  live-strip item (pattern-matching callback keyed on match id).
- **Group tables** — `group_table.py` reads standings from the Store when present, else static.

DMC component APIs fetched via context7 before building (per CLAUDE.md).

## Migration cost & risk (Dash 2.18.1 → 4.2)

Sequenced **first** in the plan so we fail fast:

1. `requirements.txt`: `dash[fastapi]>=4.2` + `uvicorn[standard]` (+ `requirements-dev.txt` async test deps).
2. **DMC 2.4.0 vs Dash 4.2** — verify; the `_set_react_version("18.2.0")` hack in `app.py` likely
   becomes unnecessary (Dash 4 defaults to React 18) and may need removing.
3. **dash-leaflet 1.0.11 vs Dash 4.2** — verify the map still renders (it is the heart of the app).
4. **Run/e2e** — dev uses `app.run(debug=True)`; production `uvicorn app:app.server`. Framework-3.11
   e2e env needs `uvicorn[standard]`.

## Testing (TDD, fully offline)

- **Client** — mocked HTTP (incl. quota-exhausted / error paths).
- **Models** — parse saved fixture JSON → typed objects.
- **Service** — cache TTL behavior, adaptive-cadence decision (`any_live`), fallback-to-static
  via a fake client.
- **Reconcile** — name/venue mapping correctness.
- **Components** — render from a fixture snapshot (no network) + static-fallback render when the
  snapshot is empty.
- **Persistent loop** — thin integration check (not heavy unit tests), given it's async.
- Real API responses captured once into `tests/fixtures/live/`.

## Out of scope (YAGNI)

Highlights video grid, odds/bookmakers, players profiles, box scores, head-to-head — not in this
phase. The client is structured so they can be added later.
