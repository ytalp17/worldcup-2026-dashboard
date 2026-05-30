# Matches Timeline in the Stadium Drawer — Design

**Date:** 2026-05-30
**Status:** Approved for planning

## Goal

Show every match scheduled at the selected stadium inside the detail drawer,
laid out as a vertical timeline (chronological).

## Data

`assets/data/wc2026_matches.csv` — 104 matches; columns:
`match_number, home_team, away_team, group, stage, stadium, match_date`.
The `stadium` column uses the same 16 generic names as
`fifa_wc2026_stadiums.csv` (the `Stadium` field), so matches join to a venue by
exact stadium-name equality — no fuzzy matching.

New `src/data/matches.py`:
- `Match` (frozen dataclass): `number:int, home:str, away:str, group:str,
  stage:str, stadium:str, date:datetime.date`.
- `MatchRepository(csv_path).load() -> list[Match]`: validates the 7 expected
  columns, parses `match_date` (`YYYY-MM-DD`) via `date.fromisoformat`, raises
  `ValueError` on missing columns or unparseable rows.
- `matches_by_stadium(matches) -> dict[str, list[Match]]`: groups by the
  generic stadium name; each list sorted by `(date, number)`.

## Join key

`Venue` gains `stadium_name: str` = `stadium.name` (the generic FIFA name, e.g.
"Dallas Stadium"). `build_venues` populates it. This is the exact key the
matches reference.

## Wiring

`app.py`:
- Load matches once: `MATCHES = MatchRepository(...).load()` and
  `MATCHES_BY_STADIUM = matches_by_stadium(MATCHES)`.
- `drawer_for_city(city)` looks up the venue, fetches
  `MATCHES_BY_STADIUM.get(venue.stadium_name, [])`, and calls
  `stadium_detail(venue, matches)`.

## UI — `src/components/detail_panel.py`

`stadium_detail(venue, matches=())` keeps the current header (photo, location,
capacity/opened badges, timezone, info blurb), then adds a **"Matches (N)"**
section rendered as `dmc.Timeline`:
- One `dmc.TimelineItem` per match.
- Title: `"<Mon D> · <label>"` where `<label>` is the group for group-stage
  rows (e.g. "Group A") and the stage name otherwise (e.g. "Round of 16").
- Body: `dmc.Text("<home> vs <away>", size="sm", c="dimmed")`.
- `Timeline` color left at theme primary (adapts to dark/light); `active` set to
  all items so bullets are filled.
- If `matches` is empty: a single dimmed "No matches scheduled" line (defensive;
  all 16 venues have matches).

The drawer body scrolls naturally when content overflows (no fixed-height inner
ScrollArea — remove the previous one so the whole body, including the timeline,
scrolls together).

## Testing (TDD)

- `tests/test_matches.py`: loads 104; `date` parsed to `datetime.date`; a known
  row (match 1: Mexico vs South Africa, Mexico City Stadium, 2026-06-11);
  missing-column and bad-date raise `ValueError`; `matches_by_stadium` groups by
  name and sorts each list by date then number.
- `tests/test_venues.py`: `Venue.stadium_name` equals the generic name
  (Dallas → "Dallas Stadium").
- `tests/test_detail_panel.py`: `stadium_detail(venue, matches)` renders a
  `dmc.Timeline` with one item per match; team names and a formatted date appear;
  empty matches → "No matches scheduled", no Timeline.
- `scripts/e2e_check.py` / inline: clicking a marker shows the timeline with
  match rows in the drawer.

## Notes

- Teams are shown as text (no flag assets available).
- Existing markers, tiles, timezone, and theme behavior are unchanged.
