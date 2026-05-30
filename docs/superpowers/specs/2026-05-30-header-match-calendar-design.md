# Header Match Calendar — Design

**Date:** 2026-05-30
**Status:** Approved (design)

## Goal

Add a `dmc.MiniCalendar` to the centre of the header, spanning **today → the World
Cup final day**, with selectable dates. Days that have a match scheduled **blink**
(reusing the venue-marker pulse). Selecting a date drives the map: stadiums hosting a
match that day **blink**, all others stay visible but **static**. Default selected
date is **today**.

## Prerequisite migration

`dmc.MiniCalendar` only exists in `dash-mantine-components` 2.3.0+ (Mantine 8), which
targets Dash 3. This is therefore a dependency migration before any feature work:

- `dash 2.18.2 → 3.x`, `dash-mantine-components 0.15.1 → 2.3.x`.
- Verify/bump `dash-leaflet` (currently 1.0.15, requires only `dash>=2.13.0`) and
  `dash-iconify` for Dash 3 / React compatibility.
- Remove the manual `dash._dash_renderer._set_react_version("18.2.0")` opt-in — Dash 3
  / DMC 2 manage React themselves.
- Fix all DMC 2 / Dash 3 API breakages until the **existing 117 tests pass and the app
  boots unchanged**. The existing suite is the migration's guard. Done on a feature
  branch with pinned-version rollback (`requirements.txt` records the new pins).

The migration is treated as a verification-driven step (make the existing tests green),
not new TDD — the tests already exist. Feature work below is TDD.

## Data layer — `MatchCalendar`

A service derived from the loaded `MATCHES` (and a stadium→city map from `VENUES`,
since `Match.stadium` is the generic FIFA name and map markers are keyed by city):

- `start`: today (injected; the app passes `date.today()`, tests pass a fixed date).
- `end`: the final day = max match date (2026-07-19), data-driven.
- `match_dates -> set[date]`: the 34 days with matches → drives **calendar blink**.
- `active_cities(d: date) -> set[str]`: host cities with a match on `d` → drives
  **map blink** and **selection highlight**. Empty for non-match days (e.g. today).

OOP: a small frozen/dataclass-style service class with the above as
properties/methods. Pure, fully unit-testable without Dash.

## Header layout

Three zones, balanced so nothing overflows and it degrades on mobile:

`brand (left) · MiniCalendar (centre) · theme toggle (right)`

`dmc.MiniCalendar`:
- `value = today` (default selected), `minDate = start`, `maxDate = end`.
- Compact `numberOfDays` with prev/next navigation so it fits small screens.
- Match-days receive a blink class via the per-day mechanism. **Exact MiniCalendar
  API (per-day styling: `getDayProps` function-as-prop vs. alternative, plus the
  selection callback property) will be confirmed via context7 against the installed
  2.3.x build during implementation**, since the component does not exist pre-upgrade.

## Blink styling

Reuse the existing `venue-pulse` keyframes (the current marker pulse) — themed for
dark/light — applied to (1) calendar match-days and (2) active map markers. No new
animation; one shared visual language.

## Map reacts to selection

A callback maps the MiniCalendar selected date → the venue-marker layer:
- Stadiums in `active_cities(selected)` render **pulsing** (`.venue-marker`).
- All other stadiums render as **static dots** (a non-animated variant), still visible.

This deliberately changes today's behaviour where **all** markers always pulse; pulsing
becomes date-driven. On the default date (today, no matches) nothing pulses — faithful
to "inactive ⇒ not blinking". "Filter" here means **highlight** (inactive stadiums stay
on the map), not hide.

## Testing (TDD, feature code)

- `MatchCalendar`: `start`/`end`, `match_dates` (34 days, includes 2026-06-11, excludes
  today), `active_cities` (correct cities for a known match day; empty for today).
- Header: contains a `dmc.MiniCalendar` with the right `minDate`/`maxDate`/`value`.
- Calendar match-days carry the blink class (via the confirmed per-day mechanism).
- Selection callback / marker builder: active cities → pulsing class, others → static.
- Full suite + headless boot.

## Out of scope

- Changing the match schedule or venue data.
- Persisting the selected date across reloads (beyond DMC defaults).
- Knockout bracket interactions.
