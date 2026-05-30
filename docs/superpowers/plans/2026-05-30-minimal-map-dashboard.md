# Minimal Map Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A full-screen Dash app whose centerpiece is a dash-leaflet map showing the 16 FIFA World Cup 2026 host cities, locked to USA/Mexico/Canada, with a light/dark theme toggle.

**Architecture:** Layered package. A data layer loads/validates host cities from CSV into frozen `HostCity` dataclasses via a `HostCityRepository`. A component layer builds the leaflet map (`build_map`) and the full-screen Mantine shell (`build_layout`). `app.py` loads cities once at startup, builds the layout, and registers one clientside theme-toggle callback. TDD throughout.

**Tech Stack:** Python, dash, dash-leaflet, dash-mantine-components, dash-iconify, pandas, pytest.

---

## File Structure

- `requirements.txt` — pinned dependencies.
- `src/__init__.py`, `src/data/__init__.py`, `src/components/__init__.py` — package markers.
- `src/data/host_cities.py` — `HostCity` dataclass + `HostCityRepository` (CSV load + validation).
- `src/components/map_view.py` — `build_map(cities)` returns a `dl.Map`.
- `src/components/layout.py` — `build_layout(cities)` returns a `dmc.MantineProvider` shell.
- `app.py` — entry point: load cities, build layout, register theme callback, run.
- `assets/styles.css` — full-screen / no-scroll CSS.
- `tests/__init__.py` — package marker.
- `tests/test_host_cities.py` — data layer tests.
- `tests/test_map_view.py` — map component tests.

Data file (already present): `assets/data/fifa_2026_host_cities.csv` with columns
`City, Country, Stadium, Capacity, Latitude, Longitude` and 16 rows.

---

## Task 1: Project setup (dependencies + package skeleton)

**Files:**
- Create: `requirements.txt`
- Create: `src/__init__.py`, `src/data/__init__.py`, `src/components/__init__.py`, `tests/__init__.py`

- [ ] **Step 1: Create requirements.txt**

```
dash==2.18.2
dash-leaflet==1.0.15
dash-mantine-components==0.15.1
dash-iconify==0.1.3
pandas==2.2.3
pytest==8.3.4
```

- [ ] **Step 2: Create empty package marker files**

Create these four files, each empty:
- `src/__init__.py`
- `src/data/__init__.py`
- `src/components/__init__.py`
- `tests/__init__.py`

- [ ] **Step 3: Install dependencies**

Run: `pip install -r requirements.txt`
Expected: all packages install without error.

- [ ] **Step 4: Verify imports work**

Run: `python -c "import dash, dash_leaflet, dash_mantine_components, pandas; print('ok')"`
Expected: prints `ok`.

- [ ] **Step 5: Commit**

```bash
git add requirements.txt src/__init__.py src/data/__init__.py src/components/__init__.py tests/__init__.py
git commit -m "chore: project skeleton and dependencies"
```

---

## Task 2: HostCity dataclass + repository (data layer)

**Files:**
- Create: `src/data/host_cities.py`
- Test: `tests/test_host_cities.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_host_cities.py`:

```python
from pathlib import Path

import pandas as pd
import pytest

from src.data.host_cities import HostCity, HostCityRepository

CSV_PATH = Path("assets/data/fifa_2026_host_cities.csv")


def test_loads_all_sixteen_cities():
    cities = HostCityRepository(CSV_PATH).load()
    assert len(cities) == 16


def test_returns_hostcity_objects_with_correct_types():
    cities = HostCityRepository(CSV_PATH).load()
    city = cities[0]
    assert isinstance(city, HostCity)
    assert isinstance(city.city, str)
    assert isinstance(city.country, str)
    assert isinstance(city.stadium, str)
    assert isinstance(city.capacity, int)
    assert isinstance(city.lat, float)
    assert isinstance(city.lon, float)


def test_known_city_values():
    cities = HostCityRepository(CSV_PATH).load()
    azteca = next(c for c in cities if c.stadium == "Estadio Azteca")
    assert azteca.city == "Mexico City"
    assert azteca.country == "Mexico"
    assert azteca.capacity == 87523


def test_only_host_countries_present():
    cities = HostCityRepository(CSV_PATH).load()
    assert {c.country for c in cities} == {"USA", "Mexico", "Canada"}


def test_coordinates_within_valid_ranges():
    cities = HostCityRepository(CSV_PATH).load()
    for c in cities:
        assert -90.0 <= c.lat <= 90.0
        assert -180.0 <= c.lon <= 180.0


def test_hostcity_is_frozen():
    city = HostCity("X", "USA", "Y", 1, 0.0, 0.0)
    with pytest.raises(Exception):
        city.capacity = 2


def test_missing_column_raises(tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text("City,Country,Stadium,Capacity,Latitude\nA,USA,S,1,10.0\n")
    with pytest.raises(ValueError):
        HostCityRepository(bad).load()


def test_out_of_range_latitude_raises(tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text(
        "City,Country,Stadium,Capacity,Latitude,Longitude\n"
        "A,USA,S,1,200.0,10.0\n"
    )
    with pytest.raises(ValueError):
        HostCityRepository(bad).load()


def test_non_numeric_capacity_raises(tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text(
        "City,Country,Stadium,Capacity,Latitude,Longitude\n"
        "A,USA,S,notanumber,10.0,10.0\n"
    )
    with pytest.raises(ValueError):
        HostCityRepository(bad).load()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_host_cities.py -v`
Expected: collection/import error — `ModuleNotFoundError: No module named 'src.data.host_cities'`.

- [ ] **Step 3: Write the implementation**

Create `src/data/host_cities.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

EXPECTED_COLUMNS = ["City", "Country", "Stadium", "Capacity", "Latitude", "Longitude"]


@dataclass(frozen=True)
class HostCity:
    city: str
    country: str
    stadium: str
    capacity: int
    lat: float
    lon: float


class HostCityRepository:
    """Loads and validates FIFA 2026 host cities from a CSV file."""

    def __init__(self, csv_path: str | Path) -> None:
        self._csv_path = Path(csv_path)

    def load(self) -> list[HostCity]:
        df = pd.read_csv(self._csv_path)

        missing = [c for c in EXPECTED_COLUMNS if c not in df.columns]
        if missing:
            raise ValueError(f"Missing expected columns: {missing}")

        cities: list[HostCity] = []
        for _, row in df.iterrows():
            try:
                capacity = int(row["Capacity"])
                lat = float(row["Latitude"])
                lon = float(row["Longitude"])
            except (ValueError, TypeError) as exc:
                raise ValueError(f"Non-numeric value in row: {row.to_dict()}") from exc

            if not -90.0 <= lat <= 90.0:
                raise ValueError(f"Latitude out of range: {lat}")
            if not -180.0 <= lon <= 180.0:
                raise ValueError(f"Longitude out of range: {lon}")

            cities.append(
                HostCity(
                    city=str(row["City"]),
                    country=str(row["Country"]),
                    stadium=str(row["Stadium"]),
                    capacity=capacity,
                    lat=lat,
                    lon=lon,
                )
            )
        return cities
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_host_cities.py -v`
Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/data/host_cities.py tests/test_host_cities.py
git commit -m "feat: add HostCity dataclass and validating repository"
```

---

## Task 3: Map view component

**Files:**
- Create: `src/components/map_view.py`
- Test: `tests/test_map_view.py`

Notes for the implementer:
- `dl.Map` accepts a list of children (tile layer + markers) and props
  `center`, `zoom`, `minZoom`, `maxBounds`, `style`.
- `NA_BOUNDS = [[14.0, -168.0], [72.0, -52.0]]` is the SW/NE box covering
  USA, Mexico, and Canada. Used for `maxBounds`.
- `OSM_URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"`.
- Children of a built `dl.Map` are accessible via `m.children` (a list).

- [ ] **Step 1: Write the failing tests**

Create `tests/test_map_view.py`:

```python
import dash_leaflet as dl

from src.components.map_view import build_map, NA_BOUNDS, OSM_URL
from src.data.host_cities import HostCity

CITIES = [
    HostCity("Mexico City", "Mexico", "Estadio Azteca", 87523, 19.3029, -99.1505),
    HostCity("Toronto", "Canada", "BMO Field", 45000, 43.6333, -79.4186),
    HostCity("Dallas", "USA", "AT&T Stadium", 80000, 32.7473, -97.0945),
]


def _children(m):
    return m.children if isinstance(m.children, list) else [m.children]


def test_build_map_returns_dl_map():
    m = build_map(CITIES)
    assert isinstance(m, dl.Map)


def test_map_has_one_marker_per_city():
    m = build_map(CITIES)
    markers = [c for c in _children(build_map(CITIES)) if isinstance(c, dl.Marker)]
    assert len(markers) == len(CITIES)


def test_map_has_osm_tile_layer():
    m = build_map(CITIES)
    tile_layers = [c for c in _children(m) if isinstance(c, dl.TileLayer)]
    assert len(tile_layers) == 1
    assert tile_layers[0].url == OSM_URL


def test_map_bounds_locked_to_north_america():
    m = build_map(CITIES)
    assert m.maxBounds == NA_BOUNDS


def test_markers_positioned_at_city_coordinates():
    m = build_map(CITIES)
    markers = [c for c in _children(m) if isinstance(c, dl.Marker)]
    positions = {tuple(mk.position) for mk in markers}
    assert (19.3029, -99.1505) in positions
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_map_view.py -v`
Expected: `ModuleNotFoundError: No module named 'src.components.map_view'`.

- [ ] **Step 3: Write the implementation**

Create `src/components/map_view.py`:

```python
from __future__ import annotations

import dash_leaflet as dl

from src.data.host_cities import HostCity

OSM_URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
OSM_ATTRIBUTION = "© OpenStreetMap contributors"

# SW and NE corners of a box covering USA, Mexico, and Canada.
NA_BOUNDS = [[14.0, -168.0], [72.0, -52.0]]

NA_CENTER = [40.0, -100.0]
NA_ZOOM = 3
NA_MIN_ZOOM = 3


def _marker(city: HostCity) -> dl.Marker:
    label = f"{city.city} — {city.stadium} ({city.capacity:,})"
    return dl.Marker(
        position=[city.lat, city.lon],
        children=[dl.Tooltip(label)],
    )


def build_map(cities: list[HostCity]) -> dl.Map:
    return dl.Map(
        children=[
            dl.TileLayer(url=OSM_URL, attribution=OSM_ATTRIBUTION),
            *[_marker(c) for c in cities],
        ],
        center=NA_CENTER,
        zoom=NA_ZOOM,
        minZoom=NA_MIN_ZOOM,
        maxBounds=NA_BOUNDS,
        style={"height": "100%", "width": "100%"},
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_map_view.py -v`
Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/components/map_view.py tests/test_map_view.py
git commit -m "feat: add host-city leaflet map view locked to North America"
```

---

## Task 4: Full-screen layout shell

**Files:**
- Create: `src/components/layout.py`
- Create: `assets/styles.css`

Note: layout assembly is verified by the app smoke-test in Task 5, so this task
has no separate unit test (the component is a thin assembly of DMC + map_view).

- [ ] **Step 1: Create the no-scroll CSS**

Create `assets/styles.css`:

```css
html,
body,
#react-entry-point,
#react-entry-point > div {
    height: 100vh;
    width: 100vw;
    margin: 0;
    padding: 0;
    overflow: hidden;
}

/* Let the AppShell main region fill remaining height and host the map. */
.mantine-AppShell-main {
    height: 100vh;
    display: flex;
    flex-direction: column;
    padding-top: var(--app-shell-header-height, 60px);
}

#map-container {
    flex: 1;
    min-height: 0;
}
```

- [ ] **Step 2: Write the layout implementation**

Create `src/components/layout.py`:

```python
from __future__ import annotations

import dash_mantine_components as dmc
from dash import html
from dash_iconify import DashIconify

from src.components.map_view import build_map
from src.data.host_cities import HostCity

DEFAULT_COLOR_SCHEME = "dark"

theme_toggle = dmc.Switch(
    id="color-scheme-toggle",
    offLabel=DashIconify(icon="radix-icons:sun", width=15),
    onLabel=DashIconify(icon="radix-icons:moon", width=15),
    checked=True,
    persistence=True,
    color="grey",
)


def build_layout(cities: list[HostCity]) -> dmc.MantineProvider:
    header = dmc.AppShellHeader(
        dmc.Group(
            [
                dmc.Title("FIFA World Cup 2026", order=3),
                theme_toggle,
            ],
            justify="space-between",
            align="center",
            h="100%",
            px="md",
        )
    )

    main = dmc.AppShellMain(
        html.Div(build_map(cities), id="map-container")
    )

    shell = dmc.AppShell(
        [header, main],
        header={"height": 60},
        padding=0,
        id="appshell",
    )

    return dmc.MantineProvider(
        shell,
        id="mantine-provider",
        defaultColorScheme=DEFAULT_COLOR_SCHEME,
    )
```

- [ ] **Step 3: Verify the module imports**

Run: `python -c "from src.components.layout import build_layout; print('ok')"`
Expected: prints `ok`.

- [ ] **Step 4: Commit**

```bash
git add src/components/layout.py assets/styles.css
git commit -m "feat: add full-screen Mantine shell with theme toggle"
```

---

## Task 5: App entry point + theme callback + smoke test

**Files:**
- Create: `app.py`
- Test: `tests/test_app.py`

The theme toggle uses a clientside callback that flips the
`data-mantine-color-scheme` attribute on the document root — the canonical DMC
pattern (no server round-trip).

- [ ] **Step 1: Write the failing smoke test**

Create `tests/test_app.py`:

```python
def test_app_builds_with_layout():
    import app

    assert app.app is not None
    # Layout is a MantineProvider instance built from the loaded cities.
    assert app.app.layout.id == "mantine-provider"


def test_app_loads_sixteen_cities():
    import app

    assert len(app.CITIES) == 16
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/test_app.py -v`
Expected: `ModuleNotFoundError: No module named 'app'`.

- [ ] **Step 3: Write app.py**

Create `app.py`:

```python
from __future__ import annotations

from pathlib import Path

from dash import Dash, Input, Output, clientside_callback

from src.components.layout import build_layout
from src.data.host_cities import HostCityRepository

CSV_PATH = Path("assets/data/fifa_2026_host_cities.csv")

CITIES = HostCityRepository(CSV_PATH).load()

app = Dash(__name__)
app.title = "FIFA World Cup 2026"
app.layout = build_layout(CITIES)

# Flip the document color scheme when the switch toggles (checked => dark).
clientside_callback(
    """
    (checked) => {
        document.documentElement.setAttribute(
            'data-mantine-color-scheme', checked ? 'dark' : 'light'
        );
        return window.dash_clientside.no_update;
    }
    """,
    Output("color-scheme-toggle", "id"),
    Input("color-scheme-toggle", "checked"),
)

if __name__ == "__main__":
    app.run(debug=True)
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `pytest tests/test_app.py -v`
Expected: both tests PASS.

- [ ] **Step 5: Run the full suite**

Run: `pytest tests/ -v`
Expected: all tests across all three test files PASS.

- [ ] **Step 6: Manual launch check**

Run: `python app.py`
Expected: server starts on `http://127.0.0.1:8050/`; opening it shows a
full-screen map of North America with 16 markers and a working light/dark
toggle in the header. Stop with Ctrl+C.

- [ ] **Step 7: Commit**

```bash
git add app.py tests/test_app.py
git commit -m "feat: wire app entry point with clientside theme toggle"
```

---

## Self-Review

**Spec coverage:**
- Load + validate 16 host cities → Task 2.
- Full-screen shell, header (title + toggle), map fills rest → Task 4 + `styles.css`.
- Map locked to NA box, OSM tiles, marker per city w/ tooltip → Task 3.
- Light/dark toggle always present → Task 4 (switch) + Task 5 (callback).
- TDD, pandas, OOP, DMC, dash-leaflet → all tasks.
- requirements.txt → Task 1.

**Type consistency:** `HostCity(city, country, stadium, capacity, lat, lon)` used identically in Tasks 2, 3, 5 tests. `build_map(cities) -> dl.Map`, `build_layout(cities) -> MantineProvider`, `HostCityRepository(path).load()` consistent across tasks. `NA_BOUNDS`, `OSM_URL` imported by name in Task 3 tests and defined in Task 3 impl. `id="mantine-provider"` defined in Task 4, asserted in Task 5. `id="color-scheme-toggle"` defined in Task 4, used by callback in Task 5.

**Deviation from spec:** Theme uses `defaultColorScheme` + clientside callback on `data-mantine-color-scheme` (current DMC idiom) instead of `dcc.Store` + `forceColorScheme`. The spec deferred exact DMC choices to context7; behavior (always-present working toggle, dark default) is unchanged.

**Placeholder scan:** none found.
