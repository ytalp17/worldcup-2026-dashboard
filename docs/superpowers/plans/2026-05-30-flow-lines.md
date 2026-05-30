# Flow Lines Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A yellow funnel pin opens a left, non-blocking drawer with a continent-grouped multi-select of the 48 group-stage teams; selecting teams draws colored, arrow-headed flow lines through each team's three group-stage stadiums in chronological order.

**Architecture:** New data modules map teams→continent and build per-team ordered stadium "flows" with a fixed color each. A flow-rendering module turns a flow into dash-leaflet Polyline + PolylineDecorator (arrowheads) + stop dots. The map gains an empty `flow-layer` LayerGroup and the funnel pin; a non-blocking filter drawer holds the grouped MultiSelect. Callbacks open/close the two mutually-exclusive left drawers and fill `flow-layer` from the selection.

**Tech Stack:** dash, dash-leaflet (Polyline, PolylineDecorator, CircleMarker, DivMarker, LayerGroup), dash-mantine-components (Drawer, MultiSelect), pandas, pytest.

**Environment:** Run pytest with `/Library/Frameworks/Python.framework/Versions/3.11/bin/python3 -m pytest` from the project root.

---

## File Structure

- Create `src/data/team_continents.py` — team→continent map + grouped options.
- Create `src/data/flows.py` — `team_color`, `FlowStop`, `TeamFlow`, `build_team_flows`.
- Create `src/components/flow_layer.py` — `render_flow`, `flows_for`.
- Create `src/components/filter_panel.py` — `build_filter_drawer`, `legend`.
- Modify `src/components/map_view.py` — add `flow-layer` LayerGroup + funnel pin.
- Modify `src/components/layout.py` — include the filter drawer.
- Modify `assets/styles.css` — `.filter-pin` styling.
- Modify `app.py` — build flows/options, wire callbacks.
- Tests: `tests/test_team_continents.py`, `tests/test_flows.py`, `tests/test_flow_layer.py`, `tests/test_filter_panel.py`, and additions to `tests/test_map_view.py`, `tests/test_layout.py`.

---

## Task 1: Team → continent mapping + grouped options

**Files:**
- Create: `src/data/team_continents.py`
- Test: `tests/test_team_continents.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_team_continents.py
from pathlib import Path

import pandas as pd
import pytest

from src.data.team_continents import (
    CONTINENT_ORDER,
    TEAM_CONTINENT,
    continent_for,
    grouped_team_options,
)

MATCHES = Path(__file__).parent.parent / "assets" / "data" / "wc2026_matches.csv"


def _group_stage_teams():
    m = pd.read_csv(MATCHES)
    gs = m[m["stage"] == "Group Stage"]
    return set(pd.concat([gs["home_team"], gs["away_team"]]))


def test_all_group_stage_teams_have_a_continent():
    teams = _group_stage_teams()
    assert len(teams) == 48
    missing = [t for t in teams if t not in TEAM_CONTINENT]
    assert missing == []


def test_continents_are_from_the_known_set():
    assert set(TEAM_CONTINENT.values()) <= set(CONTINENT_ORDER)


def test_continent_for_known_and_unknown():
    assert continent_for("Brazil") == "South America"
    assert continent_for("Japan") == "Asia"
    with pytest.raises(ValueError):
        continent_for("Atlantis")


def test_grouped_options_shape_and_order():
    options = grouped_team_options(["Brazil", "France", "USA", "Japan"])
    groups = [g["group"] for g in options]
    # Groups appear in CONTINENT_ORDER and only non-empty ones are present.
    assert groups == [c for c in CONTINENT_ORDER if c in groups]
    sa = next(g for g in options if g["group"] == "South America")
    assert sa["items"] == [{"value": "Brazil", "label": "Brazil"}]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/Library/Frameworks/Python.framework/Versions/3.11/bin/python3 -m pytest tests/test_team_continents.py -q`
Expected: `ModuleNotFoundError: No module named 'src.data.team_continents'`.

- [ ] **Step 3: Write the implementation**

```python
# src/data/team_continents.py
from __future__ import annotations

CONTINENT_ORDER = [
    "North America",
    "South America",
    "Europe",
    "Africa",
    "Asia",
    "Oceania",
]

TEAM_CONTINENT: dict[str, str] = {
    # North America
    "Canada": "North America", "Curaçao": "North America", "Haiti": "North America",
    "Mexico": "North America", "Panama": "North America", "USA": "North America",
    # South America
    "Argentina": "South America", "Brazil": "South America", "Colombia": "South America",
    "Ecuador": "South America", "Paraguay": "South America", "Uruguay": "South America",
    # Europe
    "Austria": "Europe", "Belgium": "Europe", "Bosnia and Herzegovina": "Europe",
    "Croatia": "Europe", "Czechia": "Europe", "England": "Europe", "France": "Europe",
    "Germany": "Europe", "Netherlands": "Europe", "Norway": "Europe", "Portugal": "Europe",
    "Scotland": "Europe", "Spain": "Europe", "Sweden": "Europe", "Switzerland": "Europe",
    "Türkiye": "Europe",
    # Africa
    "Algeria": "Africa", "Cabo Verde": "Africa", "Congo DR": "Africa",
    "Côte d'Ivoire": "Africa", "Egypt": "Africa", "Ghana": "Africa", "Morocco": "Africa",
    "Senegal": "Africa", "South Africa": "Africa", "Tunisia": "Africa",
    # Asia
    "IR Iran": "Asia", "Iraq": "Asia", "Japan": "Asia", "Jordan": "Asia",
    "Korea Republic": "Asia", "Qatar": "Asia", "Saudi Arabia": "Asia", "Uzbekistan": "Asia",
    # Oceania
    "Australia": "Oceania", "New Zealand": "Oceania",
}


def continent_for(team: str) -> str:
    try:
        return TEAM_CONTINENT[team]
    except KeyError as exc:
        raise ValueError(f"No continent mapped for team {team!r}") from exc


def grouped_team_options(teams: list[str]) -> list[dict]:
    """DMC MultiSelect grouped data, continents in CONTINENT_ORDER, teams sorted."""
    options: list[dict] = []
    for continent in CONTINENT_ORDER:
        items = sorted(t for t in teams if TEAM_CONTINENT.get(t) == continent)
        if items:
            options.append(
                {"group": continent, "items": [{"value": t, "label": t} for t in items]}
            )
    return options
```

- [ ] **Step 4: Run test to verify it passes**

Run: `/Library/Frameworks/Python.framework/Versions/3.11/bin/python3 -m pytest tests/test_team_continents.py -q`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add src/data/team_continents.py tests/test_team_continents.py
git commit -m "feat: team->continent map and grouped multiselect options"
```

---

## Task 2: Team flows (color + ordered stadium stops)

**Files:**
- Create: `src/data/flows.py`
- Test: `tests/test_flows.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_flows.py
from pathlib import Path

import pytest

from src.data.flows import FlowStop, TeamFlow, build_team_flows, team_color
from src.data.host_cities import HostCityRepository
from src.data.matches import MatchRepository
from src.data.stadiums import StadiumRepository
from src.data.venues import build_venues

DATA = Path(__file__).parent.parent / "assets" / "data"
IMAGE_DIR = DATA.parent / "stadiums"


def _flows():
    cities = HostCityRepository(DATA / "fifa_2026_host_cities.csv").load()
    stadiums = StadiumRepository(DATA / "fifa_wc2026_stadiums.csv").load()
    venues = build_venues(cities, stadiums, IMAGE_DIR)
    matches = MatchRepository(DATA / "wc2026_matches.csv").load()
    return build_team_flows(matches, venues)


def test_team_color_is_deterministic_and_hex():
    assert team_color("Brazil") == team_color("Brazil")
    assert team_color("Brazil").startswith("#") and len(team_color("Brazil")) == 7
    assert team_color("Brazil") != team_color("Argentina")


def test_builds_a_flow_per_group_stage_team():
    flows = _flows()
    assert len(flows) == 48
    assert all(isinstance(f, TeamFlow) for f in flows.values())


def test_brazil_flow_stops_in_chronological_order():
    flows = _flows()
    brazil = flows["Brazil"]
    assert brazil.continent == "South America"
    assert brazil.color == team_color("Brazil")
    names = [s.stadium_name for s in brazil.stops]
    assert names == ["New York New Jersey Stadium", "Philadelphia Stadium", "Miami Stadium"]
    dates = [s.date for s in brazil.stops]
    assert dates == sorted(dates)
    assert all(isinstance(s, FlowStop) for s in brazil.stops)


def test_mexico_flow_doubles_back():
    flows = _flows()
    stops = flows["Mexico"].stops
    assert (stops[0].lat, stops[0].lon) == (stops[2].lat, stops[2].lon)  # returns to Mexico City


def test_unmatched_stadium_raises():
    from src.data.matches import Match
    from datetime import date
    bad = [Match(1, "Brazil", "X", "Group A", "Group Stage", "Nowhere Stadium", date(2026, 6, 11))]
    with pytest.raises(ValueError):
        build_team_flows(bad, [])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/Library/Frameworks/Python.framework/Versions/3.11/bin/python3 -m pytest tests/test_flows.py -q`
Expected: `ModuleNotFoundError: No module named 'src.data.flows'`.

- [ ] **Step 3: Write the implementation**

```python
# src/data/flows.py
from __future__ import annotations

import colorsys
from collections import defaultdict
from dataclasses import dataclass
from datetime import date

from src.data.matches import Match
from src.data.team_continents import TEAM_CONTINENT, continent_for
from src.data.venues import Venue

# Stable team order used to spread colors deterministically.
_ALL_TEAMS = sorted(TEAM_CONTINENT)


def team_color(team: str) -> str:
    """Deterministic, well-spread hex color, stable per team."""
    i = _ALL_TEAMS.index(team)  # ValueError if team unknown
    hue = (i * 137.508) % 360  # golden-angle spread
    r, g, b = colorsys.hls_to_rgb(hue / 360.0, 0.55, 0.6)
    return "#%02x%02x%02x" % (round(r * 255), round(g * 255), round(b * 255))


@dataclass(frozen=True)
class FlowStop:
    lat: float
    lon: float
    stadium_name: str
    date: date
    match_number: int


@dataclass(frozen=True)
class TeamFlow:
    team: str
    continent: str
    color: str
    stops: tuple[FlowStop, ...]


def build_team_flows(matches: list[Match], venues: list[Venue]) -> dict[str, TeamFlow]:
    venue_by_name = {v.stadium_name: v for v in venues}
    by_team: dict[str, list[Match]] = defaultdict(list)
    for m in matches:
        if m.stage != "Group Stage":
            continue
        by_team[m.home].append(m)
        by_team[m.away].append(m)

    flows: dict[str, TeamFlow] = {}
    for team, team_matches in by_team.items():
        stops: list[FlowStop] = []
        for m in sorted(team_matches, key=lambda x: (x.date, x.number)):
            venue = venue_by_name.get(m.stadium)
            if venue is None:
                raise ValueError(f"No venue for stadium {m.stadium!r}")
            stops.append(FlowStop(venue.lat, venue.lon, m.stadium, m.date, m.number))
        flows[team] = TeamFlow(team, continent_for(team), team_color(team), tuple(stops))
    return flows
```

- [ ] **Step 4: Run test to verify it passes**

Run: `/Library/Frameworks/Python.framework/Versions/3.11/bin/python3 -m pytest tests/test_flows.py -q`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add src/data/flows.py tests/test_flows.py
git commit -m "feat: build per-team group-stage flows with fixed colors"
```

---

## Task 3: Flow rendering (polyline + arrowheads + stop dots)

**Files:**
- Create: `src/components/flow_layer.py`
- Test: `tests/test_flow_layer.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_flow_layer.py
from datetime import date

import dash_leaflet as dl

from src.components.flow_layer import flows_for, render_flow
from src.data.flows import FlowStop, TeamFlow


def _flow():
    stops = (
        FlowStop(40.8, -74.0, "New York New Jersey Stadium", date(2026, 6, 13), 7),
        FlowStop(39.9, -75.1, "Philadelphia Stadium", date(2026, 6, 19), 40),
        FlowStop(25.9, -80.2, "Miami Stadium", date(2026, 6, 24), 60),
    )
    return TeamFlow("Brazil", "South America", "#22c55e", stops)


def test_render_flow_has_polyline_decorator_and_dots():
    comps = render_flow(_flow())
    polylines = [c for c in comps if isinstance(c, dl.Polyline)]
    decorators = [c for c in comps if isinstance(c, dl.PolylineDecorator)]
    dots = [c for c in comps if isinstance(c, dl.CircleMarker)]
    assert len(polylines) == 1
    assert polylines[0].color == "#22c55e"
    assert polylines[0].positions == [[40.8, -74.0], [39.9, -75.1], [25.9, -80.2]]
    assert len(decorators) == 1
    assert len(dots) == 3


def test_flows_for_empty_selection_is_empty():
    assert flows_for([], {"Brazil": _flow()}) == []
    assert flows_for(None, {"Brazil": _flow()}) == []


def test_flows_for_selected_team_includes_its_polyline():
    comps = flows_for(["Brazil"], {"Brazil": _flow()})
    assert any(isinstance(c, dl.Polyline) and c.color == "#22c55e" for c in comps)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/Library/Frameworks/Python.framework/Versions/3.11/bin/python3 -m pytest tests/test_flow_layer.py -q`
Expected: `ModuleNotFoundError: No module named 'src.components.flow_layer'`.

- [ ] **Step 3: Write the implementation**

```python
# src/components/flow_layer.py
from __future__ import annotations

import dash_leaflet as dl

from src.data.flows import TeamFlow


def render_flow(flow: TeamFlow) -> list:
    positions = [[s.lat, s.lon] for s in flow.stops]
    arrow = {
        "offset": "6%",
        "repeat": "18%",
        "endOffset": "0",
        "arrowHead": {
            "pixelSize": 11,
            "headAngle": 40,
            "polygon": False,
            "pathOptions": {"color": flow.color, "weight": 3},
        },
    }
    comps: list = [
        dl.Polyline(positions=positions, color=flow.color, weight=3),
        dl.PolylineDecorator(positions=positions, patterns=[arrow]),
    ]
    for s in flow.stops:
        comps.append(
            dl.CircleMarker(
                center=[s.lat, s.lon],
                radius=5,
                color=flow.color,
                fillColor=flow.color,
                fillOpacity=1.0,
                weight=1,
            )
        )
    return comps


def flows_for(selected, team_flows: dict) -> list:
    comps: list = []
    for team in selected or []:
        flow = team_flows.get(team)
        if flow is not None:
            comps.extend(render_flow(flow))
    return comps
```

- [ ] **Step 4: Run test to verify it passes**

Run: `/Library/Frameworks/Python.framework/Versions/3.11/bin/python3 -m pytest tests/test_flow_layer.py -q`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add src/components/flow_layer.py tests/test_flow_layer.py
git commit -m "feat: render team flow as polyline + arrowheads + stop dots"
```

---

## Task 4: Filter drawer + legend

**Files:**
- Create: `src/components/filter_panel.py`
- Test: `tests/test_filter_panel.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_filter_panel.py
import dash_mantine_components as dmc

from src.components.filter_panel import build_filter_drawer, legend
from src.data.flows import FlowStop, TeamFlow
from datetime import date


def _walk(node):
    yield node
    children = getattr(node, "children", None)
    if isinstance(children, (list, tuple)):
        for c in children:
            yield from _walk(c)
    elif children is not None:
        yield from _walk(children)


def test_filter_drawer_is_left_and_non_blocking():
    drawer = build_filter_drawer([{"group": "Europe", "items": [{"value": "France", "label": "France"}]}])
    assert isinstance(drawer, dmc.Drawer)
    assert drawer.id == "filter-drawer"
    assert drawer.position == "left"
    assert drawer.withOverlay is False


def test_filter_drawer_has_multiselect_with_grouped_data():
    options = [{"group": "Europe", "items": [{"value": "France", "label": "France"}]}]
    drawer = build_filter_drawer(options)
    selects = [n for n in _walk(drawer) if isinstance(n, dmc.MultiSelect)]
    assert len(selects) == 1
    assert selects[0].id == "team-filter"
    assert selects[0].data == options


def test_legend_lists_selected_teams_with_color():
    flow = TeamFlow("Brazil", "South America", "#22c55e",
                    (FlowStop(0, 0, "S", date(2026, 6, 1), 1),))
    rows = legend(["Brazil"], {"Brazil": flow})
    texts = [n.children for n in _walk(dmc.Box(rows)) if isinstance(n, dmc.Text)]
    assert "Brazil" in texts
    assert legend([], {"Brazil": flow}) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/Library/Frameworks/Python.framework/Versions/3.11/bin/python3 -m pytest tests/test_filter_panel.py -q`
Expected: `ModuleNotFoundError: No module named 'src.components.filter_panel'`.

- [ ] **Step 3: Write the implementation**

```python
# src/components/filter_panel.py
from __future__ import annotations

import dash_mantine_components as dmc

from src.data.flows import TeamFlow


def build_filter_drawer(options: list[dict]) -> dmc.Drawer:
    return dmc.Drawer(
        id="filter-drawer",
        title="Flow lines by team",
        position="left",
        size="md",
        padding="md",
        opened=False,
        withCloseButton=True,
        withOverlay=False,
        lockScroll=False,
        zIndex=2500,
        children=[
            dmc.MultiSelect(
                id="team-filter",
                data=options,
                searchable=True,
                clearable=True,
                placeholder="Select teams…",
                maxDropdownHeight=320,
            ),
            dmc.Stack(id="filter-legend", gap="xs", mt="md"),
        ],
    )


def legend(selected, team_flows: dict[str, TeamFlow]) -> list:
    rows: list = []
    for team in selected or []:
        flow = team_flows.get(team)
        if flow is None:
            continue
        rows.append(
            dmc.Group(
                [
                    dmc.Box(
                        w=12, h=12,
                        style={"background": flow.color, "borderRadius": "50%", "flex": "0 0 auto"},
                    ),
                    dmc.Text(team, size="sm"),
                ],
                gap="xs",
                align="center",
            )
        )
    return rows
```

- [ ] **Step 4: Run test to verify it passes**

Run: `/Library/Frameworks/Python.framework/Versions/3.11/bin/python3 -m pytest tests/test_filter_panel.py -q`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add src/components/filter_panel.py tests/test_filter_panel.py
git commit -m "feat: non-blocking left filter drawer with grouped team multiselect"
```

---

## Task 5: Map + layout integration (flow layer, funnel pin, filter drawer)

**Files:**
- Modify: `src/components/map_view.py`
- Modify: `src/components/layout.py`
- Modify: `assets/styles.css`
- Test: `tests/test_map_view.py`, `tests/test_layout.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_map_view.py`:

```python
def test_map_has_flow_layer_and_filter_pin():
    import dash_leaflet as dl
    from src.components.map_view import FILTER_PIN
    m = build_map(VENUES)
    children = m.children if isinstance(m.children, list) else [m.children]
    layer_ids = [getattr(c, "id", None) for c in children]
    assert "flow-layer" in layer_ids
    pins = [c for c in children if isinstance(c, dl.DivMarker) and getattr(c, "id", None) == "filter-pin"]
    assert len(pins) == 1
    assert pins[0].position == FILTER_PIN
```

Append to `tests/test_layout.py`:

```python
def test_layout_contains_filter_drawer():
    layout = build_layout(VENUES)
    drawers = [n for n in _walk(layout) if isinstance(n, dmc.Drawer)]
    ids = {d.id for d in drawers}
    assert "filter-drawer" in ids
    assert "stadium-drawer" in ids
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `/Library/Frameworks/Python.framework/Versions/3.11/bin/python3 -m pytest tests/test_map_view.py::test_map_has_flow_layer_and_filter_pin tests/test_layout.py::test_layout_contains_filter_drawer -q`
Expected: FAIL (`ImportError: FILTER_PIN` / assertion: only one drawer).

- [ ] **Step 3: Modify `src/components/map_view.py`**

Add near the other constants:

```python
# Fixed control pin (right-middle, over the Atlantic) that opens the filter drawer.
FILTER_PIN = [37.5, -71.0]
```

Add this helper above `build_map`:

```python
def _filter_pin() -> dl.DivMarker:
    funnel = (
        '<div class="filter-pin">'
        '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="2" stroke-linecap="round" '
        'stroke-linejoin="round"><polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"/></svg>'
        "</div>"
    )
    return dl.DivMarker(
        id="filter-pin",
        position=FILTER_PIN,
        iconOptions={
            "html": funnel,
            "className": "filter-pin-icon",
            "iconSize": [34, 34],
            "iconAnchor": [17, 17],
        },
        children=[dl.Tooltip("Filter teams")],
    )
```

In `build_map`, change the `children` list to add the flow layer and the pin (keep the tile layer first, then venue markers, then these):

```python
    return dl.Map(
        children=[
            dl.TileLayer(id="base-tiles", url=DARK_TILE, attribution=TILE_ATTRIBUTION),
            *[_marker(v) for v in venues],
            dl.LayerGroup(id="flow-layer"),
            _filter_pin(),
        ],
        center=NA_CENTER,
        zoom=NA_ZOOM,
        minZoom=NA_MIN_ZOOM,
        maxBounds=NA_BOUNDS,
        maxBoundsViscosity=1.0,
        dragging=False,
        boxZoom=False,
        keyboard=False,
        zoomControl=False,
        style={"height": "100%", "width": "100%"},
    )
```

- [ ] **Step 4: Modify `src/components/layout.py`**

Add import at top:

```python
from src.components.filter_panel import build_filter_drawer
```

Change `build_layout` signature and body to accept options and include the filter drawer:

```python
def build_layout(venues: list[Venue], team_options: list | None = None) -> dmc.MantineProvider:
```

After the existing `drawer = dmc.Drawer(... id="stadium-drawer" ...)` block, add:

```python
    filter_drawer = build_filter_drawer(team_options or [])
```

And change the provider's children to include it:

```python
    return dmc.MantineProvider(
        [shell, drawer, filter_drawer],
        id="mantine-provider",
        defaultColorScheme=DEFAULT_COLOR_SCHEME,
    )
```

- [ ] **Step 5: Add `.filter-pin` styling to `assets/styles.css`**

```css
/* Yellow funnel control pin that opens the team-filter drawer. */
.filter-pin-icon {
    background: transparent;
    border: none;
}

.filter-pin {
    width: 34px;
    height: 34px;
    border-radius: 50%;
    background: #facc15;
    color: #1a1003;
    display: flex;
    align-items: center;
    justify-content: center;
    border: 2px solid #fff;
    box-shadow: 0 0 8px 2px rgba(250, 204, 21, 0.7);
    cursor: pointer;
}
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `/Library/Frameworks/Python.framework/Versions/3.11/bin/python3 -m pytest tests/test_map_view.py tests/test_layout.py -q`
Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git add src/components/map_view.py src/components/layout.py assets/styles.css tests/test_map_view.py tests/test_layout.py
git commit -m "feat: add flow layer, funnel filter pin, and filter drawer to the map"
```

---

## Task 6: App wiring (flows, options, callbacks, mutual exclusion)

**Files:**
- Modify: `app.py`
- Test: `tests/test_app.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_app.py`:

```python
def test_app_builds_team_flows_and_options():
    import app
    assert len(app.TEAM_FLOWS) == 48
    groups = [g["group"] for g in app.TEAM_OPTIONS]
    assert "South America" in groups


def test_app_flow_layer_children_for_selection():
    import app
    import dash_leaflet as dl
    children = app.flow_children(["Brazil"])
    assert any(isinstance(c, dl.Polyline) for c in children)
    assert app.flow_children([]) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/Library/Frameworks/Python.framework/Versions/3.11/bin/python3 -m pytest tests/test_app.py -q`
Expected: FAIL (`AttributeError: module 'app' has no attribute 'TEAM_FLOWS'`).

- [ ] **Step 3: Modify `app.py`**

Add imports (near the other `src.data` / `src.components` imports):

```python
from dash import Patch  # not required; keep only if used. Otherwise omit.
from src.components.filter_panel import legend
from src.components.flow_layer import flows_for
from src.data.flows import build_team_flows
from src.data.team_continents import grouped_team_options
```

(Only add the imports you actually use: `legend`, `flows_for`, `build_team_flows`, `grouped_team_options`. Do not add `Patch`.)

After `VENUES = build_venues(...)` and `MATCHES = ... ; MATCHES_BY_STADIUM = ...`, add:

```python
TEAM_FLOWS = build_team_flows(MATCHES, VENUES)
TEAM_OPTIONS = grouped_team_options(sorted(TEAM_FLOWS))


def flow_children(selected):
    return flows_for(selected, TEAM_FLOWS)
```

Change the layout build to pass options:

```python
app.layout = build_layout(VENUES, TEAM_OPTIONS)
```

Update the existing marker-click callback (`open_stadium_drawer`) to also close the filter drawer. Change its decorator outputs and return values:

```python
@callback(
    Output("stadium-drawer", "opened"),
    Output("stadium-drawer", "title"),
    Output("stadium-drawer", "children"),
    Output("filter-drawer", "opened", allow_duplicate=True),
    Input({"type": MARKER_TYPE, "index": ALL}, "n_clicks"),
    prevent_initial_call=True,
)
def open_stadium_drawer(n_clicks):
    if not any(n_clicks):
        return no_update, no_update, no_update, no_update
    triggered = ctx.triggered_id
    city = triggered.get("index") if isinstance(triggered, dict) else None
    opened, title, children = drawer_for_city(city)
    # Opening the stadium drawer closes the filter drawer.
    return opened, title, children, (False if opened else no_update)
```

Add two new callbacks after it:

```python
@callback(
    Output("filter-drawer", "opened"),
    Output("stadium-drawer", "opened", allow_duplicate=True),
    Input("filter-pin", "n_clicks"),
    prevent_initial_call=True,
)
def open_filter_drawer(n_clicks):
    if not n_clicks:
        return no_update, no_update
    return True, False  # open filter, close stadium drawer


@callback(
    Output("flow-layer", "children"),
    Output("filter-legend", "children"),
    Input("team-filter", "value"),
)
def update_flows(selected):
    return flow_children(selected), legend(selected, TEAM_FLOWS)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `/Library/Frameworks/Python.framework/Versions/3.11/bin/python3 -m pytest tests/test_app.py -q`
Expected: all pass.

- [ ] **Step 5: Run the full suite**

Run: `/Library/Frameworks/Python.framework/Versions/3.11/bin/python3 -m pytest tests/ -q`
Expected: all pass.

- [ ] **Step 6: Boot check**

Run (background) on a free port and confirm HTTP 200 and the `team-filter`/`flow-layer`/`filter-pin` callbacks are registered:
`/Library/Frameworks/Python.framework/Versions/3.11/bin/python3 -c "import app; print('ok')"`
Expected: prints `ok` with no errors.

- [ ] **Step 7: Commit**

```bash
git add app.py tests/test_app.py
git commit -m "feat: wire filter pin, team selection -> flow lines, drawer mutual exclusion"
```

---

## Self-Review

**Spec coverage:** continent map + grouped options (Task 1); fixed colors + ordered flows (Task 2); polyline+arrowheads+dots (Task 3); non-blocking left filter drawer + legend (Task 4); flow layer + funnel pin + drawer in layout (Task 5); selection→lines + mutual-exclusion callbacks (Task 6). All spec sections covered.

**Type consistency:** `build_team_flows(matches, venues) -> dict[str, TeamFlow]`; `TeamFlow(team, continent, color, stops)`; `FlowStop(lat, lon, stadium_name, date, match_number)`; `render_flow(flow)->list`; `flows_for(selected, team_flows)->list`; `build_filter_drawer(options)->Drawer`; `legend(selected, team_flows)->list`; ids `flow-layer`, `filter-pin`, `filter-drawer`, `team-filter`, `filter-legend`, `stadium-drawer` consistent across tasks. `FILTER_PIN` defined in map_view (Task 5), imported in its test.

**Placeholder scan:** none. The `allow_duplicate=True` outputs require `prevent_initial_call=True` (present on both callbacks that use it).

**Risk note:** `PolylineDecorator` propTypes mark `dash`/`marker`/`arrowHead` as required within a pattern; supplying only `arrowHead` may log a console propType *warning* but renders correctly. Verify arrows visually in the e2e check; if needed, the warning is harmless.
