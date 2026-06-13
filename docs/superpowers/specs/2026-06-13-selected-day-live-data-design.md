# Selected-Day Live Data — Design

**Date:** 2026-06-13
**Status:** Approved, ready for implementation plan
**Branch:** feat/highlightly-live-data (do NOT merge to main without user validation)

## Goal

Make the live experience span the whole tournament retrospectively: the header calendar
starts at the opening day (June 11), and the bottom strip + the modal reflect the **selected
calendar day** — including finished games with final scores. Every match in the stadium drawer
becomes a clickable link to the same detail modal.

Builds on the existing live integration (Highlightly API, Dash 4.2 WebSocket push, tabbed modal).

## Decisions (from clarifying questions)

| Topic | Decision |
|---|---|
| Calendar range | Starts at the tournament's first match date (June 11), ends at the final + 1 |
| Default selected day | **Today** (live games show on load; scroll back for past days) |
| Strip | Reflects the **selected day**: past → finished w/ final scores, today → live/scheduled, future → scheduled; all clickable. Today keeps auto-updating via the WebSocket; other days fetched once and cached |
| Drawer | **Every** match (past/today/future) is a clickable link opening the modal; unresolved matches stay plain text |
| Map badges | Out of scope — LIVE score badges stay today/in-play only; day-based pulse already follows the selected day |

## Architecture

### 1. Calendar range — `src/data/match_calendar.py`, `src/components/header_calendar.py`
- `MatchCalendar.start` returns the **earliest match date** (min of the schedule), not `today`.
- Add `MatchCalendar.default_day` → `today` clamped into `[start, end]`.
- `build_match_calendar`: `minDate = start` (June 11), `maxDate = end + 1 day`,
  `value = defaultDate = default_day` (today). `numberOfDays` unchanged.

### 2. Service — `src/data/live/service.py`
- `matches_on(date_iso: str, now: float) -> list[dict]`: the day's match dicts (same shape as
  `snapshot()["matches"]`), via `parse_matches` + venue join. Cached per date under key
  `matches:{date_iso}`; past dates (date < today) use a long TTL (finished data is immutable),
  today uses the normal 60s TTL. Returns `[]` on error.
- `match_summary(match_id: int, now: float) -> dict | None`: one match's header dict
  (match_id, home, away, venue, state, clock, home_score, away_score, is_live) parsed from the
  detail endpoint (`client.match(id)[0]` → `parse_match`). Cached under `summary:{id}`. `None` on error.

### 3. Strip + modal — `app.py`
- `render_live_strip(selected_date, live)`: Inputs `match-calendar.value` + `live-store.data`.
  If `selected_date == today` → `strip_items(live)` (auto-updating). Else →
  `strip_items({"matches": LIVE.matches_on(selected_date, now)})` when `LIVE`, else `[]`.
  Pure branch helper `strip_day_matches(selected, today, live, matches_on)` for testability.
- `open_live_modal`: drop the `live-store` dependency. `match_id = ctx.triggered_id["index"]`;
  `match = LIVE.match_summary(match_id, now)` (None when no key); events/stats/lineups by id as
  today; return `(True, modal_body(match, events, stats, lineups))`. Works for any match.

### 4. Drawer links — `app.py` (resolution) + `src/components/detail_panel.py` (render)
- New pure helper `index_matches_by_pair(api_matches) -> {(canon_home, canon_away): match_id}`
  (in `reconcile.py`), using `canonical_team`.
- Drawer callback (`drawer_for_city` / `open_stadium_drawer`): for each distinct date among the
  venue's scheduled matches, fetch `LIVE.matches_on(date)` (cached), build the pair→id index, and
  produce `match_links: {match_number: api_match_id}` for that venue's matches. Pass to
  `stadium_detail`.
- `stadium_detail(venue, matches, user_tz, live=None, match_links=None)`: `_match_item` wraps its
  content in a clickable element with id `{"type": "open-live-modal", "index": api_id}` when the
  match has a resolved id; otherwise renders plain (current behavior). `detail_panel` stays IO-free.

## Data flow
```
calendar value ──► render_live_strip ──► strip_items (selected day; live-store if today)
strip item / drawer item / drawer live-section click ──► open_live_modal(match_id)
   └─► match_summary(id) + match_events/statistics/lineups(id) ──► modal_body (tabs)
drawer open ──► matches_on(date) per venue date ──► pair→id index ──► clickable match rows
```

## Testing (TDD, offline)
- `MatchCalendar.start` = earliest date; `default_day` clamps to range. Unit test.
- `matches_on` / `match_summary`: fake client + fixtures; cache behavior; `[]`/`None` on error.
- `strip_day_matches`: today→live, other→fetched, no-key→empty. Pure unit test.
- `index_matches_by_pair`: pair keys via canonical names (incl. an alias case). Pure unit test.
- `stadium_detail` with `match_links`: clickable id present for resolved matches, plain otherwise.
- `open_live_modal` decoupling: covered by component/render tests of `modal_body` (already) + a
  service test for `match_summary`.
- Full suite stays green and offline (no-key mode unaffected).

## Out of scope (YAGNI)
Map badges showing past-day scores; per-day standings history; changing the modal's tabs.
