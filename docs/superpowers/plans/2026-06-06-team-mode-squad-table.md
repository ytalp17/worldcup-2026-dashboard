# Team-Mode Squad Table Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a per-team squad table (dash-ag-grid) to the Team-mode bento dashboard, updating with the carousel.

**Architecture:** A pandas-backed `squads.py` data layer (CSV → canonical-named `Squad`/`Player` objects) feeds a `squad_table.py` component (ag-grid styled like the group grid). The bento grid is rearranged to give the squad a full-height right strip. A carousel-index callback re-renders the grid rows; a clientside callback syncs the grid theme.

**Tech Stack:** Dash 2.18, dash-ag-grid 32.3.2, dash-mantine-components 2.4, pandas. Runtime = conda base (`~/anaconda3/bin/conda run -n base python -m pytest tests/ -v`).

---

## Conventions

- Run unit tests with: `~/anaconda3/bin/conda run -n base python -m pytest tests/ -v`
- Canonical team names match `assets/country_logos/<name>.svg` and the carousel.
- Commit messages end with the Co-Authored-By trailer for Claude Opus 4.8 (1M context).

---

### Task 1: Squad data layer (`src/data/squads.py`)

**Files:**
- Create: `src/data/squads.py`
- Test: `tests/test_squads.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_squads.py
from pathlib import Path
from src.data.squads import Player, Squad, SquadRepository, squad_for_team

CSV = Path(__file__).parent.parent / "assets" / "data" / "world_cup_2026_squads.csv"


def _load():
    return SquadRepository(CSV).load()


def test_loads_all_48_teams_keyed_by_canonical_name():
    squads = _load()
    assert len(squads) == 48
    # CSV "South Korea" is keyed under the canonical "Korea Republic".
    assert "Korea Republic" in squads
    assert "South Korea" not in squads
    # Identity case unchanged.
    assert "Brazil" in squads


def test_all_overrides_resolve():
    squads = _load()
    for canonical in [
        "Bosnia and Herzegovina", "Cabo Verde", "Curaçao", "Czechia",
        "Congo DR", "IR Iran", "Côte d'Ivoire", "Korea Republic",
        "Türkiye", "USA",
    ]:
        assert canonical in squads, canonical


def test_squad_has_players_with_expected_fields():
    squad = _load()["Canada"]
    assert isinstance(squad, Squad)
    assert squad.name == "Canada"
    assert 23 <= len(squad.players) <= 30
    p = next(pl for pl in squad.players if pl.name == "Alphonso Davies")
    assert isinstance(p, Player)
    assert p.number == 19
    assert p.position == "Left-Back"
    assert p.club == "Bayern Munich"
    assert p.height_m == "1.83"
    assert p.foot == "left"
    assert p.market_value == "€40.00m"


def test_blank_caps_tolerated():
    # Owen Goodman (Canada) has an empty international_caps cell.
    squad = _load()["Canada"]
    p = next(pl for pl in squad.players if pl.name == "Owen Goodman")
    assert p.caps == ""  # blank preserved, no crash


def test_squad_for_team():
    squads = _load()
    assert squad_for_team(squads, "Korea Republic").name == "Korea Republic"
    assert squad_for_team(squads, "Nowhere") is None
```

- [ ] **Step 2: Run tests, verify they fail** (`ModuleNotFoundError: src.data.squads`).

- [ ] **Step 3: Implement `src/data/squads.py`**

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

# CSV team spellings that differ from the app's canonical names (which match the
# carousel and country_logos/<name>.svg). Everything else is identical.
_CANONICAL = {
    "Bosnia-Herzegovina": "Bosnia and Herzegovina",
    "Cape Verde": "Cabo Verde",
    "Curacao": "Curaçao",
    "Czech Republic": "Czechia",
    "DR Congo": "Congo DR",
    "Iran": "IR Iran",
    "Ivory Coast": "Côte d'Ivoire",
    "South Korea": "Korea Republic",
    "Turkey": "Türkiye",
    "United States": "USA",
}


def canonical_team(csv_name: str) -> str:
    return _CANONICAL.get(csv_name, csv_name)


@dataclass(frozen=True)
class Player:
    number: str       # shirt number as string ("" if missing)
    name: str
    position: str     # raw CSV position (e.g. "Centre-Back")
    dob: str
    age: str
    club: str
    height_m: str
    foot: str
    caps: str
    goals: str
    debut: str
    market_value: str


@dataclass(frozen=True)
class Squad:
    name: str                    # canonical team name
    players: tuple[Player, ...]


def _cell(value) -> str:
    """CSV cell -> clean string; NaN/None -> ''."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    text = str(value).strip()
    return "" if text.lower() == "nan" else text


class SquadRepository:
    def __init__(self, path: str | Path):
        self.path = Path(path)

    def load(self) -> dict[str, Squad]:
        df = pd.read_csv(self.path, dtype=str, keep_default_na=False)
        squads: dict[str, list[Player]] = {}
        for _, row in df.iterrows():
            team = canonical_team(_cell(row["country"]))
            squads.setdefault(team, []).append(
                Player(
                    number=_cell(row["shirt_number"]),
                    name=_cell(row["name"]),
                    position=_cell(row["position"]),
                    dob=_cell(row["date_of_birth"]),
                    age=_cell(row["age"]),
                    club=_cell(row["club"]),
                    height_m=_cell(row["height_m"]),
                    foot=_cell(row["foot"]),
                    caps=_cell(row["international_caps"]),
                    goals=_cell(row["international_goals"]),
                    debut=_cell(row["debut"]),
                    market_value=_cell(row["market_value"]),
                )
            )
        return {name: Squad(name, tuple(players)) for name, players in squads.items()}


def squad_for_team(squads: dict[str, Squad], team: str) -> Squad | None:
    return squads.get(team)
```

- [ ] **Step 4: Run tests, verify pass.**
- [ ] **Step 5: Commit** (`feat: add squad data layer`).

---

### Task 2: Squad table component (`src/components/squad_table.py`)

**Files:**
- Create: `src/components/squad_table.py`
- Test: `tests/test_squad_table.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_squad_table.py
import dash_ag_grid as dag
import dash_mantine_components as dmc

from src.components.squad_table import (
    COL_DEFS, build_squad_panel, position_code, squad_rows,
)
from src.data.squads import Player, Squad


def _squad():
    return Squad("Canada", (
        Player(number="19", name="Alphonso Davies", position="Left-Back",
               dob="02/11/2000", age="25", club="Bayern Munich", height_m="1.83",
               foot="left", caps="58", goals="15", debut="14/06/2017",
               market_value="€40.00m"),
        Player(number="18", name="Owen Goodman", position="Goalkeeper",
               dob="27/11/2003", age="22", club="Barnsley FC", height_m="1.93",
               foot="left", caps="", goals="0", debut="01/04/2026",
               market_value="€550k"),
    ))


def test_position_code_maps_known_positions():
    assert position_code("Goalkeeper") == "GK"
    assert position_code("Centre-Back") == "CB"
    assert position_code("Defensive Midfield") == "DM"
    assert position_code("Second Striker") == "SS"


def test_position_code_unknown_falls_back():
    # Non-empty, never crashes.
    assert position_code("Sweeper") != ""


def test_squad_rows_shape_and_formatting():
    rows = squad_rows(_squad())
    assert len(rows) == 2
    davies = rows[0]
    assert davies["number"] == "19"
    assert davies["name"] == "Alphonso Davies"
    assert davies["pos"] == "LB"
    assert davies["age"] == "25"
    assert davies["club"] == "Bayern Munich"
    assert davies["height"] == "1.83 m"
    assert davies["foot"] == "Left"
    assert davies["caps"] == "58"
    assert davies["value"] == "€40.00m"


def test_squad_rows_blank_caps_and_blank_height():
    rows = squad_rows(Squad("X", (
        Player(number="1", name="Z", position="Goalkeeper", dob="", age="",
               club="", height_m="", foot="", caps="", goals="0", debut="",
               market_value=""),
    )))
    assert rows[0]["caps"] == ""
    assert rows[0]["height"] == ""   # blank height not rendered as " m"
    assert rows[0]["foot"] == ""


def test_col_defs_exclude_country_and_team_id():
    fields = {c.get("field") for c in COL_DEFS}
    assert "country" not in fields
    assert "team_id" not in fields
    # Sanity: the displayed columns are present.
    assert {"number", "name", "pos", "value"} <= fields


def test_col_defs_pin_number_and_player_left():
    by_field = {c["field"]: c for c in COL_DEFS}
    assert by_field["number"].get("pinned") == "left"
    assert by_field["name"].get("pinned") == "left"


def test_build_squad_panel_has_grid_and_title():
    panel = build_squad_panel(_squad())
    grids = [n for n in _walk(panel) if isinstance(n, dag.AgGrid)]
    assert len(grids) == 1
    assert grids[0].id == "squad-grid"
    assert len(grids[0].rowData) == 2
    titles = [n for n in _walk(panel)
              if isinstance(n, dmc.Text) and getattr(n, "id", None) == "squad-table-title"]
    assert titles and titles[0].children == "Canada"


def test_build_squad_panel_none_is_empty():
    panel = build_squad_panel(None)
    grids = [n for n in _walk(panel) if isinstance(n, dag.AgGrid)]
    assert grids[0].rowData == []


def _walk(node):
    yield node
    children = getattr(node, "children", None)
    if isinstance(children, (list, tuple)):
        for c in children:
            yield from _walk(c)
    elif children is not None:
        yield from _walk(children)
```

- [ ] **Step 2: Run tests, verify fail** (`ModuleNotFoundError`).

- [ ] **Step 3: Implement `src/components/squad_table.py`**

```python
from __future__ import annotations

import dash_ag_grid as dag
import dash_mantine_components as dmc

from src.data.squads import Squad

POSITION_CODES = {
    "Goalkeeper": "GK",
    "Centre-Back": "CB",
    "Left-Back": "LB",
    "Right-Back": "RB",
    "Defensive Midfield": "DM",
    "Central Midfield": "CM",
    "Attacking Midfield": "AM",
    "Left Midfield": "LM",
    "Right Midfield": "RM",
    "Left Winger": "LW",
    "Right Winger": "RW",
    "Centre-Forward": "CF",
    "Second Striker": "SS",
}


def position_code(position: str) -> str:
    """Short code for a position; falls back to capitalised initials of words."""
    if position in POSITION_CODES:
        return POSITION_CODES[position]
    parts = position.replace("-", " ").split()
    return "".join(p[0] for p in parts).upper() or "?"


# Pinned identity columns stay visible while the stat columns scroll right.
COL_DEFS = [
    {"headerName": "#", "field": "number", "width": 48, "pinned": "left",
     "sortable": False, "cellClass": "squad-grid__num"},
    {"headerName": "Player", "field": "name", "width": 150, "pinned": "left",
     "sortable": False},
    {"headerName": "Pos", "field": "pos", "width": 56, "sortable": False},
    {"headerName": "DOB", "field": "dob", "width": 96, "sortable": False},
    {"headerName": "Age", "field": "age", "width": 56, "sortable": False},
    {"headerName": "Club", "field": "club", "width": 150, "sortable": False},
    {"headerName": "Ht", "field": "height", "width": 70, "sortable": False},
    {"headerName": "Foot", "field": "foot", "width": 64, "sortable": False},
    {"headerName": "Caps", "field": "caps", "width": 56, "sortable": False},
    {"headerName": "Gls", "field": "goals", "width": 56, "sortable": False},
    {"headerName": "Debut", "field": "debut", "width": 96, "sortable": False},
    {"headerName": "Value", "field": "value", "width": 84, "sortable": False},
]

_GRID_OPTIONS = {
    "suppressCellFocus": True,
    "rowHeight": 36,
    "headerHeight": 36,
}


def squad_rows(squad: Squad) -> list[dict]:
    rows = []
    for p in squad.players:
        rows.append({
            "number": p.number,
            "name": p.name,
            "pos": position_code(p.position),
            "dob": p.dob,
            "age": p.age,
            "club": p.club,
            "height": f"{p.height_m} m" if p.height_m else "",
            "foot": p.foot.title() if p.foot else "",
            "caps": p.caps,
            "goals": p.goals,
            "debut": p.debut,
            "value": p.market_value,
        })
    return rows


def build_squad_panel(squad: Squad | None) -> dmc.Box:
    name = squad.name if squad else "—"
    rows = squad_rows(squad) if squad else []

    header = dmc.Stack(
        [
            dmc.Text("Squad", fw=700, size="lg"),
            dmc.Text("World Cup", size="xs", c="dimmed"),
            dmc.Text(name, id="squad-table-title", size="xs", c="dimmed"),
        ],
        gap=2,
        className="squad-panel__header",
    )

    grid = dag.AgGrid(
        id="squad-grid",
        columnDefs=COL_DEFS,
        rowData=rows,
        # No columnSize: fixed widths + a narrower card => native horizontal
        # scroll for the 12 columns; normal domLayout => vertical scroll for rows.
        className="ag-theme-quartz-dark squad-grid",
        dashGridOptions=_GRID_OPTIONS,
        style={"width": "100%", "height": "100%"},
    )

    return dmc.Box([header, grid], className="squad-panel__body")
```

- [ ] **Step 4: Run tests, verify pass.**
- [ ] **Step 5: Commit** (`feat: add squad table component`).

---

### Task 3: Wire squad panel into the layout & bento (`src/components/layout.py`)

**Files:**
- Modify: `src/components/layout.py`
- Test: `tests/test_layout.py`

- [ ] **Step 1: Update the bento test** — replace the e1–e7 assertion with squad + e1–e4.

In `tests/test_layout.py`, change `test_layout_has_bento_with_map_table_and_empty_cards`:

```python
def test_layout_has_bento_with_map_table_squad_and_empty_cards():
    nodes = list(_walk(build_layout(
        VENUES, group_panel=dmc.Box("x"), squad_panel=dmc.Box("y"),
    )))
    classes = _classnames(nodes)
    ids = {nid for n in nodes if isinstance((nid := getattr(n, "id", None)), str)}
    assert "main-split" in classes
    assert "map-container" in ids
    assert "bento-card--map" in classes
    assert "bento-card--table" in classes
    assert "bento-card--squad" in classes
    # Four single-cell empty placeholder cards remain (down from seven).
    for i in range(1, 5):
        assert f"bento-e{i}" in ids
    assert "bento-e5" not in ids
```

Update `test_main_split_defaults_to_time_mode_class` to also pass `squad_panel=dmc.Box("y")` (keyword optional, so not strictly required, but keep call consistent).

- [ ] **Step 2: Run, verify fail** (`bento-card--squad` missing / unexpected `squad_panel` kwarg).

- [ ] **Step 3: Modify `build_layout`** in `src/components/layout.py`:
  - Add `squad_panel=None` to the signature (after `group_panel=None`).
  - After `table_card`, add:
    ```python
    squad_card = dmc.Box(squad_panel, className="bento-card bento-card--squad")
    ```
  - Reduce empty cards to four:
    ```python
    empty_cards = [
        dmc.Box(className="bento-card bento-card--empty", id=f"bento-e{i}")
        for i in range(1, 5)
    ]
    ```
  - Update the main Box children to include the squad card:
    ```python
    main = dmc.AppShellMain(
        dmc.Box(
            [map_card, table_card, squad_card, *empty_cards],
            id="main-split",
            className="main-split",
        )
    )
    ```

- [ ] **Step 4: Run tests, verify pass.**
- [ ] **Step 5: Commit** (`feat: mount squad card in bento layout`).

---

### Task 4: Bento + squad-grid CSS (`assets/styles.css`)

**Files:**
- Modify: `assets/styles.css`

No unit test (CSS); verified via Playwright in Task 6.

- [ ] **Step 1: Replace the `.main-split--team` grid template** (the `grid-template-columns/rows/areas` block) with:

```css
.main-split--team {
    grid-template-columns: 1.3fr 1.3fr 1fr 1.4fr;
    grid-template-rows: 1.4fr 1fr 1fr;
    grid-template-areas:
        "map  map  table squad"
        "map  map  e1    squad"
        "e2   e3   e4    squad";
    gap: 12px;
    padding: 12px;
}
```

- [ ] **Step 2: Replace the grid-area assignment block** (`--table` + `#bento-e1..e7`) with:

```css
.main-split--team .bento-card--table { grid-area: table; }
.main-split--team .bento-card--squad { grid-area: squad; }
.main-split--team #bento-e1 { grid-area: e1; }
.main-split--team #bento-e2 { grid-area: e2; }
.main-split--team #bento-e3 { grid-area: e3; }
.main-split--team #bento-e4 { grid-area: e4; }
```

- [ ] **Step 3: Add squad panel styles** after the group-grid block (before the mobile media query):

```css
/* --- squad table (lives in the full-height squad card) --- */

.squad-panel__body {
    display: flex;
    flex-direction: column;
    height: 100%;
    padding: 12px 14px;
    gap: 8px;
    overflow: hidden;   /* the grid itself scrolls */
}

.squad-panel__header {
    flex: 0 0 auto;
}

/* Compact, transparent grid; scrolls both axes inside the card. */
.squad-grid {
    flex: 1 1 auto;
    min-height: 0;      /* allow the flex child to shrink so the grid scrolls */
    --ag-background-color: transparent;
    --ag-odd-row-background-color: transparent;
    --ag-header-background-color: transparent;
    --ag-borders: none;
    --ag-row-border-width: 0;
    --ag-font-size: 13px;
}

.squad-grid .ag-cell,
.squad-grid .ag-header-cell {
    padding-left: 6px !important;
    padding-right: 6px !important;
}

.squad-grid__num {
    color: var(--mantine-color-dimmed);
}
```

- [ ] **Step 4: Update the mobile media query** — add `squad` to the stacked
  `grid-template-areas` (after `table`) and give the squad card a fixed height.
  Inside `@media (max-width: 768px) { .main-split--team { ... } }` set the areas to:

```css
        grid-template-areas:
            "map"
            "table"
            "squad"
            "e1"
            "e2"
            "e3"
            "e4";
```

  and add a rule:

```css
    .main-split--team .bento-card--squad {
        height: 60vh;
    }
```

- [ ] **Step 5: Commit** (`feat: bento + squad-grid styling`).

---

### Task 5: App wiring & callbacks (`app.py`)

**Files:**
- Modify: `app.py`
- Test: `tests/test_app.py`

- [ ] **Step 1: Write failing test** — append to `tests/test_app.py`:

```python
def test_squad_panel_payload_returns_name_and_rows():
    import app as app_module
    name, rows = app_module.squad_panel_payload(0)
    assert isinstance(name, str) and name != ""
    assert isinstance(rows, list) and len(rows) > 0
    # rows are squad_rows dicts
    assert "name" in rows[0] and "pos" in rows[0]


def test_squad_panel_payload_matches_centered_team():
    import app as app_module
    from src.components.team_carousel import center_team
    name, rows = app_module.squad_panel_payload(0)
    expected = center_team(app_module.TEAM_NAMES, 0)
    # The payload name is the squad's canonical team name == centered team.
    assert name == expected
```

(If the existing `tests/test_app.py` imports `app` differently, match its style — use the same import pattern already present in that file.)

- [ ] **Step 2: Run, verify fail** (`AttributeError: module 'app' has no attribute 'squad_panel_payload'`).

- [ ] **Step 3: Modify `app.py`:**
  - Imports:
    ```python
    from src.components.squad_table import build_squad_panel, squad_rows
    from src.data.squads import SquadRepository, squad_for_team
    ```
  - After `GROUPS = build_groups(MATCHES)`:
    ```python
    SQUADS = SquadRepository(DATA_DIR / "world_cup_2026_squads.csv").load()
    ```
  - Add payload helper near `group_panel_payload`:
    ```python
    def squad_panel_payload(index):
        """(team_name, rowData) for the centred team at `index`."""
        team = center_team(TEAM_NAMES, index or 0)
        squad = squad_for_team(SQUADS, team)
        name = squad.name if squad else "—"
        rows = squad_rows(squad) if squad else []
        return name, rows
    ```
  - In the `build_layout(...)` call, add:
    ```python
    squad_panel=build_squad_panel(squad_for_team(SQUADS, center_team(TEAM_NAMES, 0))),
    ```
  - After the `update_group_panel` callback, add:
    ```python
    @callback(
        Output("squad-grid", "rowData"),
        Output("squad-table-title", "children"),
        Input("carousel-index", "data"),
    )
    def update_squad_panel(index):
        name, rows = squad_panel_payload(index)
        return rows, name
    ```
  - After the `_GRID_THEME_JS` clientside callback for `group-grid`, add a
    matching one for the squad grid:
    ```python
    _SQUAD_GRID_THEME_JS = """
    (checked) => (checked ? 'ag-theme-quartz-dark squad-grid'
                          : 'ag-theme-quartz squad-grid')
    """

    clientside_callback(
        _SQUAD_GRID_THEME_JS,
        Output("squad-grid", "className"),
        Input("color-scheme-toggle", "checked"),
    )
    ```

- [ ] **Step 4: Run tests, verify pass; run the full suite** (`pytest tests/ -v`) to confirm no regressions.
- [ ] **Step 5: Boot smoke-check** — `~/anaconda3/bin/conda run -n base python -c "import app; print('OK', app.app.layout.id)"`.
- [ ] **Step 6: Commit** (`feat: wire squad panel callbacks`).

---

### Task 6: Playwright e2e verification (`scripts/e2e_squad_panel.py`)

**Files:**
- Create: `scripts/e2e_squad_panel.py`

Run with Framework 3.11 python (has playwright + cached Chromium); see
[[e2e-playwright-setup]]. NOT a pytest test.

- [ ] **Step 1: Write the script** (model it on `scripts/e2e_group_panel.py`): serve
  `app.app.run(port=…)` on a background thread, drive headless Chromium. Checks:
  1. Time mode: squad card hidden (only map visible).
  2. Flip to Team mode: `.bento-card--squad` visible.
  3. `#squad-grid` renders ≥ 20 player rows for the default team.
  4. `#squad-table-title` text equals the centered team name.
  5. The squad grid has a horizontal scrollbar (total column width > card width):
     check `.ag-center-cols-viewport` `scrollWidth > clientWidth`.
  6. Click carousel-next → squad rows change (different first player name / title).
  7. Toggle theme → `#squad-grid` className flips quartz ↔ quartz-dark.
  8. Map remains the largest card (bounding box area > squad card).
  9. Mobile viewport (390px): cards stack single-column, no horizontal page overflow.

- [ ] **Step 2: Run it** with the Framework python; iterate until all checks PASS.
  Capture a screenshot to a fresh filename for visual confirmation.

- [ ] **Step 3: Commit** (`test: e2e squad panel checks`).

---

## Self-Review Notes

- Type consistency: `Player`/`Squad` fields used in Task 2 match Task 1's
  dataclass exactly (`number, name, position, dob, age, club, height_m, foot,
  caps, goals, debut, market_value`).
- `squad_rows` field keys (`number, name, pos, dob, age, club, height, foot,
  caps, goals, debut, value`) match `COL_DEFS` `field`s exactly.
- Layout `squad_panel` kwarg threads through `build_layout` → `app.py`.
- Empty-card count change (7→4) is covered by the updated layout test.
