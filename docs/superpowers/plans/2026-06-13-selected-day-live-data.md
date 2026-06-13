# Selected-Day Live Data — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Make the calendar span the tournament from June 11, drive the bottom strip + modal from the selected calendar day (incl. finished games), and make every stadium-drawer match a clickable link to the modal.

**Architecture:** Add per-day and by-id fetch methods to `LiveDataService`; the strip uses `live-store` for today and `matches_on(day)` otherwise; the modal fetches the match header by id; the drawer resolves each scheduled match to its API id via a pure pair-index helper.

**Tech Stack:** Python 3.11 (env `wc2026-live`), Dash 4.2 (FastAPI), dash-mantine-components, pandas, pytest.

**Branch:** feat/highlightly-live-data. **Do NOT merge to main.**

**ENV (all tasks):** test/run with `/Users/yberber/anaconda3/envs/wc2026-live/bin/python`. Work from `/Users/yberber/Documents/WC2026`. `from __future__ import annotations` is the first line of every src file.

---

## Task 1: Calendar starts at the earliest match date, defaults to today

**Files:**
- Modify: `src/data/match_calendar.py` (the `start` property + new `default_day`)
- Modify: `src/components/header_calendar.py` (`build_match_calendar`)
- Test: `tests/test_match_calendar.py`, `tests/test_header_calendar.py`

- [ ] **Step 1: Write the failing test** (add to `tests/test_match_calendar.py`)

```python
def test_start_is_earliest_match_date_not_today():
    from datetime import date, time, datetime
    from src.data.matches import Match
    from src.data.match_calendar import MatchCalendar
    def m(num, d, stadium="Dallas Stadium"):
        return Match(number=num, home="A", away="B", group="G", stage="Group Stage",
                     stadium=stadium, date=d, local_time=time(12, 0),
                     kickoff_utc=datetime(d.year, d.month, d.day, 18, 0))
    matches = [m(1, date(2026, 6, 11)), m(2, date(2026, 6, 20))]
    cal = MatchCalendar(matches, {"Dallas Stadium": "Dallas"}, today=date(2026, 6, 13))
    assert cal.start == date(2026, 6, 11)           # earliest, not today
    assert cal.end == date(2026, 6, 20)
    assert cal.default_day == date(2026, 6, 13)     # today, in range

def test_default_day_clamped_into_range():
    from datetime import date, time, datetime
    from src.data.matches import Match
    from src.data.match_calendar import MatchCalendar
    def m(num, d):
        return Match(number=num, home="A", away="B", group="G", stage="Group Stage",
                     stadium="Dallas Stadium", date=d, local_time=time(12, 0),
                     kickoff_utc=datetime(d.year, d.month, d.day, 18, 0))
    matches = [m(1, date(2026, 6, 11)), m(2, date(2026, 6, 20))]
    # today before the tournament -> clamp to start
    cal = MatchCalendar(matches, {"Dallas Stadium": "Dallas"}, today=date(2026, 6, 1))
    assert cal.default_day == date(2026, 6, 11)
```

- [ ] **Step 2: Run → FAIL**

Run: `/Users/yberber/anaconda3/envs/wc2026-live/bin/python -m pytest tests/test_match_calendar.py -k "start_is_earliest or default_day_clamped" -v`
Expected: FAIL (`start` returns today; no `default_day`).

- [ ] **Step 3: Implement** in `src/data/match_calendar.py`

In `__init__`, after building `_cities_by_date`, also compute the earliest date:
```python
        self._start = min(self._cities_by_date) if self._cities_by_date else today
```
Replace the `start` property and add `default_day`:
```python
    @property
    def start(self) -> date:
        return self._start

    @property
    def default_day(self) -> date:
        """Today, clamped into [start, end] — the day selected on load."""
        if self._today < self._start:
            return self._start
        if self._today > self._end:
            return self._end
        return self._today
```
(Keep `_today`, `end`, `match_dates`, `active_cities` as-is.)

- [ ] **Step 4: Update `build_match_calendar`** in `src/components/header_calendar.py`

```python
def build_match_calendar(calendar: MatchCalendar) -> dmc.MiniCalendar:
    """Compact header calendar spanning the opening day → the final day. Opens on
    today (clamped); users can scroll back for past days. Selecting a date drives
    the map highlight + the bottom strip in app.py."""
    return dmc.MiniCalendar(
        id=CALENDAR_ID,
        value=calendar.default_day.isoformat(),
        defaultDate=calendar.default_day.isoformat(),
        minDate=calendar.start.isoformat(),
        maxDate=(calendar.end + timedelta(days=1)).isoformat(),
        numberOfDays=CALENDAR_DAYS,
        persistence=True,
    )
```

- [ ] **Step 5: Run tests → PASS**

Run: `/Users/yberber/anaconda3/envs/wc2026-live/bin/python -m pytest tests/test_match_calendar.py tests/test_header_calendar.py -v`
Expected: PASS. If a `test_header_calendar.py` assertion hard-codes `minDate == today` or `value == start`, update it to the new behavior (minDate = earliest date; value = default_day).

- [ ] **Step 6: Commit**

```bash
git add src/data/match_calendar.py src/components/header_calendar.py tests/test_match_calendar.py tests/test_header_calendar.py
git commit -m "feat: calendar spans tournament from opening day, defaults to today"
```

---

## Task 2: Service — `matches_on` (per day) and `match_summary` (by id)

**Files:**
- Modify: `src/data/live/service.py`
- Test: `tests/test_live_service.py`

- [ ] **Step 1: Write the failing test** (add to `tests/test_live_service.py`; reuses `_FakeClient`/`_index`/`_BoomClient` already in this file)

```python
def test_matches_on_returns_day_match_dicts_and_caches():
    client = _FakeClient()           # its .matches(date, league_id) returns the 2-match payload
    svc = LiveDataService(client, _index())
    out = svc.matches_on("2026-06-12", now=0.0)
    assert {m["home"] for m in out} == {"USA", "Brazil"}
    svc.matches_on("2026-06-12", now=10.0)        # cached
    assert client.match_calls == 1
    svc.matches_on("2026-06-13", now=20.0)        # different date -> new fetch
    assert client.match_calls == 2

def test_matches_on_empty_on_error():
    svc = LiveDataService(_BoomClient(), _index())
    assert svc.matches_on("2026-06-12", now=0.0) == []

def test_match_summary_parses_detail_and_caches():
    class _C(_FakeClient):
        def __init__(self):
            super().__init__(); self.detail_calls = 0
        def match(self, match_id):
            self.detail_calls += 1
            return [{"id": match_id, "homeTeam": {"name": "USA"},
                     "awayTeam": {"name": "Paraguay"},
                     "state": {"description": "Finished", "clock": 90,
                               "score": {"current": "4 - 1"}}}]
    c = _C()
    svc = LiveDataService(c, _index())
    s = svc.match_summary(1267454654, now=0.0)
    assert s["home"] == "USA" and s["home_score"] == 4 and s["state"] == "finished"
    svc.match_summary(1267454654, now=5.0)        # cached
    assert c.detail_calls == 1

def test_match_summary_none_on_error():
    svc = LiveDataService(_BoomClient(), _index())
    assert svc.match_summary(1, now=0.0) is None
```
Note: ensure `_FakeClient.matches(self, date, league_id)` ignores `date` (returns the same 2 matches) — it already does. If `_BoomClient` lacks `match`, the AttributeError is caught → None (acceptable).

- [ ] **Step 2: Run → FAIL**

Run: `/Users/yberber/anaconda3/envs/wc2026-live/bin/python -m pytest tests/test_live_service.py -k "matches_on or match_summary" -v`
Expected: FAIL (methods missing).

- [ ] **Step 3: Implement** in `src/data/live/service.py`

Add a constant near the others: `_MATCHES_ON_TTL = 600.0`. Add methods to `LiveDataService` (reuse `_cached`, `models`, `self._match_dict`):
```python
    def matches_on(self, date_iso: str, now: float) -> list[dict]:
        """Match dicts for one calendar day (same shape as snapshot 'matches').
        Cached per date; [] on error."""
        try:
            raw = self._cached(
                f"matches:{date_iso}", _MATCHES_ON_TTL, now,
                lambda: self._client.matches(date=date_iso, league_id=self._league_id))
            return [self._match_dict(m) for m in models.parse_matches(raw)]
        except Exception:
            logger.exception("Live matches_on fetch failed for %s", date_iso)
            return []

    def match_summary(self, match_id: int, now: float) -> dict | None:
        """One match's header dict from the detail endpoint (bare list of one).
        Cached; None on error."""
        try:
            raw = self._cached(
                f"summary:{match_id}", _MATCHES_ON_TTL, now,
                lambda: self._client.match(match_id))
            rows = raw if isinstance(raw, list) else [raw]
            if not rows:
                return None
            return self._match_dict(models.parse_match(rows[0]))
        except Exception:
            logger.exception("Live match_summary fetch failed for %s", match_id)
            return None
```

- [ ] **Step 4: Run → PASS**

Run: `/Users/yberber/anaconda3/envs/wc2026-live/bin/python -m pytest tests/test_live_service.py -v`
Expected: PASS (new + existing).

- [ ] **Step 5: Commit**

```bash
git add src/data/live/service.py tests/test_live_service.py
git commit -m "feat: LiveDataService.matches_on (per day) + match_summary (by id)"
```

---

## Task 3: `index_matches_by_pair` reconcile helper

**Files:**
- Modify: `src/data/live/reconcile.py`
- Test: `tests/test_live_reconcile.py`

- [ ] **Step 1: Write the failing test** (add to `tests/test_live_reconcile.py`)

```python
def test_index_matches_by_pair_keys_on_canonical_names():
    from src.data.live.reconcile import index_matches_by_pair
    api_matches = [
        {"match_id": 11, "home": "USA", "away": "Paraguay"},
        {"match_id": 22, "home": "South Korea", "away": "Czech Republic"},
    ]
    idx = index_matches_by_pair(api_matches)
    assert idx[("usa", "paraguay")] == 11
    # static names "Korea Republic"/"Czechia" canonicalize to the API spellings
    from src.data.live.reconcile import canonical_team
    assert idx[(canonical_team("Korea Republic"), canonical_team("Czechia"))] == 22
```

- [ ] **Step 2: Run → FAIL**

Run: `/Users/yberber/anaconda3/envs/wc2026-live/bin/python -m pytest tests/test_live_reconcile.py -k index_matches_by_pair -v`
Expected: FAIL (function missing).

- [ ] **Step 3: Implement** in `src/data/live/reconcile.py`

```python
def index_matches_by_pair(api_matches, aliases: dict[str, str] = TEAM_ALIASES) -> dict[tuple[str, str], int]:
    """{(canonical_home, canonical_away): match_id} for API match dicts, so a
    static schedule match can be resolved to its API id by team pair."""
    return {
        (canonical_team(m["home"], aliases), canonical_team(m["away"], aliases)): m["match_id"]
        for m in api_matches
        if m.get("home") and m.get("away") and m.get("match_id") is not None
    }
```
Note: the alias table maps `"czech republic" -> "czechia"`? Check `TEAM_ALIASES`: it currently has `"czech republic": "czechia"`. The API uses "Czech Republic"; static uses "Czechia". `canonical_team("Czech Republic")` → "czechia"; `canonical_team("Czechia")` → "czechia". Both sides agree → lookup works. Same for "South Korea"→"korea republic" alias. The test relies on these existing alias entries — if an entry is missing add it to `TEAM_ALIASES`.

- [ ] **Step 4: Run → PASS**

Run: `/Users/yberber/anaconda3/envs/wc2026-live/bin/python -m pytest tests/test_live_reconcile.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/data/live/reconcile.py tests/test_live_reconcile.py
git commit -m "feat: index_matches_by_pair to resolve static matches to API ids"
```

---

## Task 4: Strip follows the selected calendar day

**Files:**
- Create: `tests/test_strip_day.py`
- Modify: `app.py` (`render_live_strip` + a pure helper)

- [ ] **Step 1: Write the failing test** (`tests/test_strip_day.py`)

```python
from __future__ import annotations
from datetime import date
from app import strip_day_matches  # pure helper

def test_today_uses_live_store():
    live = {"matches": [{"match_id": 1, "home": "A", "away": "B"}]}
    out = strip_day_matches("2026-06-13", date(2026, 6, 13), live, lambda d: [{"x": d}])
    assert out == live["matches"]          # today -> live-store matches

def test_other_day_uses_fetcher():
    out = strip_day_matches("2026-06-12", date(2026, 6, 13), {"matches": []},
                            lambda d: [{"match_id": 9, "day": d}])
    assert out == [{"match_id": 9, "day": "2026-06-12"}]

def test_no_fetcher_other_day_empty():
    assert strip_day_matches("2026-06-12", date(2026, 6, 13), {}, None) == []

def test_bad_selected_date_falls_back_to_live():
    live = {"matches": [{"match_id": 1}]}
    assert strip_day_matches(None, date(2026, 6, 13), live, lambda d: [{"z": 1}]) == live["matches"]
```

- [ ] **Step 2: Run → FAIL**

Run: `/Users/yberber/anaconda3/envs/wc2026-live/bin/python -m pytest tests/test_strip_day.py -v`
Expected: FAIL (`strip_day_matches` missing).

- [ ] **Step 3: Implement** in `app.py`

Add the pure helper near the other payload helpers:
```python
def strip_day_matches(selected_date, today, live, matches_on):
    """Match dicts for the strip on the selected day. Today -> the live-store
    matches (auto-updating); any other valid day -> matches_on(day); when the
    fetcher is None (no key) or the date is unparseable -> the live-store matches."""
    from datetime import date as _date
    if selected_date:
        try:
            day = _date.fromisoformat(selected_date)
        except (ValueError, TypeError):
            day = today
        if day != today and matches_on is not None:
            return matches_on(selected_date)
    return (live or {}).get("matches", [])
```
Update `render_live_strip`:
```python
@callback(
    Output("live-strip", "children"),
    Input("match-calendar", "value"),
    Input("live-store", "data"),
)
def render_live_strip(selected_date, live):
    fetch = (lambda d: LIVE.matches_on(d, time.monotonic())) if LIVE is not None else None
    matches = strip_day_matches(selected_date, date.today(), live, fetch)
    return strip_items({"matches": matches})
```
(`time`, `date`, `LIVE`, `strip_items` are already imported/defined in app.py.)

- [ ] **Step 4: Run → PASS + import check**

Run: `/Users/yberber/anaconda3/envs/wc2026-live/bin/python -m pytest tests/test_strip_day.py -v`
Then: `/Users/yberber/anaconda3/envs/wc2026-live/bin/python -c "import app; print('app OK')"`
Expected: PASS; app imports.

- [ ] **Step 5: Commit**

```bash
git add app.py tests/test_strip_day.py
git commit -m "feat: bottom strip reflects the selected calendar day (live today, fetched otherwise)"
```

---

## Task 5: Decouple modal-open from live-store (use match_summary)

**Files:**
- Modify: `app.py` (`open_live_modal`)

- [ ] **Step 1: Update `open_live_modal`** in `app.py`

Replace the live-store match lookup with a by-id summary fetch so past/selected-day matches render:
```python
@callback(
    Output("live-match-modal", "opened"),
    Output("live-match-modal", "children"),
    Input({"type": "live-strip-item", "index": ALL}, "n_clicks"),
    Input({"type": "open-live-modal", "index": ALL}, "n_clicks"),
    prevent_initial_call=True,
)
def open_live_modal(strip_clicks, drawer_clicks):
    clicks = (strip_clicks or []) + (drawer_clicks or [])
    if not any(c for c in clicks if c):
        return no_update, no_update
    triggered = ctx.triggered_id
    if not isinstance(triggered, dict):
        return no_update, no_update
    match_id = triggered["index"]
    now = time.monotonic()
    if LIVE is not None:
        match = LIVE.match_summary(match_id, now)
        events = LIVE.match_events(match_id, now)
        stats = LIVE.match_statistics(match_id, now)
        lineups = LIVE.match_lineups(match_id, now)
    else:
        match, events, stats, lineups = None, [], {}, {}
    return True, modal_body(match, events, stats, lineups)
```
(Removes the `State("live-store", "data")` input and the `next(... live ...)` lookup.)

- [ ] **Step 2: Verify** — full suite + import (the modal_body tests already cover rendering)

Run: `/Users/yberber/anaconda3/envs/wc2026-live/bin/python -m pytest tests/ -q`
Then: `/Users/yberber/anaconda3/envs/wc2026-live/bin/python -c "import app; print('app OK')"`
Expected: all pass; app imports.

- [ ] **Step 3: Commit**

```bash
git add app.py
git commit -m "feat: modal fetches match header by id (works for past/selected-day games)"
```

---

## Task 6: Every drawer match links to the modal

**Files:**
- Modify: `src/components/detail_panel.py` (`_match_item`, `_matches_section`, `stadium_detail`)
- Modify: `app.py` (`drawer_for_city`, `open_stadium_drawer`)
- Test: `tests/test_detail_panel.py`

- [ ] **Step 1: Write the failing test** (add to `tests/test_detail_panel.py`; reuse the existing `_venue()` / Match helpers in that file)

```python
def test_drawer_match_is_clickable_when_id_resolved():
    from src.components.detail_panel import stadium_detail
    from datetime import date, time, datetime
    from src.data.matches import Match
    venue = _venue(stadium_name="Dallas Stadium")  # existing helper in this test file
    m = Match(number=4, home="USA", away="Paraguay", group="Group D", stage="Group Stage",
              stadium="Dallas Stadium", date=date(2026, 6, 12), local_time=time(18, 0),
              kickoff_utc=datetime(2026, 6, 13, 1, 0))
    body = stadium_detail(venue, matches=(m,), user_tz=None,
                          match_links={4: 1267454654})
    blob = str(body.to_plotly_json())
    assert "open-live-modal" in blob and "1267454654" in blob

def test_drawer_match_plain_when_no_link():
    from src.components.detail_panel import stadium_detail
    from datetime import date, time, datetime
    from src.data.matches import Match
    venue = _venue(stadium_name="Dallas Stadium")
    m = Match(number=4, home="USA", away="Paraguay", group="Group D", stage="Group Stage",
              stadium="Dallas Stadium", date=date(2026, 6, 12), local_time=time(18, 0),
              kickoff_utc=datetime(2026, 6, 13, 1, 0))
    body = stadium_detail(venue, matches=(m,), user_tz=None, match_links={})
    assert "open-live-modal" not in str(body.to_plotly_json())
```
If the test file has no `_venue` helper that accepts `stadium_name`, construct the `Venue` the same way the existing tests in that file do (read them first) and set `stadium_name="Dallas Stadium"`.

- [ ] **Step 2: Run → FAIL**

Run: `/Users/yberber/anaconda3/envs/wc2026-live/bin/python -m pytest tests/test_detail_panel.py -k "clickable_when_id or plain_when_no_link" -v`
Expected: FAIL (`stadium_detail` has no `match_links`).

- [ ] **Step 3: Implement** in `src/components/detail_panel.py`

Add `from dash import html` to the imports if not present. Change `_match_item` to optionally wrap its content in a clickable div:
```python
def _match_item(match: Match, user_tz: str | None, api_id=None) -> dmc.TimelineItem:
    kv = kickoff_view(match, user_tz)
    day = kv.user_date or match.date
    title = f"{day.strftime('%b')} {day.day} · {_match_label(match)}"
    content = [
        dmc.Text([_team_span(match.home), " vs ", _team_span(match.away)], size="sm"),
        _kickoff_line(kv),
    ]
    if api_id is not None:
        content = [html.Div(
            content, id={"type": "open-live-modal", "index": api_id},
            n_clicks=0, style={"cursor": "pointer"})]
    return dmc.TimelineItem(
        title=title,
        bullet=DashIconify(icon="tabler:ball-football", width=12),
        children=content,
    )
```
Thread `match_links` through `_matches_section` and `stadium_detail`:
```python
def _matches_section(matches, user_tz, match_links=None):
    links = match_links or {}
    ...
    body = dmc.Timeline(
        [_match_item(m, user_tz, links.get(m.number)) for m in matches],
        active=len(matches), bulletSize=20, lineWidth=2,
    )
    ...
```
```python
def stadium_detail(venue, matches=(), user_tz=None, live=None, match_links=None):
    ...
    children.append(_matches_section(matches, user_tz, match_links))
    ...
```
(Keep the existing `live` live-section behavior unchanged; only add the `match_links` parameter and pass-through.)

- [ ] **Step 4: Resolve ids in `app.py`** (`drawer_for_city` + callback)

```python
def _venue_match_links(matches, now):
    """{match_number: api_match_id} for a venue's matches, resolved per date."""
    if LIVE is None:
        return {}
    from src.data.live.reconcile import canonical_team, index_matches_by_pair
    links = {}
    by_date = {}
    for m in matches:
        by_date.setdefault(m.date.isoformat(), []).append(m)
    for date_iso, day_matches in by_date.items():
        idx = index_matches_by_pair(LIVE.matches_on(date_iso, now))
        for m in day_matches:
            mid = idx.get((canonical_team(m.home), canonical_team(m.away)))
            if mid is not None:
                links[m.number] = mid
    return links

def drawer_for_city(city, user_tz=None, live=None):
    venue = VENUES_BY_CITY.get(city) if city else None
    if venue is None:
        return False, no_update, no_update
    matches = MATCHES_BY_STADIUM.get(venue.stadium_name, [])
    links = _venue_match_links(matches, time.monotonic())
    return True, venue.official_name, stadium_detail(venue, matches, user_tz, live=live, match_links=links)
```
(`open_stadium_drawer` already calls `drawer_for_city(city, user_tz, live)` — no signature change needed there.)

- [ ] **Step 5: Run tests + import**

Run: `/Users/yberber/anaconda3/envs/wc2026-live/bin/python -m pytest tests/test_detail_panel.py -v`
Then: `/Users/yberber/anaconda3/envs/wc2026-live/bin/python -c "import app; print('app OK')"`
Expected: PASS; app imports.

- [ ] **Step 6: Commit**

```bash
git add src/components/detail_panel.py app.py tests/test_detail_panel.py
git commit -m "feat: every stadium-drawer match links to the live-match modal"
```

---

## Task 7: Final verification (do NOT merge)

- [ ] **Step 1: Full suite**

Run: `/Users/yberber/anaconda3/envs/wc2026-live/bin/python -m pytest tests/ -q`
Expected: all green, offline.

- [ ] **Step 2: Manual live check** (with the key; the app auto-loads `.env`)

Run: `/Users/yberber/anaconda3/envs/wc2026-live/bin/python app.py`, then confirm: the calendar scrolls back to June 11; selecting June 12 shows that day's finished games in the strip; clicking a finished strip item opens the modal with stats/timeline/lineups; opening a stadium drawer shows each match as a clickable link that opens the modal.

- [ ] **Step 3: STOP — do not merge.** Summarize and ask the user to validate.

---

## Self-review notes
- **Spec coverage:** calendar range+default (Task 1); matches_on/match_summary (Task 2); pair index (Task 3); selected-day strip (Task 4); modal decoupling (Task 5); drawer links (Task 6); verification (Task 7). All spec sections covered.
- **Type consistency:** `match_summary`/`matches_on` reuse `self._match_dict` → identical dict shape as `snapshot()["matches"]`, consumed by `strip_items` and `modal_body` (already). `index_matches_by_pair` keys `(canonical_home, canonical_away)`; `_venue_match_links` looks up with the same `canonical_team`. `match_links` keyed by `match.number` in both producer and `_matches_section`.
- **No placeholders:** every step has concrete code/commands.
