# Team Travel Distance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Precompute each team's total group-stage travel distance offline into a CSV, then display it per-team (legend + map hover) and as a static longest/shortest leaderboard in the flow drawer.

**Architecture:** The haversine math is pure functions in `flows.py`, run offline by a generator script that writes `assets/data/team_distances.csv`. At runtime the app loads that CSV (zero math) and stamps a `distance_km` field onto each `TeamFlow` — mirroring how `build_venues` consumes `altitudes`. Display surfaces read `flow.distance_km` through a shared `format_distance` formatter.

**Tech Stack:** Python 3.11, pandas, Plotly Dash, dash-leaflet, dash-mantine-components, pytest.

**Conventions:** `python3` below is the Framework 3.11 interpreter (`/Library/Frameworks/Python.framework/Versions/3.11/bin/python3`). All tests import from `src...`. Run from repo root `/Users/yberber/Documents/WC2026`.

---

### Task 1: Haversine + path distance (pure math)

**Files:**
- Modify: `src/data/flows.py`
- Test: `tests/test_flows.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_flows.py`:

```python
from src.data.flows import haversine_km, path_distance_km


def test_haversine_zero_for_same_point():
    assert haversine_km(40.0, -74.0, 40.0, -74.0) == 0.0


def test_haversine_known_pair_nyc_to_la():
    # NYC (40.7128,-74.0060) -> LA (34.0522,-118.2437) ~= 3936 km
    d = haversine_km(40.7128, -74.0060, 34.0522, -118.2437)
    assert abs(d - 3936) < 20


def test_path_distance_sums_consecutive_legs():
    stops = (
        FlowStop(40.7128, -74.0060, "A", date(2026, 6, 1), 1),
        FlowStop(34.0522, -118.2437, "B", date(2026, 6, 2), 2),
        FlowStop(40.7128, -74.0060, "C", date(2026, 6, 3), 3),
    )
    leg = haversine_km(40.7128, -74.0060, 34.0522, -118.2437)
    assert abs(path_distance_km(stops) - 2 * leg) < 1e-6


def test_path_distance_zero_or_one_stop_is_zero():
    assert path_distance_km(()) == 0.0
    assert path_distance_km((FlowStop(0, 0, "A", date(2026, 6, 1), 1),)) == 0.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_flows.py -k "haversine or path_distance" -v`
Expected: FAIL with `ImportError: cannot import name 'haversine_km'`.

- [ ] **Step 3: Write minimal implementation**

In `src/data/flows.py`, add `import math` near the top imports, and add these functions after the `team_color` function (before the `FlowStop` dataclass):

```python
_EARTH_RADIUS_KM = 6371.0


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two points in kilometres."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * _EARTH_RADIUS_KM * math.asin(math.sqrt(a))
```

`path_distance_km` references `FlowStop`, so add it after the `FlowStop` dataclass definition:

```python
def path_distance_km(stops: tuple[FlowStop, ...]) -> float:
    """Total great-circle distance along an ordered sequence of stops."""
    return sum(
        haversine_km(a.lat, a.lon, b.lat, b.lon)
        for a, b in zip(stops, stops[1:])
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_flows.py -k "haversine or path_distance" -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add src/data/flows.py tests/test_flows.py
git commit -m "feat: haversine and path-distance helpers"
```

---

### Task 2: `distance_km` field on TeamFlow + `distances` param on build

**Files:**
- Modify: `src/data/flows.py`
- Test: `tests/test_flows.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_flows.py`:

```python
def test_build_team_flows_stamps_distance_from_dict():
    flows = build_team_flows(
        MatchRepository(DATA / "wc2026_matches.csv").load(),
        _venues(),
        distances={"Brazil": 1839.7},
    )
    assert flows["Brazil"].distance_km == 1839.7
    # A team absent from the dict keeps the default.
    assert flows["Mexico"].distance_km == 0.0


def test_build_team_flows_distance_defaults_to_zero():
    assert all(f.distance_km == 0.0 for f in _flows().values())
```

Also add a `_venues()` helper near `_flows()` at the top of the file (so both tests share venue construction):

```python
def _venues():
    cities = HostCityRepository(DATA / "fifa_2026_host_cities.csv").load()
    stadiums = StadiumRepository(DATA / "fifa_wc2026_stadiums.csv").load()
    return build_venues(cities, stadiums, IMAGE_DIR)
```

And refactor the existing `_flows()` to reuse it:

```python
def _flows():
    matches = MatchRepository(DATA / "wc2026_matches.csv").load()
    return build_team_flows(matches, _venues())
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_flows.py -k "distance_from_dict or distance_defaults" -v`
Expected: FAIL — `TypeError: build_team_flows() got an unexpected keyword argument 'distances'` (and/or `distance_km` attribute error).

- [ ] **Step 3: Write minimal implementation**

In `src/data/flows.py`, add the field to `TeamFlow` (after `stops`):

```python
@dataclass(frozen=True)
class TeamFlow:
    team: str
    continent: str
    color: str
    stops: tuple[FlowStop, ...]
    distance_km: float = 0.0
```

Update `build_team_flows` signature and the `flows[team] = ...` line:

```python
def build_team_flows(
    matches: list[Match],
    venues: list[Venue],
    distances: dict[str, float] | None = None,
) -> dict[str, TeamFlow]:
    venue_by_name = {v.stadium_name: v for v in venues}
    by_team: dict[str, list[Match]] = defaultdict(list)
    for m in matches:
        if m.stage != "Group Stage":
            continue
        by_team[m.home].append(m)
        by_team[m.away].append(m)

    distances = distances or {}
    flows: dict[str, TeamFlow] = {}
    for team, team_matches in by_team.items():
        stops: list[FlowStop] = []
        for m in sorted(team_matches, key=lambda x: (x.date, x.number)):
            venue = venue_by_name.get(m.stadium)
            if venue is None:
                raise ValueError(f"No venue for stadium {m.stadium!r}")
            stops.append(FlowStop(venue.lat, venue.lon, m.stadium, m.date, m.number))
        flows[team] = TeamFlow(
            team,
            continent_for(team),
            team_color(team),
            tuple(stops),
            distances.get(team, 0.0),
        )
    return flows
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_flows.py -v`
Expected: PASS (all flows tests, including the pre-existing ones).

- [ ] **Step 5: Commit**

```bash
git add src/data/flows.py tests/test_flows.py
git commit -m "feat: TeamFlow.distance_km populated from distances dict"
```

---

### Task 3: `format_distance` shared formatter

**Files:**
- Modify: `src/data/flows.py`
- Test: `tests/test_flows.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_flows.py`:

```python
from src.data.flows import format_distance


def test_format_distance_km_and_miles():
    # 1839.7 km -> 1840 km, 1143 mi, with thousands separators.
    assert format_distance(1839.7) == "1,840 km / 1,143 mi"


def test_format_distance_small_value():
    # 500 km -> 311 mi
    assert format_distance(500.0) == "500 km / 311 mi"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_flows.py -k "format_distance" -v`
Expected: FAIL with `ImportError: cannot import name 'format_distance'`.

- [ ] **Step 3: Write minimal implementation**

In `src/data/flows.py`, add after `path_distance_km`:

```python
_KM_TO_MILES = 0.621371


def format_distance(km: float) -> str:
    """Human-readable distance, e.g. '1,840 km / 1,143 mi'."""
    miles = km * _KM_TO_MILES
    return f"{round(km):,} km / {round(miles):,} mi"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_flows.py -k "format_distance" -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add src/data/flows.py tests/test_flows.py
git commit -m "feat: format_distance km/miles formatter"
```

---

### Task 4: `rank_by_distance` leaderboard helper

**Files:**
- Modify: `src/data/flows.py`
- Test: `tests/test_flows.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_flows.py`:

```python
from src.data.flows import rank_by_distance


def _flow_with(team, km):
    return TeamFlow(team, "Europe", "#fff", (), km)


def test_rank_by_distance_longest_and_shortest():
    flows = {
        "A": _flow_with("A", 100.0),
        "B": _flow_with("B", 500.0),
        "C": _flow_with("C", 300.0),
        "D": _flow_with("D", 50.0),
    }
    longest, shortest = rank_by_distance(flows, n=2)
    assert [f.team for f in longest] == ["B", "C"]
    assert [f.team for f in shortest] == ["D", "A"]


def test_rank_by_distance_caps_at_available():
    flows = {"A": _flow_with("A", 100.0)}
    longest, shortest = rank_by_distance(flows, n=5)
    assert [f.team for f in longest] == ["A"]
    assert [f.team for f in shortest] == ["A"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_flows.py -k "rank_by_distance" -v`
Expected: FAIL with `ImportError: cannot import name 'rank_by_distance'`.

- [ ] **Step 3: Write minimal implementation**

In `src/data/flows.py`, add at the end of the file:

```python
def rank_by_distance(
    team_flows: dict[str, TeamFlow], n: int = 5
) -> tuple[list[TeamFlow], list[TeamFlow]]:
    """Return (n longest, n shortest) flows by distance_km."""
    ordered = sorted(team_flows.values(), key=lambda f: f.distance_km, reverse=True)
    longest = ordered[:n]
    shortest = list(reversed(ordered[-n:])) if ordered else []
    return longest, shortest
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_flows.py -k "rank_by_distance" -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add src/data/flows.py tests/test_flows.py
git commit -m "feat: rank_by_distance longest/shortest helper"
```

---

### Task 5: `DistanceRepository` CSV loader

**Files:**
- Create: `src/data/distances.py`
- Test: `tests/test_distances.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_distances.py`:

```python
import pytest

from src.data.distances import DistanceRepository


def test_loads_distance_by_team(tmp_path):
    csv = tmp_path / "d.csv"
    csv.write_text("team,distance_km\nBrazil,1839.7\nMexico,420.0\n")
    distances = DistanceRepository(csv).load()
    assert distances == {"Brazil": 1839.7, "Mexico": 420.0}
    assert all(isinstance(v, float) for v in distances.values())


def test_missing_column_raises(tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text("team,foo\nBrazil,1\n")
    with pytest.raises(ValueError):
        DistanceRepository(bad).load()


def test_non_numeric_distance_raises(tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text("team,distance_km\nBrazil,far\n")
    with pytest.raises(ValueError):
        DistanceRepository(bad).load()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_distances.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.data.distances'`.

- [ ] **Step 3: Write minimal implementation**

Create `src/data/distances.py`:

```python
from __future__ import annotations

from pathlib import Path

import pandas as pd

REQUIRED_COLUMNS = ["team", "distance_km"]


class DistanceRepository:
    """Loads precomputed team travel distances (km) keyed by team name."""

    def __init__(self, csv_path: str | Path) -> None:
        self._csv_path = Path(csv_path)

    def load(self) -> dict[str, float]:
        df = pd.read_csv(self._csv_path)

        missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
        if missing:
            raise ValueError(f"Missing expected columns: {missing}")

        distances: dict[str, float] = {}
        for _, row in df.iterrows():
            try:
                distances[str(row["team"])] = float(row["distance_km"])
            except (ValueError, TypeError) as exc:
                raise ValueError(f"Non-numeric distance in row: {row.to_dict()}") from exc
        return distances
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_distances.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add src/data/distances.py tests/test_distances.py
git commit -m "feat: DistanceRepository CSV loader"
```

---

### Task 6: Generator script + produce the CSV

**Files:**
- Create: `scripts/compute_team_distances.py`
- Create (generated): `assets/data/team_distances.csv`

- [ ] **Step 1: Write the generator script**

Create `scripts/compute_team_distances.py`:

```python
"""Precompute each team's group-stage travel distance into a CSV.

Run from the repo root:  python3 scripts/compute_team_distances.py
Regenerate this whenever the match schedule or venues change.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.data.flows import build_team_flows, path_distance_km  # noqa: E402
from src.data.host_cities import HostCityRepository  # noqa: E402
from src.data.matches import MatchRepository  # noqa: E402
from src.data.stadiums import StadiumRepository  # noqa: E402
from src.data.venues import build_venues  # noqa: E402

DATA = ROOT / "assets" / "data"
IMAGE_DIR = ROOT / "assets" / "stadiums"
OUT = DATA / "team_distances.csv"


def main() -> None:
    cities = HostCityRepository(DATA / "fifa_2026_host_cities.csv").load()
    stadiums = StadiumRepository(DATA / "fifa_wc2026_stadiums.csv").load()
    venues = build_venues(cities, stadiums, IMAGE_DIR)
    matches = MatchRepository(DATA / "wc2026_matches.csv").load()
    flows = build_team_flows(matches, venues)

    rows = [
        {"team": team, "distance_km": round(path_distance_km(flow.stops), 1)}
        for team, flow in flows.items()
    ]
    df = pd.DataFrame(rows).sort_values("team").reset_index(drop=True)
    df.to_csv(OUT, index=False)
    print(f"Wrote {len(df)} rows to {OUT}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run the script to generate the CSV**

Run: `python3 scripts/compute_team_distances.py`
Expected: prints `Wrote 48 rows to .../assets/data/team_distances.csv`.

- [ ] **Step 3: Sanity-check the output**

Run: `python3 -c "from src.data.distances import DistanceRepository; from pathlib import Path; d=DistanceRepository(Path('assets/data/team_distances.csv')).load(); print(len(d), d['Brazil'])"`
Expected: `48` and a positive Brazil distance (> 0).

- [ ] **Step 4: Commit**

```bash
git add scripts/compute_team_distances.py assets/data/team_distances.csv
git commit -m "feat: generate team_distances.csv from schedule"
```

---

### Task 7: CSV consistency test (single source of truth)

**Files:**
- Modify: `tests/test_distances.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_distances.py`:

```python
from pathlib import Path

from src.data.flows import build_team_flows, path_distance_km
from src.data.host_cities import HostCityRepository
from src.data.matches import MatchRepository
from src.data.stadiums import StadiumRepository
from src.data.venues import build_venues

DATA = Path(__file__).parent.parent / "assets" / "data"
IMAGE_DIR = DATA.parent / "stadiums"
CSV_PATH = DATA / "team_distances.csv"


def test_csv_matches_recomputed_distances():
    cities = HostCityRepository(DATA / "fifa_2026_host_cities.csv").load()
    stadiums = StadiumRepository(DATA / "fifa_wc2026_stadiums.csv").load()
    venues = build_venues(cities, stadiums, IMAGE_DIR)
    matches = MatchRepository(DATA / "wc2026_matches.csv").load()
    flows = build_team_flows(matches, venues)

    on_disk = DistanceRepository(CSV_PATH).load()
    assert set(on_disk) == set(flows)
    assert len(on_disk) == 48
    for team, flow in flows.items():
        assert abs(on_disk[team] - path_distance_km(flow.stops)) < 0.1
```

- [ ] **Step 2: Run test to verify it passes immediately**

Run: `python3 -m pytest tests/test_distances.py::test_csv_matches_recomputed_distances -v`
Expected: PASS — this is a regression guard; the CSV was just generated from the same source, so it confirms consistency rather than driving new code. (If it FAILS, the committed CSV is stale — rerun Task 6 Step 2.)

- [ ] **Step 3: Commit**

```bash
git add tests/test_distances.py
git commit -m "test: guard team_distances.csv against the live schedule"
```

---

### Task 8: Wire distances into the app

**Files:**
- Modify: `app.py`
- Modify: `src/components/layout.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_app_distances.py`:

```python
import app


def test_app_flows_carry_distance():
    assert app.TEAM_FLOWS["Brazil"].distance_km > 0
    assert hasattr(app, "DISTANCES")
    assert len(app.DISTANCES) == 48
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_app_distances.py -v`
Expected: FAIL — `AttributeError: module 'app' has no attribute 'DISTANCES'` (or Brazil distance is 0.0 because flows aren't stamped yet).

- [ ] **Step 3: Wire it in**

In `app.py`, add the import alongside the other repository imports (after the `AltitudeRepository` import line):

```python
from src.data.distances import DistanceRepository
```

After the `ALTITUDES = ...` line, add:

```python
DISTANCES = DistanceRepository(DATA_DIR / "team_distances.csv").load()
```

Change the `TEAM_FLOWS` line to pass distances:

```python
TEAM_FLOWS = build_team_flows(MATCHES, VENUES, distances=DISTANCES)
```

Change the layout build line to pass flows through:

```python
app.layout = build_layout(VENUES, TEAM_OPTIONS, TEAM_FLOWS)
```

In `src/components/layout.py`, update `build_layout` signature and the `build_filter_drawer` call:

```python
def build_layout(
    venues: list[Venue],
    team_options: list | None = None,
    team_flows: dict | None = None,
) -> dmc.MantineProvider:
```

Do **not** change the `build_filter_drawer(team_options or [])` call in this task — leave it one-argument. This task only threads `team_flows` *into* `build_layout` so `app.py` can pass it; the call site that forwards it to `build_filter_drawer` is updated in Task 11, when `build_filter_drawer` learns to use it. This keeps every intermediate commit working.

- [ ] **Step 4: Run test + full suite to verify**

Run: `python3 -m pytest tests/test_app_distances.py tests/test_layout.py -v`
Expected: PASS. Brazil distance > 0, `DISTANCES` present with 48 entries, layout still builds.

- [ ] **Step 5: Commit**

```bash
git add app.py src/components/layout.py tests/test_app_distances.py
git commit -m "feat: load team_distances.csv and stamp flows in app"
```

---

### Task 9: Distance in the selected-team legend

**Files:**
- Modify: `src/components/filter_panel.py`
- Test: `tests/test_filter_panel.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_filter_panel.py` (note: `_walk`, `TeamFlow`, `FlowStop`, `date`, `legend` are already imported/defined in this file):

```python
def test_legend_row_includes_formatted_distance():
    flow = TeamFlow(
        "Brazil", "South America", "#22c55e",
        (FlowStop(0, 0, "S", date(2026, 6, 1), 1),),
        1839.7,
    )
    rows = legend(["Brazil"], {"Brazil": flow})
    texts = [n.children for n in _walk(dmc.Box(rows)) if isinstance(n, dmc.Text)]
    joined = " ".join(t for t in texts if isinstance(t, str))
    assert "Brazil" in joined
    assert "1,840 km / 1,143 mi" in joined
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_filter_panel.py::test_legend_row_includes_formatted_distance -v`
Expected: FAIL — the distance text is not present.

- [ ] **Step 3: Write minimal implementation**

In `src/components/filter_panel.py`, import the formatter at the top:

```python
from src.data.flows import TeamFlow, format_distance
```

In `legend()`, change the text element of each row to include the distance. Replace the `dmc.Text(team, size="sm")` line with:

```python
                    dmc.Text(
                        f"{team} — {format_distance(flow.distance_km)}", size="sm"
                    ),
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_filter_panel.py -v`
Expected: PASS (including the pre-existing legend test, which only checks that "Brazil" is among the texts — still true).

- [ ] **Step 5: Commit**

```bash
git add src/components/filter_panel.py tests/test_filter_panel.py
git commit -m "feat: show travel distance in the selected-team legend"
```

---

### Task 10: Distance tooltip on the flow line

**Files:**
- Modify: `src/components/flow_layer.py`
- Test: `tests/test_flow_layer.py`

- [ ] **Step 1: Write the failing test**

In `tests/test_flow_layer.py`, update `_flow()` to carry a distance, and add a test. Change `_flow()`'s return line to:

```python
    return TeamFlow("Brazil", "South America", "#22c55e", stops, 1839.7)
```

Append the test:

```python
def test_polyline_has_distance_tooltip():
    comps = render_flow(_flow())
    polyline = next(c for c in comps if isinstance(c, dl.Polyline))
    tooltips = [c for c in (polyline.children or []) if isinstance(c, dl.Tooltip)]
    assert len(tooltips) == 1
    assert "1,840 km / 1,143 mi" in tooltips[0].children
    assert "Brazil" in tooltips[0].children
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_flow_layer.py::test_polyline_has_distance_tooltip -v`
Expected: FAIL — the `Polyline` has no `Tooltip` child.

- [ ] **Step 3: Write minimal implementation**

In `src/components/flow_layer.py`, import the formatter:

```python
from src.data.flows import TeamFlow, format_distance
```

Replace the `dl.Polyline(...)` construction inside `render_flow` with:

```python
        dl.Polyline(
            positions=positions,
            color=flow.color,
            weight=3,
            children=[dl.Tooltip(f"{flow.team}: {format_distance(flow.distance_km)}")],
        ),
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_flow_layer.py -v`
Expected: PASS (including the pre-existing render test).

- [ ] **Step 5: Commit**

```bash
git add src/components/flow_layer.py tests/test_flow_layer.py
git commit -m "feat: show travel distance as a flow-line tooltip"
```

---

### Task 11: Static longest/shortest leaderboard in the drawer

**Files:**
- Modify: `src/components/filter_panel.py`
- Modify: `src/components/layout.py`
- Test: `tests/test_filter_panel.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_filter_panel.py`:

```python
from src.components.filter_panel import build_filter_drawer


def _flows_for_leaderboard():
    def mk(team, km):
        return TeamFlow(team, "Europe", "#fff",
                        (FlowStop(0, 0, "S", date(2026, 6, 1), 1),), km)
    return {
        "Faraway": mk("Faraway", 9000.0),
        "Midway": mk("Midway", 3000.0),
        "Nearby": mk("Nearby", 100.0),
    }


def test_drawer_renders_longest_and_shortest_leaderboard():
    drawer = build_filter_drawer([], _flows_for_leaderboard())
    texts = [n.children for n in _walk(drawer) if isinstance(n, dmc.Text)]
    joined = " ".join(t for t in texts if isinstance(t, str))
    assert "Longest journeys" in joined
    assert "Shortest journeys" in joined
    assert "Faraway" in joined
    assert "Nearby" in joined
    assert "9,000 km" in joined


def test_build_filter_drawer_without_flows_still_builds():
    drawer = build_filter_drawer([])
    assert isinstance(drawer, dmc.Drawer)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_filter_panel.py -k "leaderboard or without_flows" -v`
Expected: FAIL — `build_filter_drawer()` takes 1 positional arg / leaderboard text absent.

- [ ] **Step 3: Write minimal implementation**

In `src/components/filter_panel.py`, import `rank_by_distance`:

```python
from src.data.flows import TeamFlow, format_distance, rank_by_distance
```

Add a leaderboard helper above `build_filter_drawer`:

```python
def _leaderboard_section(title: str, flows: list[TeamFlow]) -> dmc.Stack:
    rows = [
        dmc.Group(
            [
                dmc.Box(
                    w=10,
                    h=10,
                    style={
                        "background": f.color,
                        "borderRadius": "50%",
                        "flex": "0 0 auto",
                    },
                ),
                dmc.Text(f"{f.team} — {format_distance(f.distance_km)}", size="xs"),
            ],
            gap="xs",
            align="center",
        )
        for f in flows
    ]
    return dmc.Stack(
        [dmc.Text(title, size="sm", fw=600), *rows],
        gap=4,
    )


def _leaderboard(team_flows: dict[str, TeamFlow]) -> dmc.Stack:
    longest, shortest = rank_by_distance(team_flows, n=5)
    return dmc.Stack(
        [
            _leaderboard_section("Longest journeys", longest),
            _leaderboard_section("Shortest journeys", shortest),
        ],
        gap="md",
        mt="lg",
    )
```

Change `build_filter_drawer` to accept flows and append the leaderboard:

```python
def build_filter_drawer(
    options: list[dict], team_flows: dict | None = None
) -> dmc.Drawer:
    children = [
        dmc.MultiSelect(
            id="team-filter",
            data=options,
            searchable=True,
            clearable=True,
            placeholder="Select teams…",
            maxDropdownHeight=320,
            comboboxProps={"zIndex": 3000},
        ),
        dmc.Stack(id="filter-legend", gap="xs", mt="md"),
    ]
    if team_flows:
        children.append(dmc.Divider(my="md"))
        children.append(_leaderboard(team_flows))
    return dmc.Drawer(
        id="filter-drawer",
        title="Flow lines by team",
        position="right",
        size="md",
        padding="md",
        opened=False,
        withCloseButton=True,
        withOverlay=False,
        lockScroll=False,
        zIndex=2500,
        children=children,
    )
```

In `src/components/layout.py`, update the call site to pass flows through:

```python
    filter_drawer = build_filter_drawer(team_options or [], team_flows or {})
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_filter_panel.py tests/test_layout.py -v`
Expected: PASS (including the pre-existing drawer tests — position right, dropdown zIndex, grouped data — which are unaffected).

- [ ] **Step 5: Commit**

```bash
git add src/components/filter_panel.py src/components/layout.py tests/test_filter_panel.py
git commit -m "feat: static longest/shortest travel leaderboard in flow drawer"
```

---

### Task 12: Full verification

**Files:** none (verification only)

- [ ] **Step 1: Run the full test suite**

Run: `python3 -m pytest tests/ -v`
Expected: all tests PASS (the prior ~95 plus the new ones).

- [ ] **Step 2: Verify the app imports and flows carry distances**

Run: `python3 -c "import app; print('app ok, flows', len(app.TEAM_FLOWS), 'brazil', app.TEAM_FLOWS['Brazil'].distance_km)"`
Expected: `app ok, flows 48 brazil <positive number>`.

- [ ] **Step 3: Finish the branch**

Use the superpowers:finishing-a-development-branch skill to merge `feature/team-travel-distance` and clean up.

---

## Self-Review Notes

- **Spec coverage:** offline generation (Task 6), CSV loader (Task 5), `distance_km` on TeamFlow + `distances` param (Task 2), `format_distance` (Task 3), `rank_by_distance` (Task 4), legend display (Task 9), map tooltip (Task 10), static leaderboard (Task 11), CSV-consistency guard (Task 7), app wiring (Task 8). All spec sections map to a task.
- **Type consistency:** `build_team_flows(matches, venues, distances=None)`, `TeamFlow(..., distance_km=0.0)`, `format_distance(km) -> str`, `rank_by_distance(flows, n=5) -> (list, list)`, `DistanceRepository(path).load() -> dict[str, float]`, `build_filter_drawer(options, team_flows=None)`, `build_layout(venues, team_options=None, team_flows=None)` — used consistently across tasks.
- **Note on Task 8/11 ordering:** `build_layout` learns the `team_flows` param in Task 8 but only forwards it to `build_filter_drawer` in Task 11; Task 8 keeps the one-arg call. This avoids a broken intermediate state.
