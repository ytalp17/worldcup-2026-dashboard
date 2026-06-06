# Team-Mode Group Standings Panel — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** In Team mode, split the main area so the map fills ~2/3 on the right and a left-side `dash-ag-grid` panel shows the centred team's group standings (all stats `0` for now); Time mode stays full-width map.

**Architecture:** `mode-toggle.checked` already drives Team mode and `carousel-index.data` already holds the centred-team index. A new pure data layer (`groups.py`) derives groups from the match CSV; a new component (`group_table.py`) renders the panel with a custom ag-grid flag cell renderer; `layout.py` turns `AppShellMain` into a flex row; `app.py` adds one server content callback and two clientside callbacks (panel visibility + map `invalidateSize`, and grid theme).

**Tech Stack:** Dash 2.18, dash-mantine-components 2.4, dash-ag-grid 32.3.2 (already installed), dash-leaflet 1.0.11, pytest. Runtime is **conda base**: run tests with `~/anaconda3/bin/conda run -n base python -m pytest tests/ -v`.

**Reference spec:** `docs/superpowers/specs/2026-06-06-team-mode-group-standings-design.md`

**Conventions:**
- TDD: write the failing test, watch it fail, implement minimally, watch it pass, commit.
- Tests run under conda base. The exact command for a single file is shown per task.
- CLAUDE.md exception (approved): `dash-ag-grid` is allowed for this table; keep everything else DMC.

---

### Task 1: Shared `display_name` helper (Korea + ampersand)

Promote the private `_display_name` in `team_carousel.py` to a public `display_name`, add a "Korea Republic" → "South Korea" override, and route the carousel through it. The group table will import the same helper so display names are consistent everywhere.

**Files:**
- Modify: `src/components/team_carousel.py` (the `_display_name` function near line 43 and its single caller in `carousel_view` near line 57)
- Test: `tests/test_team_carousel.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_team_carousel.py` (extend the existing import line and append the test):

```python
# add display_name to the existing `from src.components.team_carousel import (...)` block
from src.components.team_carousel import display_name


def test_display_name_applies_overrides_then_ampersand():
    assert display_name("Korea Republic") == "South Korea"
    assert display_name("Bosnia and Herzegovina") == "Bosnia & Herzegovina"
    assert display_name("Brazil") == "Brazil"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `~/anaconda3/bin/conda run -n base python -m pytest tests/test_team_carousel.py::test_display_name_applies_overrides_then_ampersand -v`
Expected: FAIL with `ImportError: cannot import name 'display_name'`.

- [ ] **Step 3: Write minimal implementation**

In `src/components/team_carousel.py`, replace the existing `_display_name` definition:

```python
def _display_name(team: str) -> str:
    """Carousel label for a team: 'and' → '&' to save width (e.g. Bosnia)."""
    return team.replace(" and ", " & ")
```

with:

```python
# A few teams display under a shorter / more familiar name than their raw FIFA
# name. Overrides win; otherwise "and" → "&" to save width (e.g. Bosnia).
_DISPLAY_OVERRIDES = {"Korea Republic": "South Korea"}


def display_name(team: str) -> str:
    """Human-friendly label for a team, used by the carousel and the group table."""
    if team in _DISPLAY_OVERRIDES:
        return _DISPLAY_OVERRIDES[team]
    return team.replace(" and ", " & ")
```

Then update the single caller inside `carousel_view` — change:

```python
        "center_name": _display_name(center_t),
```

to:

```python
        "center_name": display_name(center_t),
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `~/anaconda3/bin/conda run -n base python -m pytest tests/test_team_carousel.py -v`
Expected: PASS (new test plus all existing carousel tests, including the ampersand test).

- [ ] **Step 5: Commit**

```bash
git add src/components/team_carousel.py tests/test_team_carousel.py
git commit -m "refactor: public display_name helper with Korea Republic override"
```

---

### Task 2: Group data layer (`src/data/groups.py`)

Pure module (no Dash) deriving the 12 groups and each group's official team order from the loaded matches, with all standings stats zeroed.

**Files:**
- Create: `src/data/groups.py`
- Test: `tests/test_groups.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_groups.py`:

```python
from datetime import date, datetime, time

from src.data.groups import Group, GroupStanding, build_groups, group_for_team
from src.data.matches import Match


def _m(number, home, away, group, stage="Group Stage"):
    return Match(
        number=number,
        home=home,
        away=away,
        group=group,
        stage=stage,
        stadium="X Stadium",
        date=date(2026, 6, 11),
        local_time=time(13, 0),
        kickoff_utc=datetime.fromisoformat("2026-06-11T19:00:00+00:00"),
    )


def test_group_standing_defaults_are_zero():
    s = GroupStanding(team="Mexico")
    assert (s.played, s.won, s.drawn, s.lost, s.goal_diff, s.points) == (0, 0, 0, 0, 0, 0)


def test_build_groups_orders_by_first_appearance():
    matches = [
        _m(2, "Korea Republic", "Czechia", "Group A"),   # out of order on purpose
        _m(1, "Mexico", "South Africa", "Group A"),
        _m(25, "Czechia", "South Africa", "Group A"),
    ]
    groups = build_groups(matches)
    assert [s.team for s in groups["Group A"].standings] == [
        "Mexico", "South Africa", "Korea Republic", "Czechia"
    ]


def test_build_groups_counts_and_zeroes():
    matches = [
        _m(1, "A", "B", "Group A"),
        _m(2, "C", "D", "Group A"),
        _m(3, "E", "F", "Group B"),
    ]
    groups = build_groups(matches)
    assert set(groups) == {"Group A", "Group B"}
    assert len(groups["Group A"].standings) == 2
    assert all(s.points == 0 and s.played == 0 for s in groups["Group A"].standings)
    assert isinstance(groups["Group A"], Group)


def test_build_groups_ignores_knockout_rows():
    matches = [
        _m(1, "A", "B", "Group A"),
        _m(73, "Winner 1", "Winner 2", "", stage="Round of 32"),
    ]
    groups = build_groups(matches)
    assert set(groups) == {"Group A"}


def test_group_for_team_finds_and_misses():
    groups = build_groups([
        _m(1, "Mexico", "South Africa", "Group A"),
        _m(2, "Canada", "Qatar", "Group B"),
    ])
    assert group_for_team(groups, "Canada").name == "Group B"
    assert group_for_team(groups, "Nowhere") is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `~/anaconda3/bin/conda run -n base python -m pytest tests/test_groups.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.data.groups'`.

- [ ] **Step 3: Write minimal implementation**

Create `src/data/groups.py`:

```python
from __future__ import annotations

from dataclasses import dataclass

from src.data.matches import Match


@dataclass(frozen=True)
class GroupStanding:
    team: str
    played: int = 0
    won: int = 0
    drawn: int = 0
    lost: int = 0
    goal_diff: int = 0
    points: int = 0


@dataclass(frozen=True)
class Group:
    name: str                              # e.g. "Group A"
    standings: tuple[GroupStanding, ...]   # official (seeding) order


def build_groups(matches: list[Match]) -> dict[str, Group]:
    """Map group name -> Group. Teams are ordered by first appearance across the
    group's Group-Stage matches in match_number order; all stats start at zero."""
    order: dict[str, list[str]] = {}
    for m in sorted(matches, key=lambda match: match.number):
        if m.stage != "Group Stage" or not m.group:
            continue
        teams = order.setdefault(m.group, [])
        for team in (m.home, m.away):
            if team not in teams:
                teams.append(team)
    return {
        name: Group(name, tuple(GroupStanding(team=t) for t in teams))
        for name, teams in order.items()
    }


def group_for_team(groups: dict[str, Group], team: str) -> Group | None:
    """The Group a team belongs to, or None if the team is unknown."""
    for group in groups.values():
        if any(s.team == team for s in group.standings):
            return group
    return None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `~/anaconda3/bin/conda run -n base python -m pytest tests/test_groups.py -v`
Expected: PASS (all 5 tests).

- [ ] **Step 5: Commit**

```bash
git add src/data/groups.py tests/test_groups.py
git commit -m "feat: group standings data layer (zeroed, official order)"
```

---

### Task 3: Group panel component (`src/components/group_table.py`)

Builds the rowData and the DMC panel containing the ag-grid. The team column uses a `cellRenderer` named `"TeamCell"` (registered in Task 4).

**Files:**
- Create: `src/components/group_table.py`
- Test: `tests/test_group_table.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_group_table.py`:

```python
import dash_ag_grid as dag

from src.components.group_table import build_group_panel, group_rows
from src.data.groups import Group, GroupStanding


def _asset(path):  # mimic app.get_asset_url
    return "/assets/" + path


def _group():
    return Group(
        name="Group A",
        standings=(
            GroupStanding(team="Mexico"),
            GroupStanding(team="South Africa"),
            GroupStanding(team="Korea Republic"),
            GroupStanding(team="Bosnia and Herzegovina"),
        ),
    )


def _walk(node):
    yield node
    children = getattr(node, "children", None)
    if isinstance(children, (list, tuple)):
        for c in children:
            yield from _walk(c)
    elif children is not None:
        yield from _walk(children)


def test_group_rows_rank_display_name_and_flag():
    rows = group_rows(_group(), _asset)
    assert [r["rank"] for r in rows] == [1, 2, 3, 4]
    # display name is remapped / ampersanded ...
    assert rows[2]["team"] == "South Korea"
    assert rows[3]["team"] == "Bosnia & Herzegovina"
    # ... but the flag url uses the RAW team name.
    assert rows[2]["flag"] == "/assets/country_logos/Korea Republic.svg"
    assert rows[0]["team"] == "Mexico"
    assert rows[0]["flag"] == "/assets/country_logos/Mexico.svg"


def test_group_rows_stats_all_zero():
    rows = group_rows(_group(), _asset)
    for r in rows:
        assert r["mp"] == r["w"] == r["d"] == r["l"] == r["gd"] == r["pts"] == 0


def test_build_group_panel_has_expected_ids_and_team_renderer():
    panel = build_group_panel(_group(), _asset)
    ids = {getattr(n, "id", None) for n in _walk(panel)}
    assert {"group-grid", "group-table-title", "group-extra"} <= ids

    grid = next(n for n in _walk(panel) if isinstance(n, dag.AgGrid))
    team_col = next(c for c in grid.columnDefs if c.get("field") == "team")
    assert team_col["cellRenderer"] == "TeamCell"
    assert len(grid.rowData) == 4


def test_build_group_panel_shows_group_name():
    panel = build_group_panel(_group(), _asset)
    title = next(n for n in _walk(panel) if getattr(n, "id", None) == "group-table-title")
    assert title.children == "Group A"


def test_build_group_panel_handles_none_group():
    panel = build_group_panel(None, _asset)
    grid = next(n for n in _walk(panel) if isinstance(n, dag.AgGrid))
    assert grid.rowData == []
    title = next(n for n in _walk(panel) if getattr(n, "id", None) == "group-table-title")
    assert title.children == "—"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `~/anaconda3/bin/conda run -n base python -m pytest tests/test_group_table.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.components.group_table'`.

- [ ] **Step 3: Write minimal implementation**

Create `src/components/group_table.py`:

```python
from __future__ import annotations

from collections.abc import Callable

import dash_ag_grid as dag
import dash_mantine_components as dmc
from dash_iconify import DashIconify

from src.components.team_carousel import display_name
from src.data.groups import Group

# Narrow, right-aligned numeric column shared by MP/W/D/L/GD/Pts.
_NUM_COL = {
    "width": 46,
    "sortable": False,
    "cellClass": "ag-right-aligned-cell",
    "headerClass": "ag-right-aligned-header",
}

COL_DEFS = [
    {"headerName": "#", "field": "rank", "width": 42, "sortable": False,
     "cellClass": "group-grid__rank"},
    {"headerName": "Team", "field": "team", "cellRenderer": "TeamCell",
     "flex": 1, "minWidth": 130, "sortable": False},
    {"headerName": "MP", "field": "mp", **_NUM_COL},
    {"headerName": "W", "field": "w", **_NUM_COL},
    {"headerName": "D", "field": "d", **_NUM_COL},
    {"headerName": "L", "field": "l", **_NUM_COL},
    {"headerName": "GD", "field": "gd", **_NUM_COL},
    {"headerName": "Pts", "field": "pts", **_NUM_COL,
     "cellStyle": {"fontWeight": 700}},
]

# autoHeight: the grid grows to fit its (4) rows; the panel handles any overflow.
_GRID_OPTIONS = {
    "suppressCellFocus": True,
    "rowHeight": 40,
    "headerHeight": 36,
    "domLayout": "autoHeight",
}


def group_rows(group: Group, asset_url: Callable[[str], str]) -> list[dict]:
    """ag-grid rowData for a group. `team` is the display name; `flag` uses the
    raw team name (country_logos/<raw>.svg); all stats are zero for now."""
    rows: list[dict] = []
    for rank, s in enumerate(group.standings, start=1):
        rows.append({
            "rank": rank,
            "team": display_name(s.team),
            "flag": asset_url(f"country_logos/{s.team}.svg"),
            "mp": s.played,
            "w": s.won,
            "d": s.drawn,
            "l": s.lost,
            "gd": s.goal_diff,
            "pts": s.points,
        })
    return rows


def build_group_panel(group: Group | None, asset_url: Callable[[str], str]) -> dmc.Box:
    """The panel body: header (Table / World Cup / group name + chevron), the
    ag-grid, and an empty flex spacer reserved for future infographics."""
    name = group.name if group else "—"
    rows = group_rows(group, asset_url) if group else []

    header = dmc.Group(
        [
            dmc.Stack(
                [
                    dmc.Text("Table", fw=700, size="lg"),
                    dmc.Text("World Cup", size="xs", c="dimmed"),
                    dmc.Text(name, id="group-table-title", size="xs", c="dimmed"),
                ],
                gap=2,
            ),
            DashIconify(icon="radix-icons:chevron-right", width=20),
        ],
        justify="space-between",
        align="flex-start",
        wrap="nowrap",
        className="group-panel__header",
    )

    grid = dag.AgGrid(
        id="group-grid",
        columnDefs=COL_DEFS,
        rowData=rows,
        columnSize="sizeToFit",
        className="ag-theme-quartz-dark group-grid",
        dashGridOptions=_GRID_OPTIONS,
        style={"width": "100%"},
    )

    return dmc.Box(
        [header, grid, dmc.Box(id="group-extra", style={"flex": "1 1 auto"})],
        className="group-panel__body",
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `~/anaconda3/bin/conda run -n base python -m pytest tests/test_group_table.py -v`
Expected: PASS (all 5 tests).

- [ ] **Step 5: Commit**

```bash
git add src/components/group_table.py tests/test_group_table.py
git commit -m "feat: group standings panel component (ag-grid)"
```

---

### Task 4: TeamCell cell renderer (`assets/dashAgGridComponentFunctions.js`)

dash-ag-grid auto-loads any `assets/dashAgGridComponentFunctions.js` and registers the functions on `window.dashAgGridComponentFunctions`. This renders the flag image + team name in the Team column. Browser code — not unit-tested; verified in Task 8 (Playwright).

**Files:**
- Create: `assets/dashAgGridComponentFunctions.js`

- [ ] **Step 1: Create the renderer file**

Create `assets/dashAgGridComponentFunctions.js`:

```javascript
// Registered automatically by dash-ag-grid. `TeamCell` renders the flag image
// (from row.data.flag) next to the team's display name (the cell value).
var dagcomponentfuncs = (window.dashAgGridComponentFunctions =
    window.dashAgGridComponentFunctions || {});

dagcomponentfuncs.TeamCell = function (props) {
    return React.createElement(
        "div",
        { className: "team-cell" },
        React.createElement("img", {
            src: props.data.flag,
            className: "team-cell__flag",
            alt: "",
        }),
        React.createElement("span", { className: "team-cell__name" }, props.value)
    );
};
```

- [ ] **Step 2: Sanity-check the file is valid JS (no syntax error)**

Run: `node --check assets/dashAgGridComponentFunctions.js && echo OK`
Expected: `OK`. (If `node` is unavailable, skip — the file is verified visually in Task 8.)

- [ ] **Step 3: Commit**

```bash
git add assets/dashAgGridComponentFunctions.js
git commit -m "feat: TeamCell ag-grid renderer (flag + name)"
```

---

### Task 5: Split layout (`src/components/layout.py`)

Turn `AppShellMain` into a flex row holding the existing `map-container` and a new visibility wrapper `group-panel` (hidden by default, mirroring `carousel-wrapper`). Add the `map-resize-tick` store. Add a `group_panel` parameter to `build_layout`.

**Files:**
- Modify: `src/components/layout.py` (`build_layout` signature ~line 45, the `main` assignment ~line 84, and the provider children ~line 104)
- Test: `tests/test_layout.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_layout.py`:

```python
def test_layout_has_split_with_map_and_group_panel():
    nodes = list(_walk(build_layout(VENUES, group_panel=dmc.Box("x"))))
    classnames = {getattr(n, "className", None) for n in nodes}
    ids = {getattr(n, "id", None) for n in nodes}
    assert "main-split" in classnames
    assert "group-panel" in ids
    assert "map-container" in ids


def test_group_panel_wrapper_hidden_by_default():
    panel = next(
        n for n in _walk(build_layout(VENUES, group_panel=dmc.Box("x")))
        if getattr(n, "id", None) == "group-panel"
    )
    assert panel.style == {"display": "none"}


def test_layout_has_map_resize_tick_store():
    stores = [n for n in _walk(build_layout(VENUES)) if isinstance(n, dcc.Store)]
    assert "map-resize-tick" in {s.id for s in stores}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `~/anaconda3/bin/conda run -n base python -m pytest tests/test_layout.py -v`
Expected: FAIL — `build_layout()` has no `group_panel` kwarg / `main-split` not found / no `map-resize-tick` store.

- [ ] **Step 3: Write the implementation**

In `src/components/layout.py`, change the `build_layout` signature from:

```python
def build_layout(
    venues: list[Venue],
    team_options: list | None = None,
    team_flows: dict | None = None,
    match_calendar=None,
    team_carousel=None,
) -> dmc.MantineProvider:
```

to (add the `group_panel` parameter):

```python
def build_layout(
    venues: list[Venue],
    team_options: list | None = None,
    team_flows: dict | None = None,
    match_calendar=None,
    team_carousel=None,
    group_panel=None,
) -> dmc.MantineProvider:
```

Replace the `main` assignment:

```python
    main = dmc.AppShellMain(html.Div(build_map(venues), id="map-container"))
```

with:

```python
    # Team mode reveals a left-side standings panel; the map fills the rest.
    # The panel is hidden by default (a clientside callback shows it in Team mode),
    # mirroring the calendar/carousel wrapper pattern.
    group_panel_wrapper = dmc.Box(
        group_panel, id="group-panel", className="group-panel"
    )
    main = dmc.AppShellMain(
        dmc.Box(
            [
                html.Div(build_map(venues), id="map-container"),
                group_panel_wrapper,
            ],
            className="main-split",
        )
    )
```

(The `MantineProvider` children list is unchanged. An earlier draft added a
`map-resize-tick` store, but the final design dispatches the resize directly from
the panel clientside callback, so no extra store is needed.)

The group-panel wrapper carries `className="group-panel"` only (no inline display
style); it is collapsed by default via CSS and a clientside callback adds the
`group-panel--open` modifier in Team mode (see Task 6 / Task 7).

- [ ] **Step 4: Run tests to verify they pass**

Run: `~/anaconda3/bin/conda run -n base python -m pytest tests/test_layout.py -v`
Expected: PASS (new tests plus all existing layout tests).

- [ ] **Step 5: Commit**

```bash
git add src/components/layout.py tests/test_layout.py
git commit -m "feat: split main into map + group-panel flex row"
```

---

### Task 6: App wiring (`app.py`)

Build `GROUPS`, the initial panel, pass it into `build_layout`, add the `group_panel_payload` pure helper + the server content callback, and the two clientside callbacks (panel visibility + map resize, grid theme).

**Files:**
- Modify: `app.py` (imports ~lines 9-23; data setup ~lines 49-52; layout call ~lines 59-66; add helper + callbacks; clientside block ~lines 287-305)
- Test: `tests/test_app.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_app.py`:

```python
def test_group_panel_payload_for_group_a_team():
    import app

    idx = app.TEAM_NAMES.index("Mexico")
    name, rows = app.group_panel_payload(idx)
    assert name == "Group A"
    assert [r["rank"] for r in rows] == [1, 2, 3, 4]
    assert rows[0]["team"] == "Mexico"
    # Korea Republic is in Group A and shows under its display name.
    assert any(r["team"] == "South Korea" for r in rows)


def test_group_panel_payload_handles_none_index():
    import app

    name, rows = app.group_panel_payload(None)
    # index 0 resolves to the first team alphabetically; it has a real group.
    assert name != "—"
    assert len(rows) == 4
```

- [ ] **Step 2: Run test to verify it fails**

Run: `~/anaconda3/bin/conda run -n base python -m pytest tests/test_app.py::test_group_panel_payload_for_group_a_team -v`
Expected: FAIL with `AttributeError: module 'app' has no attribute 'group_panel_payload'`.

- [ ] **Step 3: Write the implementation**

In `app.py` add imports. Change:

```python
from src.components.flow_layer import flows_for
```

to:

```python
from src.components.flow_layer import flows_for
from src.components.group_table import build_group_panel, group_rows
```

and change:

```python
from src.data.flows import build_team_flows, team_cities
```

to:

```python
from src.data.flows import build_team_flows, team_cities
from src.data.groups import build_groups, group_for_team
```

After the `TEAM_NAMES = team_order(TEAM_FLOWS)` line (~line 51), add:

```python
GROUPS = build_groups(MATCHES)
```

Add the pure helper. Place it just after the existing `flow_children` function (~line 53-55), so it can use `app`... but `app` is defined just below at line 57. Instead, define `group_panel_payload` AFTER `app = Dash(__name__)` (it calls `app.get_asset_url`). Add it immediately after the `TEAM_CAROUSEL = build_team_carousel(...)` line (~line 59):

```python
def group_panel_payload(index):
    """(group_name, rowData) for the centred team at `index`. Used by the
    content callback and the initial panel render."""
    team = center_team(TEAM_NAMES, index or 0)
    group = group_for_team(GROUPS, team)
    name = group.name if group else "—"
    rows = group_rows(group, app.get_asset_url) if group else []
    return name, rows
```

Change the `app.layout = build_layout(...)` call to pass the initial panel:

```python
app.layout = build_layout(
    VENUES,
    TEAM_OPTIONS,
    TEAM_FLOWS,
    match_calendar=build_match_calendar(MATCH_CALENDAR),
    team_carousel=TEAM_CAROUSEL,
    group_panel=build_group_panel(group_for_team(GROUPS, center_team(TEAM_NAMES, 0)), app.get_asset_url),
)
```

Add the server content callback. Place it next to the other carousel callbacks, right after the `render_carousel` callback (~line 271):

```python
@callback(
    Output("group-grid", "rowData"),
    Output("group-table-title", "children"),
    Input("carousel-index", "data"),
)
def update_group_panel(index):
    name, rows = group_panel_payload(index)
    return rows, name
```

Add the two clientside callbacks. After the existing `_TZ_JS` clientside_callback block (~line 305), add:

```python
# Show the standings panel in Team mode; hide it (map fills the width) in Time
# mode. After the CSS width transition, dispatch a window resize so Leaflet runs
# invalidateSize() and re-tiles the resized map (otherwise the newly-exposed
# strip renders gray).
_PANEL_JS = """
(checked) => {
    setTimeout(() => window.dispatchEvent(new Event('resize')), 350);
    return checked ? 'group-panel group-panel--open' : 'group-panel';
}
"""

clientside_callback(
    _PANEL_JS,
    Output("group-panel", "className"),
    Input("mode-toggle", "checked"),
)

# Keep the ag-grid theme in sync with the app's color scheme.
_GRID_THEME_JS = """
(checked) => (checked ? 'ag-theme-quartz-dark group-grid'
                      : 'ag-theme-quartz group-grid')
"""

clientside_callback(
    _GRID_THEME_JS,
    Output("group-grid", "className"),
    Input("color-scheme-toggle", "checked"),
)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `~/anaconda3/bin/conda run -n base python -m pytest tests/test_app.py -v`
Expected: PASS (new tests plus all existing app tests).

- [ ] **Step 5: Verify the app still boots**

Run: `~/anaconda3/bin/conda run -n base python -c "import app; print('OK', app.app.layout.id)"`
Expected: `OK mantine-provider` with no exceptions.

- [ ] **Step 6: Commit**

```bash
git add app.py tests/test_app.py
git commit -m "feat: wire group-standings panel (content + clientside callbacks)"
```

---

### Task 7: Styling (`assets/styles.css`)

The split layout, panel chrome, compact/borderless grid, the team-cell flag, and the mobile stack. No unit test (CSS); verified in Task 8.

**Files:**
- Modify: `assets/styles.css` (append a new section)

- [ ] **Step 1: Append the styles**

Append to `assets/styles.css`:

```css
/* ===== Team-mode group standings panel ===== */

.main-split {
    display: flex;
    height: 100%;
    width: 100%;
}

#map-container {
    flex: 1 1 0;
    min-width: 0;   /* allow the map to shrink below its content width */
    height: 100%;
}

/* Collapsed by default (Time mode). A clientside callback adds
   `group-panel--open` in Team mode; the flex-basis transition gives the swift
   slide-in. `display` is NOT animatable, which is why we animate flex-basis. */
.group-panel {
    order: -1;   /* render on the LEFT of the map (DOM order is map-first for the mobile stack) */
    flex: 0 0 0;
    height: 100%;
    overflow: hidden;
    border-right: 1px solid var(--mantine-color-default-border);
    transition: flex-basis 0.3s ease;
}

.group-panel--open {
    flex-basis: 34%;
}

.group-panel__body {
    display: flex;
    flex-direction: column;
    height: 100%;
    padding: 16px 18px;
    gap: 12px;
}

.group-panel__header {
    flex: 0 0 auto;
}

/* Compact, borderless grid that blends with the panel background. */
.group-grid {
    flex: 0 0 auto;
    --ag-background-color: transparent;
    --ag-odd-row-background-color: transparent;
    --ag-header-background-color: transparent;
    --ag-borders: none;
    --ag-row-border-width: 0;
    --ag-cell-horizontal-padding: 8px;
    --ag-font-size: 13px;
}

.group-grid__rank {
    color: var(--mantine-color-dimmed);
}

.team-cell {
    display: flex;
    align-items: center;
    gap: 8px;
    height: 100%;
}

.team-cell__flag {
    width: 20px;
    height: 14px;
    object-fit: contain;
    border-radius: 2px;
    flex: 0 0 auto;
}

.team-cell__name {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

/* Mobile: stack the map on top and the table below; no horizontal overflow.
   No width animation here — collapse via display, expand below the map. */
@media (max-width: 768px) {
    .main-split {
        flex-direction: column;
    }
    #map-container {
        height: 55vh;
        flex: 0 0 auto;
    }
    .group-panel {
        order: 0;   /* stacked: follow DOM order so the map stays on top */
        flex: 0 0 auto;
        width: 100%;
        border-right: none;
        border-top: 1px solid var(--mantine-color-default-border);
        overflow: auto;
        transition: none;
    }
    .group-panel:not(.group-panel--open) {
        display: none;
    }
    .group-panel--open {
        display: flex;
        flex: 1 1 auto;
    }
}
```

- [ ] **Step 2: Verify the full test suite is still green**

Run: `~/anaconda3/bin/conda run -n base python -m pytest tests/ -v`
Expected: all tests PASS.

- [ ] **Step 3: Commit**

```bash
git add assets/styles.css
git commit -m "style: group-standings panel, grid, team-cell, mobile stack"
```

---

### Task 8: End-to-end visual verification (Playwright)

Confirm the browser-only behaviour the unit tests can't: panel appears in Team mode with the map re-tiling at 2/3 width, flags + names render, the grid theme follows the switch, and Time mode is unchanged.

**Files:**
- Reference: `scripts/e2e_check.py` (existing Playwright pattern)

- [ ] **Step 1: Start the app**

Run: `~/anaconda3/bin/conda run -n base python app.py` (background; serves on http://127.0.0.1:8050)

- [ ] **Step 2: Verify Time mode unchanged**

Load the page. Expect: full-width map, no standings panel visible, calendar in the header.

- [ ] **Step 3: Toggle Team mode and verify the split**

Flip the mode switch. Expect: the carousel replaces the calendar; a left-side panel appears with header "Table / World Cup / Group <X>"; the map shrinks to ~2/3 on the right and **fully re-tiles with no gray strip**; the grid shows 4 rows with flag + name and all-zero stats, **Pts** bold.

- [ ] **Step 4: Navigate the carousel and verify the table follows**

Click a carousel arrow so a team from a different group centres. Expect: the group name and the four rows update to the new team's group; the centred team appears in its row.

- [ ] **Step 5: Toggle the theme and verify grid + Korea name**

Flip the light/dark switch. Expect: the grid restyles between `ag-theme-quartz` and `ag-theme-quartz-dark` to match. Centre Korea Republic (Group A) and confirm the row reads "South Korea".

- [ ] **Step 6: Narrow the viewport and verify the mobile stack**

Resize to ~390px wide. Expect: map on top (~55vh), table stacked below, no horizontal scrollbar.

- [ ] **Step 7: Stop the app**

Stop the background process.

- [ ] **Step 8: Final full-suite run**

Run: `~/anaconda3/bin/conda run -n base python -m pytest tests/ -v`
Expected: all tests PASS.

---

## Self-Review (plan author)

**Spec coverage:** left-side panel Team-mode-only (Tasks 5,6,7) ✓; map 2/3 + invalidateSize (Tasks 5,6,7) ✓; official group order (Task 2) ✓; all-zero stats (Tasks 2,3) ✓; custom flag renderer (Task 4) ✓; Korea→South Korea + ampersand shared helper (Task 1) ✓; 34% width / mobile stack (Task 7) ✓; chevron + group-extra placeholder (Task 3) ✓; grid theme follows switch (Task 6) ✓; carousel-index drives content (Task 6) ✓; CLAUDE.md ag-grid exception noted ✓; all 10 spec tests mapped to Tasks 1-6 ✓; Playwright items (Task 8) ✓.

**Placeholder scan:** none — every code step contains full code; every run step has an exact command + expected output.

**Type consistency:** `display_name` (Task 1) imported in Tasks 3; `GroupStanding`/`Group`/`build_groups`/`group_for_team` (Task 2) used in Tasks 3,6; `group_rows`/`build_group_panel` (Task 3) used in Tasks 5,6; rowData keys (`rank,team,flag,mp,w,d,l,gd,pts`) consistent between `group_rows` (Task 3), `COL_DEFS` fields (Task 3), and `TeamCell` (`props.data.flag`, `props.value`) (Task 4); ids `group-panel` (Task 5 wrapper), `group-grid`/`group-table-title`/`group-extra` (Task 3), `map-resize-tick` (Task 5) match their callback Outputs (Task 6). Consistent.
