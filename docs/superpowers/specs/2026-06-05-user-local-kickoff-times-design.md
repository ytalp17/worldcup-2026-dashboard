# User-Local Kickoff Times — Design

**Date:** 2026-06-05
**Status:** Approved (pending written-spec review)

## Goal

Make the **user's local timezone the anchor** for all dates and times in the app.
Remove the static timezone string from the stadium drawer. Show every match's
kickoff in the user's local time (with its user-local date), alongside the venue
local time tagged `−1d`/`+1d` when the venue's calendar day differs. The header
date selector also works in user-local dates (a stadium pulses when its kickoff
falls on the selected date *in the user's timezone*).

## Core Rule

The visitor's timezone (read from the browser) defines "what day/time it is":
- **User-local time is the anchor** — shown with its user-local date.
- **Venue-local time** is shown alongside, with a `−1d`/`+1d` tag **only** when the
  venue's calendar day differs from the user-local day.
- **Same timezone** (user-local clock == venue clock) → show a single time, no tag.
- **User tz unknown** (not yet detected, or unsupported browser) → fall back to the
  current venue-date/time behavior everywhere (graceful, no errors).

## Approach: precompute the absolute instant (Approach A)

The user's timezone is per-visitor and only known at runtime, so the conversions
cannot be fully precomputed. The *hard* part — resolving each match's venue-local
time + the correct DST offset into an absolute instant — **is** fixed, so we
compute it once offline and store a `kickoff_utc` column. At runtime every
conversion is then a single `astimezone` from UTC to the user's zone; no
venue-`ZoneInfo` / stadium→zone machinery runs in the app.

## Data

### CSV (`assets/data/wc2026_matches.csv`) — overwritten in place

Add one column, `kickoff_utc` (ISO-8601 UTC instant). `local_time` (venue clock)
stays for display.

```
match_number,home_team,away_team,group,stage,stadium,match_date,local_time,kickoff_utc
1,Mexico,South Africa,Group A,Group Stage,Mexico City Stadium,2026-06-11,13:00,2026-06-11T19:00:00Z
```

### Generator script `scripts/compute_kickoff_utc.py`

A one-time/offline script (re-run whenever the schedule changes):
1. Read `assets/data/wc2026_matches.csv` (pandas).
2. For each row: resolve the stadium → host city → IANA zone (reuse
   `src/data/timezones.py` + the stadium→city mapping), build a tz-aware datetime
   from `match_date` + `local_time` in that zone, convert to UTC.
3. Write the `kickoff_utc` column and **overwrite the same CSV file in place**
   (stable column order, no index).

This is the ONLY place venue zones / DST are handled.

### `Match` dataclass (`src/data/matches.py`)

- Add `local_time: datetime.time` (parsed from `HH:MM`).
- Add `kickoff_utc: datetime` (tz-aware UTC, parsed from the ISO string).
- `EXPECTED_COLUMNS` gains `local_time` and `kickoff_utc`. Bad/missing values raise
  the existing `ValueError("Bad match row…")`.

## Runtime timezone detection

- Layout adds `dcc.Store(id="user-tz")` and a one-shot `dcc.Interval(id="tz-probe",
  interval=1, max_intervals=1)`.
- A **clientside callback** `Input("tz-probe","n_intervals") → Output("user-tz","data")`
  returns `Intl.DateTimeFormat().resolvedOptions().timeZone` (e.g. `"Europe/Berlin"`),
  or `null` on failure. Runs once, right after load.

## New pure module `src/data/kickoff.py` (TDD'd, no Dash)

```python
@dataclass(frozen=True)
class KickoffView:
    user_time: str | None     # "HH:MM" in the user's zone, or None if tz unknown
    user_date: date | None    # user-local date, or None
    venue_time: str           # "HH:MM" venue clock (from local_time)
    venue_day_offset: int     # venue_date - user_local_date, in days (… -1, 0, +1 …)
    same_clock: bool          # True when user tz unknown OR user time == venue time same day

def kickoff_view(match, user_tz: str | None) -> KickoffView: ...
```

- `user_tz` is `None` / unknown → `user_time=user_date=None`, `venue_day_offset=0`,
  `same_clock=True` (caller shows venue-only).
- Otherwise convert `match.kickoff_utc` to `ZoneInfo(user_tz)`; `venue_time` =
  `match.local_time.strftime("%H:%M")`; `venue_day_offset = (match.date - user_date).days`;
  `same_clock = (user_time == venue_time and venue_day_offset == 0)`.
- A formatting helper builds the `−1d`/`+1d` tag string from `venue_day_offset`
  (empty when 0).

## Header calendar = user-local dates

`MatchCalendar.active_cities(day, user_tz=None)`:
- If `user_tz` given: for each match, `user_day = match.kickoff_utc.astimezone(ZoneInfo(user_tz)).date()`; include its city when `user_day == day`.
- If `user_tz` is `None`: current behavior (compare `match.date`).

`MatchCalendar` already receives the matches (now carrying `kickoff_utc`) and the
stadium→city map; no new dependency. Date range padded by ±1 day
(`maxDate = max venue date + 1`) so user-local dates at the edges stay selectable;
default selected value stays "today" (before the tournament → no pulses, unchanged).

## App wiring (`app.py`)

- `update_pulse_layer` gains `Input("user-tz","data")` and threads it into
  `pulse_children_for_mode → _active_cities_for_date(selected_date, user_tz) →
  MATCH_CALENDAR.active_cities(day, user_tz)`. Using **Input** (not State) means
  pulses recompute the moment the timezone resolves.
- `open_stadium_drawer` gains `State("user-tz","data")` and passes it into
  `stadium_detail(venue, matches, user_tz)`.
- The clientside tz callback is registered (see detection above).

## Drawer (`src/components/detail_panel.py`)

- **Remove** `_timezone_text` and the clock/timezone `Group` entirely.
- `stadium_detail(venue, matches, user_tz=None)`.
- A single muted note at the top of the Matches section:
  *"Times in your timezone (Europe/Berlin), with venue time alongside"* — when tz
  known; *"Times in venue-local time"* when unknown.
- `_match_item(match, user_tz)` via `kickoff_view`:
  - **title date** = user-local date when known, else venue date.
  - under the teams, when tz known and `same_clock` is False (example: a 20:00
    New York kickoff seen from Tokyo, ~09:00 the next day → venue day is one behind):
    ```
    Brazil vs Morocco
    🌍 09:00 your time   ·   🏟 20:00 venue (−1d)
    ```
  - when `same_clock` True (same zone) → single line: `🏟 13:00 local`.
  - when tz unknown → single line `🏟 13:00 local` (current-style, venue date title).

## Testing

- `matches.py`: `local_time` + `kickoff_utc` parse correctly; missing column / bad
  value raises.
- `kickoff.py`: user conversion; `venue_day_offset` for a late-night match that
  crosses midnight in the user's zone (e.g. a 20:00 US kickoff → next-day Europe →
  venue tagged `−1d`); unknown tz → `user_time None`, `same_clock True`; same-zone →
  `same_clock True`; tag formatter (`-1` → "−1d", `0` → "").
- `match_calendar.py`: `active_cities(day, user_tz)` moves a boundary match to the
  user-local day; `user_tz=None` keeps venue-date behavior.
- `detail_panel.py`: no timezone string rendered; renders dual times when tz known;
  single venue time when unknown / same-zone; title uses user-local date.
- `layout.py`: `user-tz` store + `tz-probe` interval present.
- `app.py`: clientside tz callback registered; `update_pulse_layer` and
  `open_stadium_drawer` thread `user-tz`.
- `scripts/compute_kickoff_utc.py`: a known row converts correctly (e.g. Mexico City
  `13:00` → `19:00Z`, since America/Mexico_City is UTC−6 with no DST in 2026).

## Non-Goals

- No change to flows, carousel, or theme.
- No per-visitor precomputation (infeasible — user tz is runtime/per-visitor).
- Venue zone/DST handling lives ONLY in the offline generator script.
