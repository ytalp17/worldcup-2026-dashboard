# User-Local Kickoff Times Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Anchor every date/time in the app to the visitor's local timezone — remove the static timezone string from the stadium drawer, show each match's kickoff in user-local time (venue time tagged ±Nd alongside), and make the header calendar select user-local dates.

**Architecture:** A one-time offline script precomputes each match's absolute `kickoff_utc` (venue local + DST → UTC) and overwrites the schedule CSV. At runtime a clientside callback reads the browser timezone into a `dcc.Store`; a pure `kickoff.py` module converts `kickoff_utc → user zone` for the drawer, and `MatchCalendar.active_cities` does the same for the map pulse. When the timezone is unknown, everything falls back to venue date/time.

**Tech Stack:** Python 3.11 + pandas + `zoneinfo`; Dash 2.18 + dash-mantine-components 2.4 + dash-iconify. **Runtime is conda base** — run tests with `~/anaconda3/bin/conda run -n base python -m pytest tests/ -q`.

**Spec:** `docs/superpowers/specs/2026-06-05-user-local-kickoff-times-design.md`

> **Env note:** Git repo on branch `feature/header-match-calendar`. Commit steps are real (`git`). Tests run in conda base.

---

## File Structure

| File | Responsibility |
|---|---|
| `scripts/compute_kickoff_utc.py` | **New.** Offline generator: resolve each match's venue-local kickoff + DST → UTC; overwrite `assets/data/wc2026_matches.csv` adding `kickoff_utc`. Pure `to_utc()` helper + `main()`. |
| `assets/data/wc2026_matches.csv` | **Overwritten** by the script: gains a `kickoff_utc` column. |
| `src/data/matches.py` | `Match` gains `local_time` (time) + `kickoff_utc` (UTC datetime); repo parses + validates them. |
| `src/data/kickoff.py` | **New.** Pure `KickoffView` + `kickoff_view(match, user_tz)` + `venue_offset_tag(offset)`. No Dash. |
| `src/data/match_calendar.py` | `active_cities(day, user_tz=None)` computes user-local date from `kickoff_utc` (venue-date fallback). |
| `src/components/header_calendar.py` | Pad `maxDate` by +1 day so user-local edge dates stay selectable. |
| `src/components/detail_panel.py` | Remove timezone string; render dual kickoff times; `stadium_detail(venue, matches, user_tz=None)`. |
| `src/components/layout.py` | Add `dcc.Store(id="user-tz")` + one-shot `dcc.Interval(id="tz-probe")`. |
| `app.py` | Clientside tz callback; thread `user-tz` into pulse + drawer callbacks. |

---

## Task 1: Offline `kickoff_utc` generator + CSV migration

**Files:**
- Create: `scripts/compute_kickoff_utc.py`
- Test: `tests/test_compute_kickoff_utc.py`
- Modify (by running the script): `assets/data/wc2026_matches.csv`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_compute_kickoff_utc.py
from scripts.compute_kickoff_utc import to_utc


def test_to_utc_resolves_mexico_city_no_dst():
    # America/Mexico_City is UTC-6 year-round (no DST since 2022): 13:00 -> 19:00Z.
    assert to_utc("2026-06-11", "13:00", "America/Mexico_City") == "2026-06-11T19:00:00+00:00"


def test_to_utc_resolves_us_pacific_dst():
    # America/Los_Angeles in June is PDT = UTC-7: 18:00 -> 01:00Z next day.
    assert to_utc("2026-06-12", "18:00", "America/Los_Angeles") == "2026-06-13T01:00:00+00:00"
```

- [ ] **Step 2: Run it (fails — module missing)**

Run: `~/anaconda3/bin/conda run -n base python -m pytest tests/test_compute_kickoff_utc.py -q`
Expected: FAIL `ModuleNotFoundError: No module named 'scripts.compute_kickoff_utc'`.

- [ ] **Step 3: Write the script**

```python
# scripts/compute_kickoff_utc.py
"""Offline generator: add a `kickoff_utc` column to the WC2026 match schedule.

Resolves each match's venue-local kickoff (match_date + local_time in the
stadium's IANA zone, DST-correct) to an absolute UTC instant, then OVERWRITES
assets/data/wc2026_matches.csv in place. Re-run whenever the schedule changes:

    ~/anaconda3/bin/conda run -n base python -m scripts.compute_kickoff_utc
"""
from __future__ import annotations

from datetime import datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "assets" / "data"
CSV = DATA / "wc2026_matches.csv"


def to_utc(match_date: str, local_time: str, iana_tz: str) -> str:
    """Combine a venue-local date + 'HH:MM' in `iana_tz`, return the UTC instant
    as an ISO-8601 string with a +00:00 offset."""
    d = datetime.strptime(match_date.strip(), "%Y-%m-%d").date()
    t = time.fromisoformat(local_time.strip())
    local_dt = datetime.combine(d, t, tzinfo=ZoneInfo(iana_tz))
    return local_dt.astimezone(ZoneInfo("UTC")).isoformat()


def stadium_tz_map() -> dict[str, str]:
    """Map generic FIFA stadium name -> IANA timezone, via the venue join."""
    from src.data.host_cities import HostCityRepository
    from src.data.stadiums import StadiumRepository
    from src.data.venues import build_venues

    cities = HostCityRepository(DATA / "fifa_2026_host_cities.csv").load()
    stadiums = StadiumRepository(DATA / "fifa_wc2026_stadiums.csv").load()
    venues = build_venues(cities, stadiums, DATA.parent / "stadiums")
    return {v.stadium_name: v.timezone for v in venues}


def main() -> None:
    df = pd.read_csv(CSV)
    tz_by_stadium = stadium_tz_map()
    df["kickoff_utc"] = [
        to_utc(row.match_date, row.local_time, tz_by_stadium[row.stadium])
        for row in df.itertuples(index=False)
    ]
    df.to_csv(CSV, index=False)
    print(f"Wrote kickoff_utc for {len(df)} matches -> {CSV}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run the test (passes)**

Run: `~/anaconda3/bin/conda run -n base python -m pytest tests/test_compute_kickoff_utc.py -q`
Expected: PASS (2 passed).

- [ ] **Step 5: Run the generator to migrate the CSV**

Run (as a module, so `src` is importable): `~/anaconda3/bin/conda run -n base python -m scripts.compute_kickoff_utc`
Expected: prints `Wrote kickoff_utc for 104 matches -> …/wc2026_matches.csv`.
Verify the header now ends with `…,match_date,local_time,kickoff_utc` and row 1 shows `2026-06-11T19:00:00+00:00`:
`head -2 assets/data/wc2026_matches.csv`

- [ ] **Step 6: Commit**

```bash
git add scripts/compute_kickoff_utc.py tests/test_compute_kickoff_utc.py assets/data/wc2026_matches.csv
git commit -m "feat: precompute kickoff_utc and migrate schedule CSV"
```

---

## Task 2: `Match` carries `local_time` + `kickoff_utc`

**Files:**
- Modify: `src/data/matches.py`
- Test: `tests/test_matches.py`

- [ ] **Step 1: Update/extend the tests**

In `tests/test_matches.py`, extend `test_match_types_and_known_row` and fix the bad-row fixtures. Add `from datetime import date, datetime, time` at the top (keep existing imports). Replace the two fixture-based tests and add assertions:

```python
def test_match_types_and_known_row():
    matches = _load()
    m1 = next(m for m in matches if m.number == 1)
    assert isinstance(m1, Match)
    assert m1.home == "Mexico"
    assert m1.away == "South Africa"
    assert m1.group == "Group A"
    assert m1.stage == "Group Stage"
    assert m1.stadium == "Mexico City Stadium"
    assert m1.date == date(2026, 6, 11)
    assert m1.local_time == time(13, 0)
    assert m1.kickoff_utc == datetime.fromisoformat("2026-06-11T19:00:00+00:00")


def test_missing_column_raises(tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text(
        "match_number,home_team,away_team,group,stage,stadium\n"
        "1,A,B,Group A,Group Stage,X\n"
    )
    with pytest.raises(ValueError):
        MatchRepository(bad).load()


def test_bad_date_raises(tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text(
        "match_number,home_team,away_team,group,stage,stadium,match_date,local_time,kickoff_utc\n"
        "1,A,B,Group A,Group Stage,X,not-a-date,13:00,2026-06-11T19:00:00+00:00\n"
    )
    with pytest.raises(ValueError):
        MatchRepository(bad).load()
```

- [ ] **Step 2: Run it (fails)**

Run: `~/anaconda3/bin/conda run -n base python -m pytest tests/test_matches.py -q`
Expected: FAIL — `Match` has no `local_time` / `kickoff_utc`.

- [ ] **Step 3: Implement**

In `src/data/matches.py`: change the import line `from datetime import date` to:
```python
from datetime import date, datetime, time
```
Add the two columns to `EXPECTED_COLUMNS` (after `"match_date"`):
```python
    "match_date",
    "local_time",
    "kickoff_utc",
```
Add the two fields to `Match` (after `date: date`):
```python
    local_time: time
    kickoff_utc: datetime
```
In `load()`, parse them inside the existing per-row `try` (which already raises `ValueError`):
```python
            try:
                number = int(row["match_number"])
                match_date = date.fromisoformat(str(row["match_date"]).strip())
                local_time = time.fromisoformat(str(row["local_time"]).strip())
                kickoff_utc = datetime.fromisoformat(str(row["kickoff_utc"]).strip())
            except (ValueError, TypeError) as exc:
                raise ValueError(f"Bad match row: {row.to_dict()}") from exc
```
and pass them into the `Match(...)` constructor:
```python
                Match(
                    number=number,
                    home=str(row["home_team"]),
                    away=str(row["away_team"]),
                    group=group,
                    stage=str(row["stage"]),
                    stadium=str(row["stadium"]),
                    date=match_date,
                    local_time=local_time,
                    kickoff_utc=kickoff_utc,
                )
```

- [ ] **Step 4: Run it (passes)**

Run: `~/anaconda3/bin/conda run -n base python -m pytest tests/test_matches.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/data/matches.py tests/test_matches.py
git commit -m "feat: Match carries local_time and kickoff_utc"
```

---

## Task 3: Pure `kickoff.py` conversion module

**Files:**
- Create: `src/data/kickoff.py`
- Test: `tests/test_kickoff.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_kickoff.py
from datetime import date, datetime, time

from src.data.kickoff import KickoffView, kickoff_view, venue_offset_tag
from src.data.matches import Match


def _match(local="13:00", utc="2026-06-11T19:00:00+00:00", day=11):
    return Match(
        number=1, home="Mexico", away="South Africa", group="Group A",
        stage="Group Stage", stadium="Mexico City Stadium",
        date=date(2026, 6, day),
        local_time=time.fromisoformat(local),
        kickoff_utc=datetime.fromisoformat(utc),
    )


def test_unknown_tz_falls_back_to_venue_only():
    kv = kickoff_view(_match(), None)
    assert kv == KickoffView(
        user_time=None, user_date=None, venue_time="13:00",
        venue_day_offset=0, same_clock=True,
    )


def test_bad_tz_string_falls_back():
    kv = kickoff_view(_match(), "Not/AZone")
    assert kv.user_time is None and kv.same_clock is True


def test_same_zone_collapses_to_single_time():
    # Viewer in the venue's own zone: same clock, no offset.
    kv = kickoff_view(_match(), "America/Mexico_City")
    assert kv.user_time == "13:00"
    assert kv.venue_time == "13:00"
    assert kv.venue_day_offset == 0
    assert kv.same_clock is True


def test_eastward_viewer_crosses_to_next_day():
    # 13:00 Mexico City (19:00Z) seen from Tokyo (UTC+9) -> 04:00 next day.
    kv = kickoff_view(_match(), "Asia/Tokyo")
    assert kv.user_time == "04:00"
    assert kv.user_date == date(2026, 6, 12)
    # venue day (Jun 11) is one behind the user's day (Jun 12).
    assert kv.venue_day_offset == -1
    assert kv.same_clock is False


def test_venue_offset_tag_formatting():
    assert venue_offset_tag(0) == ""
    assert venue_offset_tag(-1) == "(-1d)"
    assert venue_offset_tag(1) == "(+1d)"
    assert venue_offset_tag(2) == "(+2d)"
```

- [ ] **Step 2: Run it (fails)**

Run: `~/anaconda3/bin/conda run -n base python -m pytest tests/test_kickoff.py -q`
Expected: FAIL `ModuleNotFoundError: No module named 'src.data.kickoff'`.

- [ ] **Step 3: Implement**

```python
# src/data/kickoff.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from src.data.matches import Match


@dataclass(frozen=True)
class KickoffView:
    user_time: str | None     # "HH:MM" in the user's zone (None if tz unknown)
    user_date: date | None    # user-local date (None if tz unknown)
    venue_time: str           # "HH:MM" venue clock
    venue_day_offset: int     # venue_date - user_local_date, in days
    same_clock: bool          # True when tz unknown OR identical clock+day


def kickoff_view(match: Match, user_tz: str | None) -> KickoffView:
    """Resolve a match's kickoff into the viewer's zone. Falls back to
    venue-only (same_clock=True) when the timezone is missing or invalid."""
    venue_time = match.local_time.strftime("%H:%M")
    if not user_tz:
        return KickoffView(None, None, venue_time, 0, True)
    try:
        zone = ZoneInfo(user_tz)
    except (ZoneInfoNotFoundError, ValueError):
        return KickoffView(None, None, venue_time, 0, True)

    local = match.kickoff_utc.astimezone(zone)
    user_time = local.strftime("%H:%M")
    user_date = local.date()
    venue_day_offset = (match.date - user_date).days
    same_clock = user_time == venue_time and venue_day_offset == 0
    return KickoffView(user_time, user_date, venue_time, venue_day_offset, same_clock)


def venue_offset_tag(offset: int) -> str:
    """e.g. -1 -> '(-1d)', +2 -> '(+2d)', 0 -> ''."""
    if offset == 0:
        return ""
    return f"({'+' if offset > 0 else '-'}{abs(offset)}d)"
```

- [ ] **Step 4: Run it (passes)**

Run: `~/anaconda3/bin/conda run -n base python -m pytest tests/test_kickoff.py -q`
Expected: PASS (5 passed).

- [ ] **Step 5: Commit**

```bash
git add src/data/kickoff.py tests/test_kickoff.py
git commit -m "feat: pure kickoff_view conversion (user-local vs venue, ±Nd)"
```

---

## Task 4: `MatchCalendar.active_cities` honors user timezone

**Files:**
- Modify: `src/data/match_calendar.py`
- Test: `tests/test_match_calendar.py`

- [ ] **Step 1: Add failing tests**

Append to `tests/test_match_calendar.py`:

```python
def test_active_cities_user_tz_shifts_match_to_next_day():
    cal = _calendar()
    # Opening matches are Jun 11 in venue time; from Tokyo they fall on Jun 12.
    assert "Mexico City" not in cal.active_cities(date(2026, 6, 11), "Asia/Tokyo")
    assert "Mexico City" in cal.active_cities(date(2026, 6, 12), "Asia/Tokyo")


def test_active_cities_user_tz_none_uses_venue_dates():
    cal = _calendar()
    assert cal.active_cities(date(2026, 6, 11), None) == {"Mexico City", "Guadalajara"}
```

- [ ] **Step 2: Run it (fails)**

Run: `~/anaconda3/bin/conda run -n base python -m pytest tests/test_match_calendar.py -q`
Expected: FAIL — `active_cities()` takes 1 positional arg / no `user_tz`.

- [ ] **Step 3: Implement**

In `src/data/match_calendar.py`, add imports and keep per-match kickoff data. Replace the file body with:

```python
from __future__ import annotations

from datetime import date
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from src.data.matches import Match


class MatchCalendar:
    """Tournament calendar derived from the match schedule. Knows the date
    range, which days have matches, and which host cities are active on a given
    day — by venue date, or by the viewer's local date when a timezone is given."""

    def __init__(
        self,
        matches: list[Match],
        stadium_to_city: dict[str, str],
        today: date,
    ) -> None:
        self._today = today
        self._cities_by_date: dict[date, set[str]] = {}
        # (kickoff_utc, city) for the user-local computation.
        self._kickoffs: list[tuple] = []
        for m in matches:
            city = stadium_to_city.get(m.stadium)
            if not city:
                continue
            self._cities_by_date.setdefault(m.date, set()).add(city)
            self._kickoffs.append((m.kickoff_utc, city))
        self._end = max(self._cities_by_date) if self._cities_by_date else today

    @property
    def start(self) -> date:
        return self._today

    @property
    def end(self) -> date:
        return self._end

    @property
    def match_dates(self) -> set[date]:
        return set(self._cities_by_date)

    def active_cities(self, day: date, user_tz: str | None = None) -> set[str]:
        """Host cities with a match on `day`. With `user_tz`, `day` is compared
        against each kickoff converted to that zone; otherwise against the venue
        date. Unknown/invalid `user_tz` falls back to venue dates."""
        if user_tz:
            try:
                zone = ZoneInfo(user_tz)
            except (ZoneInfoNotFoundError, ValueError):
                zone = None
            if zone is not None:
                return {
                    city for kickoff_utc, city in self._kickoffs
                    if kickoff_utc.astimezone(zone).date() == day
                }
        return set(self._cities_by_date.get(day, set()))
```

- [ ] **Step 4: Run it (passes)**

Run: `~/anaconda3/bin/conda run -n base python -m pytest tests/test_match_calendar.py -q`
Expected: PASS (existing + 2 new).

- [ ] **Step 5: Commit**

```bash
git add src/data/match_calendar.py tests/test_match_calendar.py
git commit -m "feat: MatchCalendar.active_cities honors user timezone"
```

---

## Task 5: Pad the header calendar's selectable range

**Files:**
- Modify: `src/components/header_calendar.py`
- Test: `tests/test_header_calendar.py`

- [ ] **Step 1: Update the test**

Replace `test_minicalendar_has_range_value_and_window` in `tests/test_header_calendar.py` with:

```python
def test_minicalendar_has_range_value_and_window():
    mc = build_match_calendar(_FakeCalendar())
    assert isinstance(mc, dmc.MiniCalendar)
    assert mc.id == CALENDAR_ID
    assert mc.value == "2026-05-30"
    assert mc.minDate == "2026-05-30"
    # maxDate is padded one day past the final venue day so user-local edge
    # dates (late-night kickoffs that roll to the next day) stay selectable.
    assert mc.maxDate == "2026-07-20"
    assert mc.numberOfDays == 10
```

- [ ] **Step 2: Run it (fails)**

Run: `~/anaconda3/bin/conda run -n base python -m pytest tests/test_header_calendar.py -q`
Expected: FAIL — `maxDate == "2026-07-19"`.

- [ ] **Step 3: Implement**

In `src/components/header_calendar.py`: add `from datetime import timedelta` at the top, and change the `maxDate` line in `build_match_calendar`:
```python
        maxDate=(calendar.end + timedelta(days=1)).isoformat(),
```

- [ ] **Step 4: Run it (passes)**

Run: `~/anaconda3/bin/conda run -n base python -m pytest tests/test_header_calendar.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/components/header_calendar.py tests/test_header_calendar.py
git commit -m "feat: pad calendar maxDate +1 day for user-local edge dates"
```

---

## Task 6: Drawer shows dual kickoff times, no timezone string

**Files:**
- Modify: `src/components/detail_panel.py`
- Test: `tests/test_detail_panel.py`

- [ ] **Step 1: Update the tests**

In `tests/test_detail_panel.py`: (a) update the `_match` helper to build the new `Match` fields; (b) replace `test_detail_shows_timezone` with a "no timezone string" test; (c) add dual-time tests. Add `datetime, time` to the datetime import.

Change the import line to:
```python
from datetime import date, datetime, time
```
Replace the `_match` helper:
```python
def _match(number, home, away, group, stage, day, local="13:00",
           utc="2026-06-11T19:00:00+00:00"):
    return Match(
        number=number,
        home=home,
        away=away,
        group=group,
        stage=stage,
        stadium="Dallas Stadium",
        date=date(2026, 6, day),
        local_time=time.fromisoformat(local),
        kickoff_utc=datetime.fromisoformat(utc),
    )
```
Replace `test_detail_shows_timezone` with:
```python
def test_detail_no_longer_shows_timezone_string():
    content = dmc.Box(stadium_detail(_venue(has_image=True)))
    text = _all_text(content)
    assert "America/Chicago" not in text
    assert "UTC" not in text
```
Append dual-time tests:
```python
def test_match_shows_venue_only_when_tz_unknown():
    matches = [_match(1, "Mexico", "South Africa", "Group A", "Group Stage", 11)]
    content = dmc.Box(stadium_detail(_venue(has_image=True), matches, user_tz=None))
    text = _all_text(content)
    assert "13:00" in text
    assert "your time" not in text


def test_match_shows_dual_times_with_offset_tag():
    # 13:00 Mexico-City kickoff seen from Tokyo -> 04:00 next day, venue (-1d).
    matches = [_match(1, "Mexico", "South Africa", "Group A", "Group Stage", 11)]
    content = dmc.Box(stadium_detail(_venue(has_image=True), matches, user_tz="Asia/Tokyo"))
    text = _all_text(content)
    assert "04:00" in text          # user-local kickoff
    assert "your time" in text
    assert "13:00" in text          # venue kickoff
    assert "(-1d)" in text          # venue day behind the user's day
    assert "Asia/Tokyo" in text     # zone named in the section note
    assert "Jun 12" in text         # title uses the user-local date


def test_match_same_zone_shows_single_time():
    matches = [_match(1, "Mexico", "South Africa", "Group A", "Group Stage", 11)]
    content = dmc.Box(
        stadium_detail(_venue(has_image=True), matches, user_tz="America/Mexico_City")
    )
    text = _all_text(content)
    assert text.count("13:00") == 1
    assert "your time" not in text
```

- [ ] **Step 2: Run it (fails)**

Run: `~/anaconda3/bin/conda run -n base python -m pytest tests/test_detail_panel.py -q`
Expected: FAIL — `_timezone_text` still renders / `stadium_detail` has no `user_tz`.

- [ ] **Step 3: Implement**

In `src/components/detail_panel.py`:

1. Replace the imports block (drop `datetime`/`zoneinfo`, add date + kickoff):
```python
from __future__ import annotations

from collections.abc import Sequence

import dash_mantine_components as dmc
from dash_iconify import DashIconify

from src.data.kickoff import kickoff_view, venue_offset_tag
from src.data.matches import Match, is_placeholder
from src.data.venues import Venue
```

2. Delete the `_timezone_text` function entirely.

3. Replace `_match_item` and add a kickoff-line helper:
```python
def _kickoff_line(match: Match, user_tz: str | None):
    kv = kickoff_view(match, user_tz)
    if kv.same_clock:
        return dmc.Group(
            [
                DashIconify(icon="tabler:building-stadium", width=14),
                dmc.Text(f"{kv.venue_time} local", size="xs", c="dimmed"),
            ],
            gap=4,
            align="center",
            wrap="nowrap",
        )
    tag = venue_offset_tag(kv.venue_day_offset)
    venue_text = f"{kv.venue_time} venue {tag}".strip()
    return dmc.Group(
        [
            DashIconify(icon="tabler:world", width=14),
            dmc.Text(f"{kv.user_time} your time", size="xs", fw=500),
            dmc.Text("·", size="xs", c="dimmed"),
            DashIconify(icon="tabler:building-stadium", width=14),
            dmc.Text(venue_text, size="xs", c="dimmed"),
        ],
        gap=4,
        align="center",
        wrap="nowrap",
    )


def _match_item(match: Match, user_tz: str | None) -> dmc.TimelineItem:
    kv = kickoff_view(match, user_tz)
    day = kv.user_date or match.date  # user-local date is the anchor when known
    title = f"{day.strftime('%b')} {day.day} · {_match_label(match)}"
    return dmc.TimelineItem(
        title=title,
        bullet=DashIconify(icon="tabler:ball-football", width=12),
        children=[
            dmc.Text(
                [_team_span(match.home), " vs ", _team_span(match.away)],
                size="sm",
            ),
            _kickoff_line(match, user_tz),
        ],
    )
```

4. Update `_matches_section` to take `user_tz` and add the zone note:
```python
def _matches_section(matches: Sequence[Match], user_tz: str | None):
    header = dmc.Group(
        [
            dmc.Text("Matches", fw=600),
            dmc.Badge(str(len(matches)), variant="light", color="grape", size="sm"),
        ],
        gap="xs",
        align="center",
    )
    note_text = (
        f"Times in your timezone ({user_tz}), with venue time alongside"
        if user_tz
        else "Times in venue-local time"
    )
    note = dmc.Text(note_text, size="xs", c="dimmed")
    if not matches:
        body = dmc.Text(NO_MATCHES_TEXT, size="sm", c="dimmed")
    else:
        body = dmc.Timeline(
            [_match_item(m, user_tz) for m in matches],
            active=len(matches),
            bulletSize=20,
            lineWidth=2,
        )
    return dmc.Stack([header, note, body], gap="sm")
```

5. Replace `stadium_detail` — drop the timezone `Group`, add `user_tz`:
```python
def stadium_detail(venue: Venue, matches: Sequence[Match] = (), user_tz: str | None = None):
    """Drawer body: photo, location, key stats, info, and the schedule of
    matches at this stadium (kickoffs shown in the user's timezone)."""
    return dmc.Stack(
        [
            _image_block(venue),
            dmc.Text(venue.location, size="sm", c="dimmed"),
            dmc.Group(_stat_badges(venue), gap="sm"),
            dmc.Text(venue.info, size="sm"),
            dmc.Divider(),
            _matches_section(matches, user_tz),
        ],
        gap="md",
    )
```

- [ ] **Step 4: Run it (passes)**

Run: `~/anaconda3/bin/conda run -n base python -m pytest tests/test_detail_panel.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/components/detail_panel.py tests/test_detail_panel.py
git commit -m "feat: drawer shows user-local + venue kickoff times; drop tz string"
```

---

## Task 7: Detect timezone + thread it through the app

**Files:**
- Modify: `src/components/layout.py`
- Modify: `app.py`
- Test: `tests/test_layout.py`, `tests/test_app.py`

- [ ] **Step 1: Add failing tests**

Append to `tests/test_layout.py`:
```python
def test_layout_has_user_tz_store_and_probe():
    from dash import dcc

    layout = build_layout(VENUES)
    stores = {getattr(n, "id", None) for n in _walk(layout) if isinstance(n, dcc.Store)}
    intervals = {getattr(n, "id", None) for n in _walk(layout) if isinstance(n, dcc.Interval)}
    assert "user-tz" in stores
    assert "tz-probe" in intervals
```

Append to `tests/test_app.py`:
```python
def test_active_cities_decider_threads_user_tz():
    import app

    # In Time mode, an unknown/None tz keeps the venue-date pulse behavior.
    assert app.pulse_children_for_mode(False, "2026-06-11", 0) is not None


def test_drawer_for_city_accepts_user_tz():
    import app

    opened, title, children = app.drawer_for_city("Dallas", "Asia/Tokyo")
    assert opened is True
    assert children is not None
```

- [ ] **Step 2: Run them (fail)**

Run: `~/anaconda3/bin/conda run -n base python -m pytest tests/test_layout.py tests/test_app.py -q`
Expected: FAIL — no `user-tz`/`tz-probe`; `drawer_for_city` takes 1 arg.

- [ ] **Step 3: Implement layout**

In `src/components/layout.py`, the `MantineProvider` children list already contains a `dcc.Store(id="carousel-index", …)`. Add the store + interval beside it:
```python
    return dmc.MantineProvider(
        [
            shell,
            drawer,
            filter_drawer,
            dcc.Store(id="carousel-index", data=0, storage_type="local"),
            dcc.Store(id="user-tz"),
            dcc.Interval(id="tz-probe", interval=1, max_intervals=1),
        ],
        id="mantine-provider",
        defaultColorScheme=DEFAULT_COLOR_SCHEME,
    )
```

- [ ] **Step 4: Implement app wiring**

In `app.py`:

(a) Add the clientside callback near the other `clientside_callback` (after it is fine). It reads the browser zone into the store:
```python
clientside_callback(
    """
    function(_) {
        try { return Intl.DateTimeFormat().resolvedOptions().timeZone || null; }
        catch (e) { return null; }
    }
    """,
    Output("user-tz", "data"),
    Input("tz-probe", "n_intervals"),
)
```

(b) Thread `user_tz` into the pulse decider + callback. Replace `_active_cities_for_date`, `pulse_children_for_mode`, and `update_pulse_layer`:
```python
def _active_cities_for_date(selected_date: str | None, user_tz: str | None) -> set[str]:
    """Host cities with a match on the selected date, in the user's timezone
    (falls back to venue dates when the timezone is unknown)."""
    if not selected_date:
        return set()
    try:
        day = date.fromisoformat(str(selected_date)[:10])
    except ValueError:
        return set()
    return MATCH_CALENDAR.active_cities(day, user_tz)


def pulse_children_for_mode(team_mode, selected_date, index, user_tz=None):
    """Team mode → centered team's cities; Time mode → the date's active cities
    in the user's timezone. `user_tz` defaults to None so existing 3-arg callers
    (and tests) keep the venue-date behavior."""
    if team_mode:
        center = center_team(TEAM_NAMES, index if index is not None else 0)
        active = team_cities(TEAM_FLOWS[center], STADIUM_TO_CITY)
    else:
        active = _active_cities_for_date(selected_date, user_tz)
    return pulse_markers(VENUES, active)


@callback(
    Output("pulse-layer", "children"),
    Input("mode-toggle", "checked"),
    Input("match-calendar", "value"),
    Input("carousel-index", "data"),
    Input("user-tz", "data"),
)
def update_pulse_layer(team_mode, selected_date, index, user_tz):
    return pulse_children_for_mode(team_mode, selected_date, index, user_tz)
```

(c) Thread `user_tz` into the drawer. Update `drawer_for_city` and `open_stadium_drawer`:
```python
def drawer_for_city(city: str | None, user_tz: str | None = None):
    """Compute the (opened, title, children) drawer state for a clicked city."""
    venue = VENUES_BY_CITY.get(city) if city else None
    if venue is None:
        return False, no_update, no_update
    matches = MATCHES_BY_STADIUM.get(venue.stadium_name, [])
    return True, venue.official_name, stadium_detail(venue, matches, user_tz)
```
In `open_stadium_drawer`, add the `State` and pass it through (keep the existing decorator Outputs/Inputs, add the State line and use it):
```python
@callback(
    Output("stadium-drawer", "opened"),
    Output("stadium-drawer", "title"),
    Output("stadium-drawer", "children"),
    Output("filter-drawer", "opened", allow_duplicate=True),
    Input({"type": MARKER_TYPE, "index": ALL}, "n_clicks"),
    State("user-tz", "data"),
    prevent_initial_call=True,
)
def open_stadium_drawer(n_clicks, user_tz):
    if not any(n_clicks):
        return no_update, no_update, no_update, no_update
    triggered = ctx.triggered_id
    city = triggered.get("index") if isinstance(triggered, dict) else None
    opened, title, children = drawer_for_city(city, user_tz)
    return opened, title, children, (False if opened else no_update)
```
Ensure `State` is in the dash import (it already is from the carousel work).

- [ ] **Step 5: Run tests + boot check**

Run: `~/anaconda3/bin/conda run -n base python -m pytest tests/ -q`
Expected: PASS (full suite).
Run: `~/anaconda3/bin/conda run -n base python -c "import app; print('OK', type(app.app.layout).__name__)"`
Expected: `OK MantineProvider`, no traceback.

- [ ] **Step 6: Commit**

```bash
git add src/components/layout.py app.py tests/test_layout.py tests/test_app.py
git commit -m "feat: detect browser timezone and thread it into pulses + drawer"
```

---

## Final verification

- [ ] Full suite green: `~/anaconda3/bin/conda run -n base python -m pytest tests/ -q`.
- [ ] App boots: `~/anaconda3/bin/conda run -n base python -c "import app; print(app.app.layout.id)"`.
- [ ] Manual smoke (`~/anaconda3/bin/conda run -n base python app.py`): open a stadium drawer — the old `Pacific Time · UTC… · America/…` line is gone; each match shows "your time" + "venue (±Nd)"; the section note names your zone. Pick a date in the header calendar — stadiums pulse on your local date.
```
