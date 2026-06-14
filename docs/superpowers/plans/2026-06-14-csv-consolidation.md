# CSV Consolidation + Team Codes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Collapse the 9 ad-hoc CSVs in `assets/data/` into 4 entity files (venues, matches, teams, squads) with no cross-file duplication and no information loss, enrich teams with FIFA codes / confederation / manager, and replace the three venue loaders + fuzzy join with one `VenueRepository`.

**Architecture:** A one-off, committed migration script (`scripts/consolidate_csvs.py`) generates the 4 new CSVs from the originals + the two `.md` files. Loaders are then repointed/simplified to read them, old files and now-dead modules are deleted, and the test suite is updated. The hardcoded `CITY_TIMEZONES` dict moves into `venues.csv`.

**Tech Stack:** Python 3, pandas, pytest. Conda env `wc2026-live` (per project memory — NOT conda base). Branch `feat/highlightly-live-data` (do NOT merge to main without user validation).

**Run tests with:** `pytest tests/ -v` (in the `wc2026-live` env).

---

## File Structure

After this plan:

**New data files** (`assets/data/`): `venues.csv`, `matches.csv`, `teams.csv`, `squads.csv`.
**New code:** `scripts/consolidate_csvs.py` (migration), `src/data/venues.py::VenueRepository`.
**Changed code:** `src/data/team_continents.py` (reads `teams.csv`, adds codes), `app.py` (wiring).
**Deleted code:** `src/data/host_cities.py`, `src/data/stadiums.py`, `src/data/altitudes.py`, `src/data/timezones.py`, `build_venues` in `venues.py`.
**Deleted data:** `fifa_2026_host_cities.csv`, `fifa_wc2026_stadiums.csv`, `wc2026_stadium_altitude.csv`, `host_cities.csv`, `fifa_2026_matches.csv`, `team_continents.csv`, `team_distances.csv`, `wc2026_matches.csv`, `world_cup_2026_squads.csv`, `fifa_abbrevations.md`, `managers.md`.
**Deleted tests:** `tests/test_host_cities.py`, `tests/test_stadiums.py`, `tests/test_altitudes.py`, `tests/test_timezones.py`.

**Key join facts (verified against the data):**
- `stadium_name` (match-join key, e.g. `Dallas Stadium`) comes from `fifa_wc2026_stadiums.csv::Stadium` — it matches the schedule's `stadium` column exactly. The altitude file's `stadium_wc2026_name` is inconsistent (`New York Stadium` vs `New York New Jersey Stadium`) and is NOT used for the name.
- `capacity`/`opened`/`info`/`image_filename`/`image_url`/`location` come from `fifa_wc2026_stadiums.csv` (Dallas capacity 94000, not host_cities' 80000).
- `official_name`/`latitude`/`longitude`/`city`/`country` come from `fifa_2026_host_cities.csv`.
- `altitude_*` join by `city`; `region_cluster`/`airport_code` join by `city` after normalizing `San Francisco Bay Area` → `San Francisco`.
- City→stadium join: normalize (`lower`, `/`+`-`→space, collapse spaces) and require the normalized city to be a substring of exactly one normalized stadium name.

---

### Task 1: Migration script generates the 4 new CSVs

**Files:**
- Create: `scripts/consolidate_csvs.py`
- Create (generated, committed): `assets/data/venues.csv`, `assets/data/teams.csv`, `assets/data/matches.csv`, `assets/data/squads.csv`
- Test: `tests/test_consolidate_csvs.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_consolidate_csvs.py
from pathlib import Path

import pandas as pd

DATA = Path(__file__).parent.parent / "assets" / "data"


def test_venues_csv_shape_and_join():
    df = pd.read_csv(DATA / "venues.csv")
    assert len(df) == 16
    expected = {
        "city", "country", "official_name", "stadium_name", "location",
        "capacity", "opened", "info", "image_filename", "image_url",
        "latitude", "longitude", "altitude_m", "altitude_ft", "altitude_tier",
        "region_cluster", "airport_code", "timezone", "tz_label",
    }
    assert set(df.columns) == expected
    dallas = df[df["city"] == "Dallas"].iloc[0]
    assert dallas["stadium_name"] == "Dallas Stadium"      # match-join key
    assert dallas["official_name"] == "AT&T Stadium"        # common name
    assert int(dallas["capacity"]) == 94000                 # from stadium-detail source
    assert dallas["timezone"] == "America/Chicago"
    assert dallas["tz_label"] == "Central Time"
    assert int(dallas["altitude_m"]) == 183
    assert dallas["airport_code"] == "DAL"
    # San Francisco resolved (not "San Francisco Bay Area")
    assert "San Francisco" in set(df["city"])
    assert df["airport_code"].notna().all()


def test_teams_csv_shape_and_codes():
    df = pd.read_csv(DATA / "teams.csv")
    assert len(df) == 48
    assert set(df.columns) == {
        "team", "continent", "distance_km", "code", "confederation",
        "coach", "coach_nationality", "coach_since",
    }
    assert df["code"].notna().all() and (df["code"].str.len() == 3).all()
    by_team = df.set_index("team")
    assert by_team.loc["Korea Republic", "code"] == "KOR"
    assert by_team.loc["USA", "code"] == "USA"
    assert by_team.loc["Côte d'Ivoire", "code"] == "CIV"   # override
    assert by_team.loc["Türkiye", "code"] == "TUR"          # override
    assert by_team.loc["Scotland", "code"] == "SCO"         # override
    assert by_team.loc["Mexico", "confederation"] == "CONCACAF"
    assert by_team.loc["Brazil", "coach"] == "Carlo Ancelotti"


def test_matches_and_squads_carried_over():
    matches = pd.read_csv(DATA / "matches.csv")
    assert len(matches) == 104
    assert list(matches.columns)[:3] == ["match_number", "home_team", "away_team"]
    squads = pd.read_csv(DATA / "squads.csv")
    assert len(squads) == 1247
    assert "country" in squads.columns and "name" in squads.columns
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_consolidate_csvs.py -v`
Expected: FAIL — `FileNotFoundError` for `venues.csv`/`teams.csv` (not yet generated).

- [ ] **Step 3: Write the migration script**

```python
# scripts/consolidate_csvs.py
"""One-off migration: consolidate the 9 source CSVs (+ 2 .md files) in
assets/data/ into 4 entity CSVs (venues, teams, matches, squads).

Run once from the repo root:  python scripts/consolidate_csvs.py
Committed for reproducibility / audit. Safe to re-run (idempotent).
"""
from __future__ import annotations

import re
import shutil
from pathlib import Path

import pandas as pd

DATA = Path(__file__).resolve().parents[1] / "assets" / "data"

# Per-venue (city -> IANA timezone, friendly label). Absorbed from the former
# src/data/timezones.py::CITY_TIMEZONES — this is the last place it lives in code
# before moving into venues.csv.
CITY_TIMEZONES = {
    "New York/New Jersey": ("America/New_York", "Eastern Time"),
    "Boston": ("America/New_York", "Eastern Time"),
    "Philadelphia": ("America/New_York", "Eastern Time"),
    "Atlanta": ("America/New_York", "Eastern Time"),
    "Miami": ("America/New_York", "Eastern Time"),
    "Toronto": ("America/Toronto", "Eastern Time"),
    "Dallas": ("America/Chicago", "Central Time"),
    "Houston": ("America/Chicago", "Central Time"),
    "Kansas City": ("America/Chicago", "Central Time"),
    "Mexico City": ("America/Mexico_City", "Central Time"),
    "Monterrey": ("America/Monterrey", "Central Time"),
    "Guadalajara": ("America/Mexico_City", "Central Time"),
    "Seattle": ("America/Los_Angeles", "Pacific Time"),
    "San Francisco": ("America/Los_Angeles", "Pacific Time"),
    "Los Angeles": ("America/Los_Angeles", "Pacific Time"),
    "Vancouver": ("America/Vancouver", "Pacific Time"),
}


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[/\-]", " ", text.lower())).strip()


def build_venues_csv() -> None:
    cities = pd.read_csv(DATA / "fifa_2026_host_cities.csv")
    stadiums = pd.read_csv(DATA / "fifa_wc2026_stadiums.csv")
    alt = pd.read_csv(DATA / "wc2026_stadium_altitude.csv")
    hc = pd.read_csv(DATA / "host_cities.csv")

    hc["city_join"] = hc["city_name"].replace(
        {"San Francisco Bay Area": "San Francisco"}
    )
    alt_by_city = {r["city"]: r for _, r in alt.iterrows()}
    hc_by_city = {r["city_join"]: r for _, r in hc.iterrows()}
    norm_stadiums = [(_norm(r["Stadium"]), r) for _, r in stadiums.iterrows()]

    rows = []
    for _, c in cities.iterrows():
        city = c["City"]
        key = _norm(city)
        hits = [r for n, r in norm_stadiums if key in n]
        assert len(hits) == 1, f"{city}: expected 1 stadium match, got {len(hits)}"
        s, a, h = hits[0], alt_by_city[city], hc_by_city[city]
        tz, tz_label = CITY_TIMEZONES[city]
        rows.append({
            "city": city,
            "country": c["Country"],
            "official_name": c["Stadium"],
            "stadium_name": s["Stadium"],
            "location": s["Location"],
            "capacity": int(s["Capacity"]),
            "opened": int(s["Opened"]),
            "info": s["Info"],
            "image_filename": s["Image_Filename"],
            "image_url": s["Image_URL"],
            "latitude": c["Latitude"],
            "longitude": c["Longitude"],
            "altitude_m": int(a["altitude_m"]),
            "altitude_ft": int(a["altitude_ft"]),
            "altitude_tier": a["altitude_tier"],
            "region_cluster": h["region_cluster"],
            "airport_code": h["airport_code"],
            "timezone": tz,
            "tz_label": tz_label,
        })
    df = pd.DataFrame(rows)
    assert len(df) == 16, f"expected 16 venues, got {len(df)}"
    df.to_csv(DATA / "venues.csv", index=False)


def _parse_abbreviations() -> dict[str, tuple[str, str]]:
    """Territory -> (code, confederation) from the tab-separated md."""
    out: dict[str, tuple[str, str]] = {}
    for line in (DATA / "fifa_abbrevations.md").read_text(encoding="utf-8").splitlines():
        parts = line.split("\t")
        if len(parts) >= 3 and parts[1].strip() != "Code":
            out[parts[0].strip()] = (parts[1].strip(), parts[2].strip())
    return out


def _clean_coach(raw: str) -> str:
    name = raw.lstrip("*").strip()
    if " replaced " in name:
        name = name.split(" replaced ")[0].strip()
    return name.rstrip("*").strip()


def _parse_managers() -> dict[str, tuple[str, str, str]]:
    """canonical team -> (coach, coach_nationality, coach_since)."""
    alias = {
        "Cape Verde": "Cabo Verde", "Curacao": "Curaçao",
        "Czech Republic": "Czechia", "DR Congo": "Congo DR",
        "Iran": "IR Iran", "Ivory Coast": "Côte d'Ivoire", "Turkey": "Türkiye",
    }
    lines = [l.strip() for l in (DATA / "managers.md").read_text(encoding="utf-8").splitlines() if l.strip()]
    recs = lines[5:]  # drop the 5-cell header
    out: dict[str, tuple[str, str, str]] = {}
    for i in range(0, len(recs), 5):
        team_raw, coach, since, _prev, nat = recs[i:i + 5]
        team = team_raw.lstrip("*").strip()
        team = alias.get(team, team)
        out[team] = (_clean_coach(coach), nat.strip(), since.strip())
    return out


def build_teams_csv() -> None:
    cont = pd.read_csv(DATA / "team_continents.csv")
    dist = pd.read_csv(DATA / "team_distances.csv")
    dist_by = dict(zip(dist["team"], dist["distance_km"]))

    abbr = _parse_abbreviations()
    abbr_alias = {
        "Cabo Verde": "Cape Verde", "Czechia": "Czech Republic",
        "IR Iran": "Iran", "USA": "United States",
    }
    # Teams absent from the abbreviations md — explicit FIFA codes.
    overrides = {
        "Côte d'Ivoire": ("CIV", "CAF"),
        "Scotland": ("SCO", "UEFA"),
        "Türkiye": ("TUR", "UEFA"),
    }
    managers = _parse_managers()

    rows = []
    for _, r in cont.iterrows():
        team = r["team"]
        if team in overrides:
            code, conf = overrides[team]
        else:
            code, conf = abbr[abbr_alias.get(team, team)]
        coach, nat, since = managers.get(team, ("", "", ""))
        rows.append({
            "team": team,
            "continent": r["continent"],
            "distance_km": dist_by[team],
            "code": code,
            "confederation": conf,
            "coach": coach,
            "coach_nationality": nat,
            "coach_since": since,
        })
    df = pd.DataFrame(rows)
    assert len(df) == 48, f"expected 48 teams, got {len(df)}"
    assert (df["code"].str.len() == 3).all(), "every team needs a 3-letter code"
    df.to_csv(DATA / "teams.csv", index=False)


def copy_unchanged() -> None:
    # Byte-for-byte rename (no pandas reserialization that could shift quoting/precision).
    shutil.copyfile(DATA / "wc2026_matches.csv", DATA / "matches.csv")
    shutil.copyfile(DATA / "world_cup_2026_squads.csv", DATA / "squads.csv")


def main() -> None:
    build_venues_csv()
    build_teams_csv()
    copy_unchanged()
    print("Wrote venues.csv, teams.csv, matches.csv, squads.csv")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run the script to generate the CSVs**

Run: `python scripts/consolidate_csvs.py`
Expected: `Wrote venues.csv, teams.csv, matches.csv, squads.csv` and 4 new files in `assets/data/`.

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_consolidate_csvs.py -v`
Expected: PASS (3 tests).

- [ ] **Step 6: Commit**

```bash
git add scripts/consolidate_csvs.py tests/test_consolidate_csvs.py \
  assets/data/venues.csv assets/data/teams.csv assets/data/matches.csv assets/data/squads.csv
git commit -m "feat: migration script generates consolidated venues/teams/matches/squads CSVs

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: `VenueRepository` reads `venues.csv` directly

**Files:**
- Modify: `src/data/venues.py` (add `pandas` import, `region_cluster`/`airport_code` fields on `Venue`, new `VenueRepository`; remove `build_venues` and the `timezones`/`HostCity`/`Stadium` imports)
- Test: `tests/test_venues.py` (rewrite)

- [ ] **Step 1: Rewrite the failing test**

Replace the entire contents of `tests/test_venues.py` with:

```python
from pathlib import Path

import pandas as pd
import pytest

from src.data.venues import Venue, VenueRepository

DATA = Path(__file__).parent.parent / "assets" / "data"
VENUES_CSV = DATA / "venues.csv"
IMAGE_DIR = DATA.parent / "stadiums"


def _venues(image_dir=IMAGE_DIR):
    return VenueRepository(VENUES_CSV, image_dir).load()


def test_loads_sixteen_venues():
    venues = _venues()
    assert len(venues) == 16
    assert all(isinstance(v, Venue) for v in venues)


def test_dallas_fields_joined_correctly():
    dallas = next(v for v in _venues() if v.city == "Dallas")
    assert dallas.official_name == "AT&T Stadium"
    assert dallas.stadium_name == "Dallas Stadium"      # match-join key
    assert dallas.capacity == 94000
    assert dallas.opened == 2009
    assert dallas.lat == pytest.approx(32.7473)
    assert dallas.lon == pytest.approx(-97.0945)
    assert dallas.altitude_m == 183
    assert dallas.timezone == "America/Chicago"
    assert dallas.tz_label == "Central Time"
    assert dallas.airport_code == "DAL"
    assert dallas.region_cluster == "Central"


def test_every_venue_has_timezone_and_altitude():
    venues = _venues()
    assert all(v.timezone and v.tz_label for v in venues)
    assert all(isinstance(v.altitude_m, int) for v in venues)


def test_has_image_reflects_file_presence(tmp_path):
    (tmp_path / "Dallas_Stadium.jpg").write_bytes(b"jpegbytes")
    by_city = {v.city: v for v in _venues(tmp_path)}
    assert by_city["Dallas"].has_image is True
    assert by_city["Monterrey"].has_image is False


def test_image_src_under_stadiums_assets():
    dallas = next(v for v in _venues() if v.city == "Dallas")
    assert dallas.image_src == "/assets/stadiums/Dallas_Stadium.jpg"


def test_missing_column_raises(tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text("city,country\nDallas,USA\n")
    with pytest.raises(ValueError):
        VenueRepository(bad, tmp_path).load()


def test_out_of_range_latitude_raises(tmp_path):
    src = pd.read_csv(VENUES_CSV)
    src.loc[0, "latitude"] = 200.0
    bad = tmp_path / "bad.csv"
    src.to_csv(bad, index=False)
    with pytest.raises(ValueError):
        VenueRepository(bad, tmp_path).load()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_venues.py -v`
Expected: FAIL — `ImportError: cannot import name 'VenueRepository'`.

- [ ] **Step 3: Rewrite `src/data/venues.py`**

Replace the entire contents of `src/data/venues.py` with:

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

REQUIRED_COLUMNS = [
    "city", "country", "official_name", "stadium_name", "location",
    "capacity", "opened", "info", "image_filename",
    "latitude", "longitude", "timezone", "tz_label",
]


@dataclass(frozen=True)
class Venue:
    """A host city joined with its stadium-detail record and image state."""

    city: str
    country: str
    lat: float
    lon: float
    official_name: str  # real stadium name, e.g. "AT&T Stadium"
    stadium_name: str  # generic FIFA name, e.g. "Dallas Stadium" (match-join key)
    location: str
    capacity: int
    opened: int
    info: str
    image_filename: str
    has_image: bool
    timezone: str  # IANA name, e.g. "America/Chicago"
    tz_label: str  # friendly label, e.g. "Central Time"
    altitude_m: int | None = None  # stadium altitude in metres, if known
    region_cluster: str | None = None
    airport_code: str | None = None

    @property
    def image_src(self) -> str:
        return f"/assets/stadiums/{self.image_filename}"


def _opt(row: pd.Series, column: str) -> str | None:
    if column not in row or pd.isna(row[column]):
        return None
    text = str(row[column]).strip()
    return text or None


class VenueRepository:
    """Loads fully-joined venue records from the consolidated venues.csv."""

    def __init__(self, csv_path: str | Path, image_dir: str | Path) -> None:
        self._csv_path = Path(csv_path)
        self._image_dir = Path(image_dir)

    def load(self) -> list[Venue]:
        df = pd.read_csv(self._csv_path)

        missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
        if missing:
            raise ValueError(f"Missing expected columns: {missing}")

        venues: list[Venue] = []
        for _, row in df.iterrows():
            try:
                lat = float(row["latitude"])
                lon = float(row["longitude"])
                capacity = int(row["capacity"])
                opened = int(row["opened"])
            except (ValueError, TypeError) as exc:
                raise ValueError(f"Non-numeric value in row: {row.to_dict()}") from exc

            if not -90.0 <= lat <= 90.0:
                raise ValueError(f"Latitude out of range: {lat}")
            if not -180.0 <= lon <= 180.0:
                raise ValueError(f"Longitude out of range: {lon}")

            altitude = row.get("altitude_m")
            altitude_m = int(altitude) if pd.notna(altitude) else None
            image_filename = str(row["image_filename"])

            venues.append(
                Venue(
                    city=str(row["city"]),
                    country=str(row["country"]),
                    lat=lat,
                    lon=lon,
                    official_name=str(row["official_name"]),
                    stadium_name=str(row["stadium_name"]),
                    location=str(row["location"]),
                    capacity=capacity,
                    opened=opened,
                    info=str(row["info"]),
                    image_filename=image_filename,
                    has_image=(self._image_dir / image_filename).exists(),
                    timezone=str(row["timezone"]),
                    tz_label=str(row["tz_label"]),
                    altitude_m=altitude_m,
                    region_cluster=_opt(row, "region_cluster"),
                    airport_code=_opt(row, "airport_code"),
                )
            )
        return venues
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_venues.py -v`
Expected: PASS (7 tests).

- [ ] **Step 5: Commit**

```bash
git add src/data/venues.py tests/test_venues.py
git commit -m "feat: VenueRepository reads consolidated venues.csv (drops fuzzy join + timezones dict)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: `teams.csv` loaders — continents + codes + distances

**Files:**
- Modify: `src/data/team_continents.py` (point `_CSV_PATH` to `teams.csv`; add `TEAM_CODE` + `code_for`)
- Test: `tests/test_team_continents.py` (update), `tests/test_distances.py` (update path/join source)

- [ ] **Step 1: Update the failing tests**

In `tests/test_team_continents.py`:
- Add `code_for` and `TEAM_CODE` to the import line:
  ```python
  from src.data.team_continents import (
      CONTINENT_ORDER,
      TEAM_CODE,
      TEAM_CONTINENT,
      code_for,
      continent_for,
      grouped_team_options,
  )
  ```
- Replace `test_mapping_is_sourced_from_csv` with:
  ```python
  def test_mapping_is_sourced_from_csv():
      csv_path = Path(__file__).parent.parent / "assets" / "data" / "teams.csv"
      df = pd.read_csv(csv_path)
      assert {"team", "continent", "code"} <= set(df.columns)
      from_csv = {str(r["team"]): str(r["continent"]) for _, r in df.iterrows()}
      assert TEAM_CONTINENT == from_csv
  ```
- Append:
  ```python
  def test_code_for_known_and_unknown():
      assert code_for("Korea Republic") == "KOR"
      assert code_for("USA") == "USA"
      assert code_for("Côte d'Ivoire") == "CIV"
      with pytest.raises(ValueError):
          code_for("Atlantis")


  def test_team_code_map_covers_all_teams():
      assert len(TEAM_CODE) == 48
      assert all(len(c) == 3 for c in TEAM_CODE.values())
  ```

In `tests/test_distances.py`, replace the bottom integration block (from `from pathlib import Path` onward) with:
```python
from pathlib import Path

from src.data.flows import build_team_flows, path_distance_km
from src.data.matches import MatchRepository
from src.data.venues import VenueRepository

DATA = Path(__file__).parent.parent / "assets" / "data"
IMAGE_DIR = DATA.parent / "stadiums"
CSV_PATH = DATA / "teams.csv"


def test_csv_matches_recomputed_distances():
    venues = VenueRepository(DATA / "venues.csv", IMAGE_DIR).load()
    matches = MatchRepository(DATA / "matches.csv").load()
    flows = build_team_flows(matches, venues)

    on_disk = DistanceRepository(CSV_PATH).load()
    assert set(on_disk) == set(flows)
    assert len(on_disk) == 48
    for team, flow in flows.items():
        assert abs(on_disk[team] - path_distance_km(flow.stops)) < 0.1
```
(The unit tests `test_loads_distance_by_team` / `test_missing_column_raises` / `test_non_numeric_distance_raises` at the top stay unchanged — `DistanceRepository` reads any `team`,`distance_km` CSV.)

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_team_continents.py tests/test_distances.py -v`
Expected: FAIL — `ImportError: cannot import name 'code_for'` and/or `FileNotFoundError`/`KeyError` on `teams.csv`.

- [ ] **Step 3: Update `src/data/team_continents.py`**

Replace lines from `_CSV_PATH = ...` through `TEAM_CONTINENT: dict[str, str] = _load_team_continents()` with:

```python
_CSV_PATH = Path(__file__).resolve().parents[2] / "assets" / "data" / "teams.csv"


def _load_team_continents(csv_path: Path = _CSV_PATH) -> dict[str, str]:
    df = pd.read_csv(csv_path)
    missing = [c for c in ("team", "continent") if c not in df.columns]
    if missing:
        raise ValueError(f"Missing expected columns: {missing}")
    return {str(row["team"]): str(row["continent"]) for _, row in df.iterrows()}


def _load_team_codes(csv_path: Path = _CSV_PATH) -> dict[str, str]:
    df = pd.read_csv(csv_path)
    if "code" not in df.columns:
        raise ValueError("Missing expected column: code")
    return {str(row["team"]): str(row["code"]) for _, row in df.iterrows()}


# Team -> continent / FIFA code, sourced from assets/data/teams.csv.
TEAM_CONTINENT: dict[str, str] = _load_team_continents()
TEAM_CODE: dict[str, str] = _load_team_codes()
```

Then add, after `continent_for`:

```python
def code_for(team: str) -> str:
    try:
        return TEAM_CODE[team]
    except KeyError as exc:
        raise ValueError(f"No FIFA code mapped for team {team!r}") from exc
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_team_continents.py tests/test_distances.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/data/team_continents.py tests/test_team_continents.py tests/test_distances.py
git commit -m "feat: team_continents reads teams.csv and exposes FIFA codes (code_for)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: Repoint matches/squads/flows/calendar tests + `app.py` wiring

**Files:**
- Modify: `tests/test_matches.py:8`, `tests/test_squads.py:4`, `tests/test_live_reconcile.py:42`
- Modify: `tests/test_flows.py` (use `VenueRepository`/`matches.csv`), `tests/test_match_calendar.py` (same)
- Modify: `app.py` (venue/distances/matches/squads wiring + imports)

- [ ] **Step 1: Update the test fixtures' CSV paths**

- `tests/test_matches.py:8`: change `"wc2026_matches.csv"` → `"matches.csv"`.
- `tests/test_squads.py:4`: change `"world_cup_2026_squads.csv"` → `"squads.csv"`.
- `tests/test_live_reconcile.py:42`: change `Path("assets/data/wc2026_matches.csv")` → `Path("assets/data/matches.csv")`.

In `tests/test_flows.py`, replace the imports + `_venues`/`_flows` helpers (top of file through `_flows`) with:
```python
from datetime import date, datetime, time
from pathlib import Path

import pytest

from src.data.flows import FlowStop, TeamFlow, build_team_flows, team_cities, team_color
from src.data.matches import Match, MatchRepository
from src.data.venues import VenueRepository

DATA = Path(__file__).parent.parent / "assets" / "data"
IMAGE_DIR = DATA.parent / "stadiums"


def _venues():
    return VenueRepository(DATA / "venues.csv", IMAGE_DIR).load()


def _flows():
    matches = MatchRepository(DATA / "matches.csv").load()
    return build_team_flows(matches, _venues())
```
And in `test_build_team_flows_stamps_distance_from_dict`, change `MatchRepository(DATA / "wc2026_matches.csv")` → `MatchRepository(DATA / "matches.csv")`.

In `tests/test_match_calendar.py`, replace the imports + `_calendar` helper with:
```python
from datetime import date
from pathlib import Path

from src.data.match_calendar import MatchCalendar
from src.data.matches import MatchRepository
from src.data.venues import VenueRepository

DATA = Path(__file__).parent.parent / "assets" / "data"
IMAGE_DIR = DATA.parent / "stadiums"
TODAY = date(2026, 5, 30)


def _calendar(today=TODAY):
    venues = VenueRepository(DATA / "venues.csv", IMAGE_DIR).load()
    stadium_to_city = {v.stadium_name: v.city for v in venues}
    matches = MatchRepository(DATA / "matches.csv").load()
    return MatchCalendar(matches, stadium_to_city, today=today)
```

- [ ] **Step 2: Update `app.py` wiring**

- Remove imports (around lines 22, 41): `from src.data.host_cities import HostCityRepository`, `from src.data.venues import build_venues`, and any `StadiumRepository`/`AltitudeRepository` imports.
- Add import: `from src.data.venues import VenueRepository`.
- Replace lines 46-51:
  ```python
  CITIES = HostCityRepository(DATA_DIR / "fifa_2026_host_cities.csv").load()
  STADIUMS = StadiumRepository(DATA_DIR / "fifa_wc2026_stadiums.csv").load()
  ALTITUDES = AltitudeRepository(DATA_DIR / "wc2026_stadium_altitude.csv").load()
  DISTANCES = DistanceRepository(DATA_DIR / "team_distances.csv").load()
  VENUES = build_venues(CITIES, STADIUMS, IMAGE_DIR, ALTITUDES)
  VENUES_BY_CITY = {v.city: v for v in VENUES}
  ```
  with:
  ```python
  VENUES = VenueRepository(DATA_DIR / "venues.csv", IMAGE_DIR).load()
  VENUES_BY_CITY = {v.city: v for v in VENUES}
  DISTANCES = DistanceRepository(DATA_DIR / "teams.csv").load()
  ```
- Change `MatchRepository(DATA_DIR / "wc2026_matches.csv")` → `MatchRepository(DATA_DIR / "matches.csv")`.
- Change `SquadRepository(DATA_DIR / "world_cup_2026_squads.csv")` → `SquadRepository(DATA_DIR / "squads.csv")`.

- [ ] **Step 3: Run the affected tests + app import**

Run: `pytest tests/test_matches.py tests/test_squads.py tests/test_flows.py tests/test_match_calendar.py tests/test_live_reconcile.py -v`
Expected: PASS.
Run: `python -c "import app; print('app import OK')"`
Expected: `app import OK` (no missing-file / missing-import errors).

- [ ] **Step 4: Commit**

```bash
git add app.py tests/test_matches.py tests/test_squads.py tests/test_flows.py \
  tests/test_match_calendar.py tests/test_live_reconcile.py
git commit -m "refactor: repoint app + tests to consolidated CSVs; app uses VenueRepository

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: Delete dead files, modules, and tests; verify suite

**Files:**
- Delete (data): `assets/data/fifa_2026_host_cities.csv`, `fifa_wc2026_stadiums.csv`, `wc2026_stadium_altitude.csv`, `host_cities.csv`, `fifa_2026_matches.csv`, `team_continents.csv`, `team_distances.csv`, `wc2026_matches.csv`, `world_cup_2026_squads.csv`, `fifa_abbrevations.md`, `managers.md`
- Delete (code): `src/data/host_cities.py`, `src/data/stadiums.py`, `src/data/altitudes.py`, `src/data/timezones.py`
- Delete (tests): `tests/test_host_cities.py`, `tests/test_stadiums.py`, `tests/test_altitudes.py`, `tests/test_timezones.py`
- **Orphaned helper scripts (user-approved 2026-06-14):** repoint `scripts/download_stadium_images.py` to read `venues.csv` (cols `image_filename`/`image_url` instead of `Image_Filename`/`Image_URL`); delete `scripts/compute_kickoff_utc.py` and `scripts/compute_team_distances.py` (superseded — their outputs `kickoff_utc`/`distance_km` are now materialized columns in `matches.csv`/`teams.csv`, which are the source of truth). Note: `scripts/consolidate_csvs.py` is a historical migration record; after its source inputs are deleted it is no longer re-runnable, by design.

- [ ] **Step 1: Verify nothing still imports the modules to be deleted**

Run:
```bash
grep -rn "host_cities\|stadiums import\|altitudes\|timezones\|build_venues" --include="*.py" src/ app.py tests/ | grep -v "test_host_cities\|test_stadiums\|test_altitudes\|test_timezones"
```
Expected: no output. If anything prints, fix that reference before deleting (it must point at the new loaders).

- [ ] **Step 2: Delete the dead data, modules, and tests**

```bash
cd /Users/yberber/Documents/WC2026
git rm assets/data/fifa_2026_host_cities.csv assets/data/fifa_wc2026_stadiums.csv \
  assets/data/wc2026_stadium_altitude.csv assets/data/host_cities.csv \
  assets/data/fifa_2026_matches.csv assets/data/team_continents.csv \
  assets/data/team_distances.csv assets/data/wc2026_matches.csv \
  assets/data/world_cup_2026_squads.csv assets/data/fifa_abbrevations.md \
  assets/data/managers.md
git rm src/data/host_cities.py src/data/stadiums.py src/data/altitudes.py src/data/timezones.py
git rm tests/test_host_cities.py tests/test_stadiums.py tests/test_altitudes.py tests/test_timezones.py
```

- [ ] **Step 3: Run the FULL suite**

Run: `pytest tests/ -v`
Expected: all tests PASS, no errors, no collection failures. (Suite was 336 passing before; it will be lower after removing 4 test files + adding new ones — confirm 0 failures/errors, not a specific count.)

- [ ] **Step 4: Verify the app still boots**

Run: `python -c "import app; print('app import OK')"`
Expected: `app import OK`.

- [ ] **Step 5: Confirm only the 4 data CSVs remain**

Run: `ls assets/data/*.csv`
Expected: exactly `matches.csv`, `squads.csv`, `teams.csv`, `venues.csv` (plus `estimated_starting_eleven.json` is the only non-CSV data file remaining; no `.md` files).

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "chore: remove pre-consolidation CSVs, .md sources, and dead loaders/tests

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Final verification (after all tasks)

- [ ] `pytest tests/ -v` — green, zero failures/errors.
- [ ] `python -c "import app"` — succeeds.
- [ ] `assets/data/` contains exactly 4 CSVs + `estimated_starting_eleven.json`.
- [ ] `grep -rn "timezones\|build_venues\|HostCityRepository\|StadiumRepository\|AltitudeRepository" src/ app.py tests/` — no output.
- [ ] Branch remains `feat/highlightly-live-data`, unmerged.
