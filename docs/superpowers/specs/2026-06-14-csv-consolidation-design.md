# CSV Consolidation + Team Codes — Design

**Date:** 2026-06-14
**Status:** Approved, ready for implementation plan
**Branch:** feat/highlightly-live-data (do NOT merge to main without user validation)

## Goal

Collapse the 9 ad-hoc CSVs in `assets/data/` into 4 entity-oriented files with no
cross-file duplication and no information loss, and enrich team data with FIFA
abbreviation codes, confederation, and manager details. Replace the three venue
loaders + fuzzy join with a single `VenueRepository`.

## Motivation

- **Venue data is described 4 times** for the same 16 venues, with mismatched join
  keys (`San Francisco` vs `San Francisco Bay Area`; common name `BMO Field` vs
  WC2026-generic `Toronto Stadium`). This is the "duplicate rows" the user noticed.
- **Two files are dead** (loaded by zero code): `fifa_2026_matches.csv` and
  `host_cities.csv`.
- New source material to incorporate: `fifa_abbrevations.md` (FIFA tri-codes +
  confederation) and `managers.md` (head coaches).

## Target files (`assets/data/`)

After migration, exactly **4 data CSVs** remain (plus the unrelated
`estimated_starting_eleven.json`, which is out of scope).

### 1. `venues.csv` — one row per venue (16)
Merges `fifa_2026_host_cities.csv` + `fifa_wc2026_stadiums.csv` +
`wc2026_stadium_altitude.csv` + `host_cities.csv`.

Columns:
```
city, country, official_name, stadium_name, location, capacity, opened,
info, image_filename, image_url, latitude, longitude,
altitude_m, altitude_ft, altitude_tier, region_cluster, airport_code,
timezone, tz_label
```
- `city` canonical form = `San Francisco`, `New York/New Jersey` (the form the app
  already uses for timezone + altitude lookup). `host_cities.csv`'s
  `San Francisco Bay Area` is normalized to `San Francisco` during the join.
- `stadium_name` = WC2026-generic name ("Mexico City Stadium"), the **match-join key**
  (matches in `matches.csv` reference this). Unchanged.
- `official_name` = common stadium name ("Estadio Azteca").
- `timezone` (IANA, e.g. `America/Chicago`) + `tz_label` (e.g. `Central Time`) absorb
  the hardcoded `CITY_TIMEZONES` dict from `src/data/timezones.py` — pure per-venue
  data that should live in the CSV, not in code. `timezones.py` is then **deleted**.
- `image_url`, `altitude_ft`, `altitude_tier`, `region_cluster`, `airport_code` are
  currently unused but **preserved** so no information is lost.

### 2. `matches.csv` — the schedule (104 rows)
Straight rename of `wc2026_matches.csv`. Columns unchanged:
```
match_number, home_team, away_team, group, stage, stadium, match_date,
local_time, kickoff_utc
```
Dead `fifa_2026_matches.csv` is deleted (its `City`/`Group`/`Stage` are derivable
from `matches.csv` + `venues.csv`).

### 3. `teams.csv` — one row per team (48)
Merges `team_continents.csv` + `team_distances.csv`, enriched from
`fifa_abbrevations.md` and `managers.md`.

Columns:
```
team, continent, distance_km, code, confederation, coach, coach_nationality, coach_since
```
- `team` = canonical names from `team_continents.csv` (the 48-team field the app uses).
- `code` = FIFA tri-code (e.g. `Korea Republic`→`KOR`, `United States`→`USA`).
- `confederation` = CONMEBOL / UEFA / CAF / AFC / CONCACAF / OFC.
- `coach`, `coach_nationality`, `coach_since` from `managers.md`. Teams without a
  manager entry get empty strings. "Previous role" is dropped.
- Source name variants are normalized to canonical during the merge:
  `Turkey`→`Türkiye`, `Czech Republic`→`Czechia`, `DR Congo`→`Congo DR`,
  `Korea Republic` (kept), `Ivory Coast`/`Curacao` matched as-is. The merge script
  asserts every of the 48 teams resolves a `code` (fail loud on a missing code).

### 4. `squads.csv` — players (1247 rows)
Rename of `world_cup_2026_squads.csv`. Content unchanged.

### Deleted after migration
`fifa_2026_host_cities.csv`, `fifa_wc2026_stadiums.csv`,
`wc2026_stadium_altitude.csv`, `host_cities.csv`, `fifa_2026_matches.csv`,
`team_continents.csv`, `team_distances.csv`, `wc2026_matches.csv`,
`world_cup_2026_squads.csv`, `fifa_abbrevations.md`, `managers.md`.

## Code changes

### New / changed
- **`src/data/venues.py`**: add `VenueRepository(csv_path, image_dir).load() -> list[Venue]`
  that reads `venues.csv` directly (no fuzzy substring join). `Venue` keeps all current
  fields including `timezone`/`tz_label` (now read straight from the CSV); gains optional
  `region_cluster: str | None`, `airport_code: str | None`. `has_image` logic preserved.
  Remove `build_venues`.
- **`src/data/team_continents.py`**: load `teams.csv`; keep `TEAM_CONTINENT`,
  `continent_for`, `grouped_team_options`, `CONTINENT_ORDER`. Add `TEAM_CODE: dict[str,str]`
  and `code_for(team) -> str`.
- **`src/data/distances.py`**: `DistanceRepository` reads `teams.csv` (cols `team`,
  `distance_km`). Validation unchanged.

### Deleted
- `src/data/host_cities.py` (`HostCity`, `HostCityRepository`)
- `src/data/stadiums.py` (`Stadium`, `StadiumRepository`)
- `src/data/altitudes.py` (`AltitudeRepository`)
- `src/data/timezones.py` (`CITY_TIMEZONES`, `timezone_for`) — data folded into `venues.csv`
- `build_venues` in `venues.py`

### Static maps deliberately KEPT (not CSV duplication)
These are translation / presentation logic, not restated CSV data, so they stay:
- `src/data/squads.py::_CANONICAL` and `src/data/lineups.py::_SLUG_TO_CANONICAL` —
  reconcile inconsistent team spellings/slugs from heterogeneous sources onto the
  app-canonical names (e.g. squad CSV `Cape Verde` → `Cabo Verde`).
- `src/data/live/reconcile.py::TEAM_ALIASES` — maps live-API team names to canonical.
- `src/data/team_continents.py::CONTINENT_ORDER` — fixed UI sort order, not data.

### app.py wiring
Replace lines 46-50:
```python
CITIES = HostCityRepository(...).load()
STADIUMS = StadiumRepository(...).load()
ALTITUDES = AltitudeRepository(...).load()
DISTANCES = DistanceRepository(DATA_DIR / "team_distances.csv").load()
VENUES = build_venues(CITIES, STADIUMS, IMAGE_DIR, ALTITUDES)
```
with:
```python
VENUES = VenueRepository(DATA_DIR / "venues.csv", IMAGE_DIR).load()
DISTANCES = DistanceRepository(DATA_DIR / "teams.csv").load()
```
Repoint `MatchRepository`→`matches.csv`, `SquadRepository`→`squads.csv`,
`team_continents._CSV_PATH`→`teams.csv`. Drop the now-unused imports.

## How the CSVs are generated

A one-off migration script `scripts/consolidate_csvs.py` performs the pandas joins to
produce the 4 new CSVs from the originals + the two `.md` files. It is the auditable
record of the merge. Run once; committed for reproducibility. After it runs and the
new files are verified, the old files are deleted.

## Data flow (unchanged downstream)
```
venues.csv ─► VenueRepository ─► VENUES ─► map markers, drawer, flows, calendar
teams.csv  ─► team_continents (TEAM_CONTINENT, TEAM_CODE) + DistanceRepository
matches.csv─► MatchRepository ─► MATCHES ─► everything match-related
squads.csv ─► SquadRepository ─► SQUADS
```

## Testing (TDD, per CLAUDE.md)
- **New** `tests/test_venues.py`: `VenueRepository.load()` returns 16 venues; each row
  has matching `official_name`/`stadium_name`; altitude attached; lat/lon range-validated
  (raises on out-of-range); `has_image` reflects file presence; `timezone`/`tz_label`,
  `airport_code`/`region_cluster` populated.
- **Update** `tests/test_team_continents.py`: load from `teams.csv`; add `code_for`
  (`Korea Republic`→`KOR`) + missing-team raises.
- **Update** `tests/test_distances.py`: read `teams.csv`.
- **Update** `tests/test_matches.py`, `tests/test_squads.py`, `tests/test_flows.py`,
  `tests/test_match_calendar.py`, `tests/test_live_reconcile.py`: repoint CSV paths.
- **Delete** `tests/test_host_cities.py`, `tests/test_stadiums.py`,
  `tests/test_altitudes.py`, `tests/test_timezones.py` — their loaders are gone;
  join/validation/timezone coverage moves into `test_venues.py`.
- Full suite green and offline (no-key mode unaffected).

## Out of scope (YAGNI)
- Surfacing `code`/`confederation`/`coach` in the UI — this spec only lands the data
  and loaders. UI usage is a separate follow-up.
- `estimated_starting_eleven.json` (different entity, no duplication).
- Map badges, standings normalization, any live-data behavior.
