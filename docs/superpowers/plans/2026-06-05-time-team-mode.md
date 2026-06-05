# Time / Team Mode + Team Carousel Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a header Time/Team mode switch that, in Team mode, replaces the calendar with an endless alphabetical team-logo carousel whose centered team drives the map (its flow lines drawn + its 3 stadiums pulsing).

**Architecture:** A `dmc.Switch` (`mode-toggle`) is the single source of truth for the mode. The header center mounts both the calendar and the carousel and toggles their `display`. A `dcc.Store` (`carousel-index`) tracks the centered team; navigation callbacks move it with modulo wrap. The existing `flow-layer` and `pulse-layer` callbacks become mode-aware (Time = calendar/filter; Team = centered team). The filter pin moves into its own `LayerGroup` so a callback can hide it in Team mode.

**Tech Stack:** Dash 2.18 + dash-mantine-components 2.4 (Mantine 8 / React 18) + dash-leaflet 1.0.11 + dash-iconify. Tests with pytest. **Runtime is conda base** — run tests with `~/anaconda3/bin/conda run -n base python -m pytest tests/ -q`.

**Spec:** `docs/superpowers/specs/2026-06-05-time-team-mode-design.md`

> **Environment note:** This project is NOT a git repo. The "Commit" steps below are written for completeness/portability but `git` will fail here — when running in this repo, treat each Commit step as a checkpoint (skip the `git` command) and simply confirm the task's tests pass before moving on.

---

## File Structure

| File | Responsibility |
|---|---|
| `src/components/team_carousel.py` | **New.** Pure helpers (`team_order`, `advance`, `window`, `center_team`) + view builder (`carousel_view`, `build_team_carousel`). |
| `src/components/mode_switch.py` | **New.** Module-level `mode_switch` `dmc.Switch` + `MODE_SWITCH_ID`. |
| `src/data/flows.py` | Add pure helper `team_cities(team_flow, stadium_to_city)`. |
| `src/components/map_view.py` | Wrap the filter pin in `LayerGroup id="filter-pin-layer"`. |
| `src/components/layout.py` | Mount calendar + carousel wrappers in center; add mode switch to right zone; add `carousel-index` store. |
| `app.py` | Mode-aware flow/pulse deciders + callbacks; center visibility, carousel nav + render, filter-pin visibility callbacks. |
| `assets/styles.css` | Carousel layout + center/side brightness + accent ring (themed). |
| `tests/test_team_carousel.py` | **New.** Tests for carousel pure functions + view. |

---

## Task 1: Carousel pure functions

**Files:**
- Create: `src/components/team_carousel.py`
- Test: `tests/test_team_carousel.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_team_carousel.py
from src.components.team_carousel import advance, center_team, team_order, window


def test_team_order_is_alphabetical_caseinsensitive():
    flows = {"brazil": object(), "Argentina": object(), "Canada": object()}
    assert team_order(flows) == ["Argentina", "brazil", "Canada"]


def test_advance_wraps_forward_and_backward():
    assert advance(47, +1, 48) == 0
    assert advance(0, -1, 48) == 47
    assert advance(10, +1, 48) == 11


def test_window_returns_prev_center_next_with_wrap():
    teams = ["A", "B", "C", "D"]
    assert window(teams, 0) == ("D", "A", "B")
    assert window(teams, 3) == ("C", "D", "A")
    assert window(teams, 1) == ("A", "B", "C")


def test_center_team_wraps():
    teams = ["A", "B", "C"]
    assert center_team(teams, 0) == "A"
    assert center_team(teams, 3) == "A"
    assert center_team(teams, 5) == "C"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `~/anaconda3/bin/conda run -n base python -m pytest tests/test_team_carousel.py -q`
Expected: FAIL with `ModuleNotFoundError` / `ImportError: cannot import name 'advance'`.

- [ ] **Step 3: Write minimal implementation**

```python
# src/components/team_carousel.py
from __future__ import annotations


def team_order(team_flows: dict) -> list[str]:
    """All teams, alphabetical A→Z (case-insensitive on the raw team name)."""
    return sorted(team_flows.keys(), key=str.casefold)


def advance(index: int, delta: int, n: int) -> int:
    """Move the carousel index with wrap-around (endless loop)."""
    return (index + delta) % n


def window(teams: list[str], index: int) -> tuple[str, str, str]:
    """(prev, center, next) team names with wrap-around. Requires len >= 1."""
    n = len(teams)
    return (teams[(index - 1) % n], teams[index % n], teams[(index + 1) % n])


def center_team(teams: list[str], index: int) -> str:
    return teams[index % len(teams)]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `~/anaconda3/bin/conda run -n base python -m pytest tests/test_team_carousel.py -q`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add src/components/team_carousel.py tests/test_team_carousel.py
git commit -m "feat: carousel index pure functions (order, advance, window)"
```

---

## Task 2: `team_cities` helper in flows.py

**Files:**
- Modify: `src/data/flows.py` (append a function after `team_cities`'s dependencies — end of file is fine)
- Test: `tests/test_flows.py` (append)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_flows.py  (append; reuse existing imports of FlowStop, TeamFlow)
def test_team_cities_maps_stops_through_stadium_to_city():
    from datetime import date

    from src.data.flows import TeamFlow, FlowStop, team_cities

    stops = (
        FlowStop(40.8, -74.0, "MetLife Stadium", date(2026, 6, 13), 7),
        FlowStop(39.9, -75.1, "Lincoln Financial Field", date(2026, 6, 19), 40),
        FlowStop(39.9, -75.1, "Lincoln Financial Field", date(2026, 6, 24), 60),
    )
    flow = TeamFlow("Brazil", "South America", "#22c55e", stops, 1839.7)
    stadium_to_city = {
        "MetLife Stadium": "New York New Jersey",
        "Lincoln Financial Field": "Philadelphia",
        "Other Stadium": "Dallas",
    }
    # De-duplicates by city; ignores stadiums absent from the map.
    assert team_cities(flow, stadium_to_city) == {"New York New Jersey", "Philadelphia"}


def test_team_cities_ignores_unknown_stadiums():
    from datetime import date

    from src.data.flows import TeamFlow, FlowStop, team_cities

    stops = (FlowStop(1.0, 2.0, "Ghost Stadium", date(2026, 6, 13), 1),)
    flow = TeamFlow("X", "Y", "#fff", stops, 0.0)
    assert team_cities(flow, {"Real Stadium": "City"}) == set()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `~/anaconda3/bin/conda run -n base python -m pytest tests/test_flows.py -q`
Expected: FAIL with `ImportError: cannot import name 'team_cities'`.

- [ ] **Step 3: Write minimal implementation**

Append to `src/data/flows.py`:

```python
def team_cities(team_flow: TeamFlow, stadium_to_city: dict[str, str]) -> set[str]:
    """The set of host cities a team plays its group-stage matches in."""
    return {
        stadium_to_city[s.stadium_name]
        for s in team_flow.stops
        if s.stadium_name in stadium_to_city
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `~/anaconda3/bin/conda run -n base python -m pytest tests/test_flows.py -q`
Expected: PASS (all flows tests, including the 2 new).

- [ ] **Step 5: Commit**

```bash
git add src/data/flows.py tests/test_flows.py
git commit -m "feat: team_cities helper mapping flow stops to host cities"
```

---

## Task 3: Carousel view + builder

The carousel has a **fixed shell** (built once) so clickable elements keep stable
ids (reliable `n_clicks`); only the three image `src`s and the center name text
change per index. `carousel_view` is the pure function that computes those four
values; `build_team_carousel` builds the shell.

**Files:**
- Modify: `src/components/team_carousel.py`
- Test: `tests/test_team_carousel.py` (append)

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_team_carousel.py  (append)
import dash_mantine_components as dmc

from src.components.team_carousel import build_team_carousel, carousel_view


def _asset(path):  # mimic app.get_asset_url
    return "/assets/" + path


def _walk(node):
    yield node
    children = getattr(node, "children", None)
    if isinstance(children, (list, tuple)):
        for c in children:
            yield from _walk(c)
    elif children is not None:
        yield from _walk(children)


def test_carousel_view_returns_three_srcs_and_center_name():
    teams = ["Argentina", "Brazil", "Canada"]
    view = carousel_view(teams, 1, _asset)
    assert view["center_name"] == "Brazil"
    assert view["center_src"] == "/assets/country_logos/Brazil.svg"
    assert view["prev_src"] == "/assets/country_logos/Argentina.svg"
    assert view["next_src"] == "/assets/country_logos/Canada.svg"


def test_carousel_view_wraps_at_index_zero():
    teams = ["Argentina", "Brazil", "Canada"]
    view = carousel_view(teams, 0, _asset)
    assert view["center_name"] == "Argentina"
    assert view["prev_src"] == "/assets/country_logos/Canada.svg"
    assert view["next_src"] == "/assets/country_logos/Brazil.svg"


def test_build_team_carousel_has_expected_ids_and_arrows():
    teams = ["Argentina", "Brazil", "Canada"]
    root = build_team_carousel(teams, _asset, index=0)
    ids = {getattr(n, "id", None) for n in _walk(root)}
    for expected in {
        "team-carousel",
        "carousel-prev",
        "carousel-next",
        "carousel-logo-prev",
        "carousel-logo-next",
        "carousel-logo-center",
        "carousel-img-prev",
        "carousel-img-center",
        "carousel-img-next",
        "carousel-name",
    }:
        assert expected in ids


def test_build_team_carousel_center_image_uses_center_class():
    teams = ["Argentina", "Brazil", "Canada"]
    root = build_team_carousel(teams, _asset, index=0)
    center_img = next(
        n for n in _walk(root)
        if isinstance(n, dmc.Image) and getattr(n, "id", None) == "carousel-img-center"
    )
    assert "carousel-logo--center" in (center_img.className or "")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `~/anaconda3/bin/conda run -n base python -m pytest tests/test_team_carousel.py -q`
Expected: FAIL with `ImportError: cannot import name 'carousel_view'`.

- [ ] **Step 3: Write minimal implementation**

Append to `src/components/team_carousel.py`:

```python
import dash_mantine_components as dmc
from dash_iconify import DashIconify

LOGO_DIR = "country_logos"


def _logo_path(team: str) -> str:
    return f"{LOGO_DIR}/{team}.svg"


def carousel_view(teams: list[str], index: int, asset_url) -> dict:
    """Compute the three logo srcs + center name for a given index (wrap-safe)."""
    prev_t, center_t, next_t = window(teams, index)
    return {
        "prev_src": asset_url(_logo_path(prev_t)),
        "center_src": asset_url(_logo_path(center_t)),
        "next_src": asset_url(_logo_path(next_t)),
        "center_name": center_t,
    }


def _side_button(button_id: str, img_id: str, src: str) -> dmc.UnstyledButton:
    return dmc.UnstyledButton(
        id=button_id,
        className="carousel-logo carousel-logo--side",
        children=dmc.Image(id=img_id, src=src, h=46, w=46, fit="contain"),
    )


def build_team_carousel(teams: list[str], asset_url, index: int = 0) -> dmc.Box:
    """Fixed carousel shell. Navigation/render callbacks (app.py) update the
    image srcs and center name; the clickable ids never change."""
    view = carousel_view(teams, index, asset_url)
    return dmc.Box(
        id="team-carousel",
        className="team-carousel",
        children=[
            dmc.ActionIcon(
                DashIconify(icon="radix-icons:chevron-left", width=22),
                id="carousel-prev",
                variant="subtle",
                size="lg",
                radius="xl",
            ),
            _side_button("carousel-logo-prev", "carousel-img-prev", view["prev_src"]),
            dmc.UnstyledButton(
                id="carousel-logo-center",
                className="carousel-logo carousel-logo--center-wrap",
                children=dmc.Stack(
                    [
                        dmc.Image(
                            id="carousel-img-center",
                            className="carousel-logo--center",
                            src=view["center_src"],
                            h=76,
                            w=76,
                            fit="contain",
                        ),
                        dmc.Text(view["center_name"], id="carousel-name", fw=600, size="sm"),
                    ],
                    gap=6,
                    align="center",
                ),
            ),
            _side_button("carousel-logo-next", "carousel-img-next", view["next_src"]),
            dmc.ActionIcon(
                DashIconify(icon="radix-icons:chevron-right", width=22),
                id="carousel-next",
                variant="subtle",
                size="lg",
                radius="xl",
            ),
        ],
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `~/anaconda3/bin/conda run -n base python -m pytest tests/test_team_carousel.py -q`
Expected: PASS (8 passed).

- [ ] **Step 5: Commit**

```bash
git add src/components/team_carousel.py tests/test_team_carousel.py
git commit -m "feat: team carousel shell + view (3 logos, center label)"
```

---

## Task 4: Mode switch component

**Files:**
- Create: `src/components/mode_switch.py`
- Test: `tests/test_mode_switch.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_mode_switch.py
import dash_mantine_components as dmc

from src.components.mode_switch import MODE_SWITCH_ID, mode_switch


def test_mode_switch_is_a_switch_with_expected_id_and_default():
    assert isinstance(mode_switch, dmc.Switch)
    assert mode_switch.id == MODE_SWITCH_ID == "mode-toggle"
    # Default unchecked == Time mode (preserves current default behavior).
    assert mode_switch.checked is False
    assert mode_switch.persistence is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `~/anaconda3/bin/conda run -n base python -m pytest tests/test_mode_switch.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.components.mode_switch'`.

- [ ] **Step 3: Write minimal implementation**

```python
# src/components/mode_switch.py
from __future__ import annotations

import dash_mantine_components as dmc
from dash_iconify import DashIconify

MODE_SWITCH_ID = "mode-toggle"

# Unchecked = Time (calendar); checked = Team (carousel).
mode_switch = dmc.Switch(
    id=MODE_SWITCH_ID,
    offLabel=DashIconify(icon="radix-icons:calendar", width=15),
    onLabel=DashIconify(icon="mdi:account-group", width=15),
    checked=False,
    persistence=True,
    color="gray",
)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `~/anaconda3/bin/conda run -n base python -m pytest tests/test_mode_switch.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/components/mode_switch.py tests/test_mode_switch.py
git commit -m "feat: Time/Team mode switch component"
```

---

## Task 5: Layout integration (center wrappers, mode switch, store)

`build_layout` gains a `team_carousel` parameter. The center zone wraps the
calendar and the carousel in two `dmc.Box`es (`calendar-wrapper`,
`carousel-wrapper`); the carousel starts hidden (`display: none`) since Time is the
default mode. The mode switch joins the theme toggle in the right zone. A
`dcc.Store id="carousel-index"` is added to the provider.

**Files:**
- Modify: `src/components/layout.py`
- Test: `tests/test_layout.py` (append)

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_layout.py  (append; _walk and VENUES already defined above)
def test_layout_mounts_calendar_and_carousel_wrappers():
    import dash_mantine_components as dmc
    from dash import dcc

    calendar = dmc.MiniCalendar(id="match-calendar", value="2026-05-30")
    carousel = dmc.Box(id="team-carousel", children=[])
    layout = build_layout(VENUES, match_calendar=calendar, team_carousel=carousel)

    ids = {getattr(n, "id", None) for n in _walk(layout)}
    assert "calendar-wrapper" in ids
    assert "carousel-wrapper" in ids
    assert "team-carousel" in ids

    # Carousel wrapper starts hidden (Time is the default mode).
    carousel_wrapper = next(
        n for n in _walk(layout)
        if isinstance(n, dmc.Box) and getattr(n, "id", None) == "carousel-wrapper"
    )
    assert carousel_wrapper.style.get("display") == "none"

    # The carousel-index store is present.
    stores = [n for n in _walk(layout) if isinstance(n, dcc.Store)]
    assert "carousel-index" in {s.id for s in stores}


def test_layout_header_contains_mode_switch():
    from src.components.mode_switch import MODE_SWITCH_ID

    layout = build_layout(VENUES)
    switch_ids = {
        getattr(n, "id", None) for n in _walk(layout)
        if getattr(n, "id", None) in {MODE_SWITCH_ID, "color-scheme-toggle"}
    }
    assert MODE_SWITCH_ID in switch_ids
    assert "color-scheme-toggle" in switch_ids
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `~/anaconda3/bin/conda run -n base python -m pytest tests/test_layout.py -q`
Expected: FAIL (`calendar-wrapper` not found / `team_carousel` is an unexpected kwarg is not the case since default None — it will fail on the wrapper assertion).

- [ ] **Step 3: Write minimal implementation**

In `src/components/layout.py`:

1. Update imports at top (add `dcc` and the mode switch):

```python
from dash import dcc, html
from src.components.mode_switch import mode_switch
```

2. Replace the `build_layout` signature and the center/right zone construction. Replace the existing `left`/`center`/`right`/`header` block and the `return` so it reads:

```python
def build_layout(
    venues: list[Venue],
    team_options: list | None = None,
    team_flows: dict | None = None,
    match_calendar=None,
    team_carousel=None,
) -> dmc.MantineProvider:
    # Three equal-flex zones so the centre widget sits at the true centre of the
    # header regardless of the brand / controls widths.
    left = dmc.Box(
        _brand(),
        style={"flex": "1 1 0", "display": "flex", "justifyContent": "flex-start"},
    )
    # Both centre widgets are always mounted; a callback toggles their display.
    calendar_wrapper = dmc.Box(match_calendar, id="calendar-wrapper")
    carousel_wrapper = dmc.Box(
        team_carousel, id="carousel-wrapper", style={"display": "none"}
    )
    center = dmc.Box(
        [calendar_wrapper, carousel_wrapper],
        style={"flex": "0 0 auto", "display": "flex", "justifyContent": "center"},
    )
    right = dmc.Box(
        dmc.Group([mode_switch, theme_toggle], gap="sm", wrap="nowrap"),
        style={"flex": "1 1 0", "display": "flex", "justifyContent": "flex-end"},
    )
    header = dmc.AppShellHeader(
        dmc.Group(
            [left, center, right],
            justify="space-between",
            align="center",
            h="100%",
            px="md",
            wrap="nowrap",
            gap="sm",
        )
    )

    main = dmc.AppShellMain(html.Div(build_map(venues), id="map-container"))

    shell = dmc.AppShell(
        [header, main],
        header={"height": 60},
        padding=0,
        id="appshell",
    )

    drawer = dmc.Drawer(
        id="stadium-drawer",
        position="left",
        size="md",
        padding="md",
        opened=False,
        withCloseButton=True,
        zIndex=DRAWER_Z_INDEX,
    )

    filter_drawer = build_filter_drawer(team_options or [], team_flows or {})

    return dmc.MantineProvider(
        [shell, drawer, filter_drawer, dcc.Store(id="carousel-index", data=0, storage_type="local")],
        id="mantine-provider",
        defaultColorScheme=DEFAULT_COLOR_SCHEME,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `~/anaconda3/bin/conda run -n base python -m pytest tests/test_layout.py -q`
Expected: PASS (all layout tests, including the 2 new). The existing
`test_header_contains_match_calendar_when_provided` still passes (the MiniCalendar
is still the only one, now inside `calendar-wrapper`).

- [ ] **Step 5: Commit**

```bash
git add src/components/layout.py tests/test_layout.py
git commit -m "feat: mount calendar+carousel wrappers, mode switch, index store"
```

---

## Task 6: Filter pin in its own layer

Wrap the filter pin in `LayerGroup id="filter-pin-layer"` so a callback can clear
it in Team mode. Two existing map tests assert the pin as a direct child of the
map — update them to search the whole tree.

**Files:**
- Modify: `src/components/map_view.py:104-124` (the `build_map` children list)
- Test: `tests/test_map_view.py` (update 2 tests)

- [ ] **Step 1: Update the failing tests**

Replace `test_map_has_flow_layer_and_filter_pin` and `test_filter_pin_uses_a_plane_icon` in `tests/test_map_view.py` with tree-walking versions, and add a layer test:

```python
def test_map_has_flow_layer_and_filter_pin():
    from src.components.map_view import FILTER_PIN
    m = build_map(VENUES)
    children = m.children if isinstance(m.children, list) else [m.children]
    layer_ids = [getattr(c, "id", None) for c in children]
    assert "flow-layer" in layer_ids
    assert "filter-pin-layer" in layer_ids
    pins = [
        c for c in _walk(m)
        if isinstance(c, dl.DivMarker) and getattr(c, "id", None) == "filter-pin"
    ]
    assert len(pins) == 1
    assert pins[0].position == FILTER_PIN


def test_filter_pin_lives_inside_filter_pin_layer():
    m = build_map(VENUES)
    children = m.children if isinstance(m.children, list) else [m.children]
    layer = next(
        c for c in children
        if isinstance(c, dl.LayerGroup) and getattr(c, "id", None) == "filter-pin-layer"
    )
    pin_ids = [getattr(n, "id", None) for n in _walk(layer)]
    assert "filter-pin" in pin_ids


def test_filter_pin_uses_a_plane_icon():
    m = build_map(VENUES)
    pin = next(
        c for c in _walk(m)
        if isinstance(c, dl.DivMarker) and getattr(c, "id", None) == "filter-pin"
    )
    html = pin.iconOptions["html"]
    assert 'data-icon="plane"' in html
    assert "22 3 2 3 10 12.46" not in html
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `~/anaconda3/bin/conda run -n base python -m pytest tests/test_map_view.py -q`
Expected: FAIL (`filter-pin-layer` not found in `build_map` children).

- [ ] **Step 3: Write minimal implementation**

In `src/components/map_view.py`, change the `build_map` children list so the pin is
wrapped in a LayerGroup:

```python
        children=[
            dl.TileLayer(id="base-tiles", url=DARK_TILE, attribution=TILE_ATTRIBUTION),
            dl.LayerGroup(id="venue-layer", children=venue_markers(venues)),
            dl.LayerGroup(id="pulse-layer"),
            dl.LayerGroup(id="flow-layer"),
            dl.LayerGroup(id="filter-pin-layer", children=[_filter_pin()]),
        ],
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `~/anaconda3/bin/conda run -n base python -m pytest tests/test_map_view.py -q`
Expected: PASS (all map_view tests).

- [ ] **Step 5: Commit**

```bash
git add src/components/map_view.py tests/test_map_view.py
git commit -m "refactor: move filter pin into its own LayerGroup for show/hide"
```

---

## Task 7: Mode-aware deciders in app.py

Add `TEAM_NAMES`, factor the date→cities logic into `_active_cities_for_date`, and
add the two pure deciders. These are importable and unit-tested without firing
callbacks.

**Files:**
- Modify: `app.py`
- Test: `tests/test_app.py` (append)

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_app.py  (append)
def test_app_team_names_alphabetical_48():
    import app

    assert len(app.TEAM_NAMES) == 48
    assert app.TEAM_NAMES == sorted(app.TEAM_NAMES, key=str.casefold)


def test_flow_children_for_mode_team_uses_centered_team():
    import dash_leaflet as dl

    import app

    idx = app.TEAM_NAMES.index("Brazil")
    # Team mode: filter value is ignored; centered team's flow is drawn.
    children = app.flow_children_for_mode(True, ["Argentina"], idx)
    assert any(isinstance(c, dl.Polyline) for c in children)


def test_flow_children_for_mode_time_uses_filter():
    import dash_leaflet as dl

    import app

    children = app.flow_children_for_mode(False, ["Brazil"], 0)
    assert any(isinstance(c, dl.Polyline) for c in children)
    assert app.flow_children_for_mode(False, [], 0) == []


def test_pulse_children_for_mode_team_pulses_centered_team_cities():
    import app

    idx = app.TEAM_NAMES.index("Brazil")
    rings = app.pulse_children_for_mode(True, None, idx)
    # Brazil plays three group-stage matches → up to three distinct host cities.
    assert 1 <= len(rings) <= 3


def test_pulse_children_for_mode_time_uses_date_logic():
    import app

    # An out-of-tournament / None date yields no pulses in Time mode.
    assert app.pulse_children_for_mode(False, None, 0) == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `~/anaconda3/bin/conda run -n base python -m pytest tests/test_app.py -q`
Expected: FAIL with `AttributeError: module 'app' has no attribute 'TEAM_NAMES'`.

- [ ] **Step 3: Write minimal implementation**

In `app.py`:

1. Add the import near the other component imports:

```python
from src.components.team_carousel import build_team_carousel, team_order
from src.data.flows import build_team_flows, team_cities
```

(The existing `from src.data.flows import build_team_flows` line is replaced by the
two-name import above.)

2. After `TEAM_OPTIONS = grouped_team_options(...)` add:

```python
TEAM_NAMES = team_order(TEAM_FLOWS)
```

3. Refactor `pulses_for_date` into a cities helper and add the deciders. Replace the
existing `pulses_for_date` function with:

```python
def _active_cities_for_date(selected_date: str | None) -> set[str]:
    """Host cities with a match on the selected date (Time mode)."""
    if not selected_date:
        return set()
    try:
        day = date.fromisoformat(str(selected_date)[:10])
    except ValueError:
        return set()
    return MATCH_CALENDAR.active_cities(day)


def flow_children_for_mode(team_mode, filter_value, index):
    """Team mode → the centered team's flow; Time mode → the filter multiselect."""
    if team_mode:
        selected = [TEAM_NAMES[(index or 0) % len(TEAM_NAMES)]]
    else:
        selected = filter_value
    return flow_children(selected)


def pulse_children_for_mode(team_mode, selected_date, index):
    """Team mode → centered team's cities; Time mode → the date's active cities."""
    if team_mode:
        center = TEAM_NAMES[(index or 0) % len(TEAM_NAMES)]
        active = team_cities(TEAM_FLOWS[center], STADIUM_TO_CITY)
    else:
        active = _active_cities_for_date(selected_date)
    return pulse_markers(VENUES, active)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `~/anaconda3/bin/conda run -n base python -m pytest tests/test_app.py -q`
Expected: PASS (all app tests, including the 5 new).

- [ ] **Step 5: Commit**

```bash
git add app.py tests/test_app.py
git commit -m "feat: mode-aware flow/pulse deciders + TEAM_NAMES"
```

---

## Task 8: Wire callbacks in app.py

Build the carousel into the layout, and register the visibility / navigation /
render / mode-aware-layer / pin-visibility callbacks. The old single
`update_flows` (which output both `flow-layer` and `filter-legend`) and
`highlight_active_stadiums` callbacks are replaced.

**Files:**
- Modify: `app.py`
- Test: `tests/test_app.py` (append — verifies the app still builds with the carousel and that callbacks are registered)

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_app.py  (append)
def test_app_layout_contains_carousel_and_mode_switch():
    import app

    def walk(node):
        yield node
        ch = getattr(node, "children", None)
        if isinstance(ch, (list, tuple)):
            for c in ch:
                yield from walk(c)
        elif ch is not None:
            yield from walk(ch)

    ids = {getattr(n, "id", None) for n in walk(app.app.layout)}
    assert "team-carousel" in ids
    assert "mode-toggle" in ids
    assert "carousel-index" in ids


def test_app_registers_mode_callbacks():
    import app

    outputs = set()
    for cb in app.app.callback_map.values():
        for o in cb["output"] if isinstance(cb["output"], list) else [cb["output"]]:
            outputs.add(str(o))
    joined = " ".join(outputs)
    assert "carousel-index.data" in joined
    assert "filter-pin-layer.children" in joined
    assert "carousel-wrapper.style" in joined
```

> Note: `app.app.callback_map` keys/values are Dash internals; the test only checks
> that the documented outputs appear somewhere, so it is robust to Dash's exact
> representation. If `callback_map` shape differs, fall back to asserting the
> callbacks by importing and confirming `app.app.layout` builds (the first test).

- [ ] **Step 2: Run tests to verify they fail**

Run: `~/anaconda3/bin/conda run -n base python -m pytest tests/test_app.py -q`
Expected: FAIL (`team-carousel` not in layout — carousel not yet built in).

- [ ] **Step 3: Write minimal implementation**

In `app.py`:

1. Pass the carousel into the layout. Replace the `app.layout = build_layout(...)`
call with:

```python
TEAM_CAROUSEL = build_team_carousel(TEAM_NAMES, app.get_asset_url, index=0)
app.layout = build_layout(
    VENUES,
    TEAM_OPTIONS,
    TEAM_FLOWS,
    match_calendar=build_match_calendar(MATCH_CALENDAR),
    team_carousel=TEAM_CAROUSEL,
)
```

> `app` (the Dash instance) must exist before `app.get_asset_url` is called, so keep
> the `app = Dash(__name__)` line above this block (it already is).

2. Add `from src.components.team_carousel import advance, carousel_view` to the
existing team_carousel import line so it reads:

```python
from src.components.team_carousel import advance, build_team_carousel, carousel_view, team_order
```

3. Replace the existing `update_flows` callback with a split flow callback + legend
callback, and add the new callbacks. Remove the old `highlight_active_stadiums`
callback (its logic now lives in the mode-aware pulse callback):

```python
@callback(
    Output("flow-layer", "children"),
    Input("mode-toggle", "checked"),
    Input("team-filter", "value"),
    Input("carousel-index", "data"),
)
def update_flow_layer(team_mode, filter_value, index):
    return flow_children_for_mode(team_mode, filter_value, index)


@callback(
    Output("filter-legend", "children"),
    Input("team-filter", "value"),
)
def update_filter_legend(selected):
    return legend(selected, TEAM_FLOWS)


@callback(
    Output("pulse-layer", "children"),
    Input("mode-toggle", "checked"),
    Input("match-calendar", "value"),
    Input("carousel-index", "data"),
)
def update_pulse_layer(team_mode, selected_date, index):
    return pulse_children_for_mode(team_mode, selected_date, index)


@callback(
    Output("calendar-wrapper", "style"),
    Output("carousel-wrapper", "style"),
    Input("mode-toggle", "checked"),
)
def toggle_center_widget(team_mode):
    hidden = {"display": "none"}
    shown = {"display": "block"}
    return (hidden, shown) if team_mode else (shown, hidden)


@callback(
    Output("filter-pin-layer", "children"),
    Output("filter-drawer", "opened", allow_duplicate=True),
    Input("mode-toggle", "checked"),
    prevent_initial_call=True,
)
def toggle_filter_pin(team_mode):
    from src.components.map_view import _filter_pin

    if team_mode:
        return [], False  # hide the pin and close the filter drawer in Team mode
    return [_filter_pin()], no_update


@callback(
    Output("carousel-index", "data"),
    Input("carousel-prev", "n_clicks"),
    Input("carousel-next", "n_clicks"),
    Input("carousel-logo-prev", "n_clicks"),
    Input("carousel-logo-next", "n_clicks"),
    State("carousel-index", "data"),
    prevent_initial_call=True,
)
def move_carousel(_p, _n, _lp, _ln, index):
    back = {"carousel-prev", "carousel-logo-prev"}
    delta = -1 if ctx.triggered_id in back else 1
    return advance(index or 0, delta, len(TEAM_NAMES))


@callback(
    Output("carousel-img-prev", "src"),
    Output("carousel-img-center", "src"),
    Output("carousel-img-next", "src"),
    Output("carousel-name", "children"),
    Input("carousel-index", "data"),
)
def render_carousel(index):
    view = carousel_view(TEAM_NAMES, index or 0, app.get_asset_url)
    return view["prev_src"], view["center_src"], view["next_src"], view["center_name"]
```

4. Add `State` to the dash import line:

```python
from dash import ALL, Dash, Input, Output, State, callback, clientside_callback, ctx, no_update
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `~/anaconda3/bin/conda run -n base python -m pytest tests/ -q`
Expected: PASS (full suite). If the `callback_map` introspection test is brittle on
this Dash version, simplify it to assert only the layout-contains test and that
`app.app` builds.

- [ ] **Step 5: Commit**

```bash
git add app.py tests/test_app.py
git commit -m "feat: wire Time/Team mode callbacks (visibility, nav, render, layers, pin)"
```

---

## Task 9: Carousel styling

**Files:**
- Modify: `assets/styles.css` (append)

- [ ] **Step 1: Add the CSS**

Append to `assets/styles.css`:

```css
/* ---- Team carousel (header centre, Team mode) ---- */
.team-carousel {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 16px;
    height: 56px; /* match the calendar's footprint so the header doesn't reflow */
}

/* Clickable logo wrappers reset button chrome. */
.carousel-logo {
    background: transparent;
    border: none;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
}

/* Side (prev/next) logos are dimmed and slightly smaller. */
.carousel-logo--side {
    opacity: 0.45;
    transition: opacity 0.2s ease;
}
.carousel-logo--side:hover {
    opacity: 0.7;
}

/* Centre logo: full brightness with an accent ring + glow (themed). */
.carousel-logo--center-wrap {
    cursor: default;
}
.carousel-logo--center {
    --marker-rgb: 56, 189, 248; /* sky-400 (dark default) */
    border-radius: 50%;
    box-shadow:
        0 0 0 3px rgb(var(--marker-rgb)),
        0 0 16px 2px rgba(var(--marker-rgb), 0.55);
}
[data-mantine-color-scheme="light"] .carousel-logo--center {
    --marker-rgb: 225, 29, 72; /* rose-600 */
}
```

- [ ] **Step 2: Manual verification**

Run the app (`~/anaconda3/bin/conda run -n base python app.py`), flip the mode switch
to Team: the calendar is replaced by the carousel; the centered logo is bright with
an accent ring and a name label, neighbours are dimmed; arrows / side logos scroll
(wrapping past the ends); the map shows the centered team's flow + 3 pulsing
stadiums; the plane pin disappears. Flip back to Time: calendar returns, date pulses
work, plane pin reappears.

- [ ] **Step 3: Commit**

```bash
git add assets/styles.css
git commit -m "style: team carousel layout, dimmed neighbours, accent ring"
```

---

## Final verification

- [ ] Run the full suite: `~/anaconda3/bin/conda run -n base python -m pytest tests/ -q` — all green.
- [ ] Manual smoke test of both modes per Task 9 Step 2.
```
