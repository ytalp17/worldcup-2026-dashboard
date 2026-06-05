# Team-Mode Group Standings Panel — Design

**Date:** 2026-06-06
**Status:** Approved (pending written-spec review)

## Goal

When **Team mode** is active, split the main area: the map shrinks to ~2/3 width on
the right and a **standings panel** occupies ~1/3 on the **left**. The panel shows the
centred (selected) team's **group** as a `dash-ag-grid` table (rank, team + flag, MP,
W, D, L, GD, Pts). All stats are `0` for now — a results API will populate them later.
**Time mode** is unchanged: full-width map, no panel. On narrow screens the split
stacks vertically (map on top, table below).

## Locked Decisions

| Decision | Choice |
|---|---|
| Panel side | **Left**; map fills the right 2/3 |
| When shown | **Team mode only**; Time mode = today's full-width map |
| Row order (all stats 0) | **Official group order** = first appearance of each team across the group's matches in `match_number` order |
| Mobile | **Stack**: map on top (`55vh`), table below, grid scrolls internally |
| Flag rendering | Custom `dash-ag-grid` cell renderer (`assets/dashAgGridComponentFunctions.js`) — sized flag SVG + name |
| Area below the table | Empty `flex:1` placeholder reserved for future infographics |
| Chevron in header | Decorative only (no behaviour) — YAGNI |
| Team display names | Shared `display_name` helper: "and" → "&" **and** "Korea Republic" → "South Korea" (applied in table **and** carousel) |
| Panel width | `flex:0 0 34%` (≈1/3) |

### CLAUDE.md exception (explicit)

CLAUDE.md hard rule: "UI components: `dash-mantine-components` only." The user explicitly
requested **dash-ag-grid** for this table. The grid is an **approved exception**;
everything around it (panel header, spacing, layout) stays DMC. The ag-grid API is
verified via the **context7 MCP** during implementation. `dash-ag-grid 32.3.2` is
already installed (in `requirements.txt`).

## Data Source

`assets/data/wc2026_matches.csv` already carries a `group` column ("Group A" … "Group L",
12 groups × 4 teams) plus `home_team`/`away_team`/`match_number`/`stage`. No new data files.

**Official order is derivable and verified:** scanning a group's matches in
`match_number` order and collecting each team on first appearance yields the FIFA
seeding order. Confirmed for Group A → `[Mexico, South Africa, Korea Republic, Czechia]`
(matches the reference screenshot). The **raw** team name "Korea Republic" is used for
data/flag lookup; the **display name** is "South Korea" (see `display_name` below).

## Architecture

`mode-toggle.checked` is already the single source of truth for the active mode, and
`carousel-index.data` already holds the centred-team index. Two things react to mode;
one thing reacts to the index:

1. **Layout** — `AppShellMain` becomes a flex **row** holding the existing
   `map-container` (`flex:1`) and a new `group-panel` (`flex:0 0 34%`). The panel is
   `display:none` in Time mode, so the map fills 100%. A CSS transition on the panel
   animates the "swift movement".
2. **Map resize** — when the map container resizes, Leaflet must `invalidateSize()` or
   the newly-exposed strip renders gray. A clientside callback dispatches a
   `window.resize` event shortly after the mode toggle; Leaflet listens to window
   resize and re-tiles.
3. **Panel content** — a server callback on `carousel-index.data` resolves the centred
   team → its `Group` → grid `rowData` + the group-name label.

### New / changed files

| File | Responsibility |
|---|---|
| `src/data/groups.py` | **New.** `GroupStanding`, `Group` dataclasses; `build_groups`, `group_for_team` (pure). |
| `src/components/team_carousel.py` | Promote `_display_name` → public `display_name`; add "Korea Republic" → "South Korea" override. |
| `src/components/group_table.py` | **New.** `group_rows`, `build_group_panel` (DMC header + `dag.AgGrid`). |
| `assets/dashAgGridComponentFunctions.js` | **New.** `TeamCell` cell renderer (flag `<img>` + name). |
| `src/components/layout.py` | `main` → flex-row `main-split` with `map-container` + `group-panel`; add `dcc.Store(id="map-resize-tick")`. |
| `app.py` | `group_panel_payload` pure helper; content callback; clientside visibility+resize callback; clientside grid-theme callback. |
| `assets/styles.css` | `.main-split`, `.group-panel`, `.group-grid` styling; mobile `@media` stack. |
| `tests/test_groups.py`, `tests/test_group_table.py` | **New.** Unit tests (TDD). |

## Component: Data Layer (`src/data/groups.py`)

Pure, no Dash. Tested first.

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
    standings: tuple[GroupStanding, ...]   # official order

def build_groups(matches: list[Match]) -> dict[str, Group]:
    """Map group name -> Group. Teams ordered by first appearance across the
    group's Group-Stage matches in match_number order; all stats zero."""

def group_for_team(groups: dict[str, Group], team: str) -> Group | None:
    """The Group a team belongs to, or None if unknown."""
```

`build_groups` filters `m.stage == "Group Stage"` (same predicate `flows.py` uses),
buckets by `m.group`, and for each bucket walks matches in `match_number` order
collecting `home` then `away` on first sight to fix the order.

## Component: Panel (`src/components/group_table.py`)

```python
from src.components.team_carousel import display_name  # "and" -> "&"; "Korea Republic" -> "South Korea"

COL_DEFS = [...]  # #, Team, MP, W, D, L, GD, Pts (Pts bold via cellStyle)

def group_rows(group: Group, asset_url) -> list[dict]:
    """rowData dicts: rank 1..n, team (display name), flag (asset url), mp/w/d/l/gd/pts.
    `flag` uses the RAW team name (country_logos/<raw>.svg); `team` uses display_name."""

def build_group_panel(group: Group | None, asset_url) -> dmc.Box:
    """Panel body (className='group-panel__body'): DMC header ('Table' + 'World Cup' +
    group-name id='group-table-title' + decorative chevron) -> dag.AgGrid(id='group-grid')
    -> empty flex:1 Box id='group-extra'. The visibility wrapper (id='group-panel') is
    added in layout.py, mirroring the existing carousel-wrapper pattern."""
```

- **Grid:** `dag.AgGrid(id="group-grid", columnDefs=COL_DEFS, rowData=group_rows(...),
  columnSize="sizeToFit", className="ag-theme-quartz-dark group-grid",
  dashGridOptions={"suppressCellFocus": True, "rowHeight": 38, "headerHeight": 34,
  "domLayout": "autoHeight"})`.
- **Team column** uses `cellRenderer: "TeamCell"`; its row dict provides `team` (name)
  and `flag` (url).
- `group is None` → grid with empty `rowData` and a neutral "—" group label (defensive;
  every carousel team has a group, so this is a guard, not a normal path).

### Cell renderer (`assets/dashAgGridComponentFunctions.js`)

dash-ag-grid auto-loads this file. Defines:

```js
var dagfuncs = (window.dashAgGridComponentFunctions = window.dashAgGridComponentFunctions || {});
dagfuncs.TeamCell = function (props) {
    return React.createElement(
        "div", { className: "team-cell" },
        React.createElement("img", { src: props.data.flag, className: "team-cell__flag", alt: "" }),
        React.createElement("span", { className: "team-cell__name" }, props.value)
    );
};
```

(Team column `field: "team"`, so `props.value` is the display name; `props.data.flag`
is the SVG url.) Not unit-tested (browser code); verified via Playwright.

## Layout & Callbacks

### `layout.py`

```python
main = dmc.AppShellMain(
    dmc.Box(
        [
            html.Div(build_map(venues), id="map-container"),
            dmc.Box(group_panel, id="group-panel", style={"display": "none"}),
        ],
        className="main-split",
    )
)
```

`build_layout` gains a `group_panel=None` parameter (built in `app.py` from `GROUPS`
and `app.get_asset_url`). Add `dcc.Store(id="map-resize-tick")` to the provider children.

### `app.py`

Pure helper (testable without callbacks):

```python
def group_panel_payload(index: int | None) -> tuple[str, list[dict]]:
    """(group_name, rowData) for the centred team at `index`."""
    team = center_team(TEAM_NAMES, index or 0)
    group = group_for_team(GROUPS, team)
    name = group.name if group else "—"
    rows = group_rows(group, app.get_asset_url) if group else []
    return name, rows
```

Callbacks:

1. **Panel content (server):**
   `Input("carousel-index", "data")` →
   `Output("group-grid", "rowData")`, `Output("group-table-title", "children")`.
   Body: `return rowData, name` via `group_panel_payload`.
   (`group-table-title` is the group-name `dmc.Text` in the header.)

2. **Panel visibility + map resize (clientside):**
   `Input("mode-toggle", "checked")` → `Output("group-panel", "style")`.
   ```js
   (checked) => {
       setTimeout(() => window.dispatchEvent(new Event('resize')), 350);
       return checked ? {display: 'flex'} : {display: 'none'};
   }
   ```
   Runs on load too, so a persisted Team mode shows the panel from first render
   (mirrors the existing `toggle_filter_pin` pattern).

3. **Grid theme (clientside):**
   `Input("color-scheme-toggle", "checked")` → `Output("group-grid", "className")`.
   ```js
   (checked) => (checked ? "ag-theme-quartz-dark group-grid"
                         : "ag-theme-quartz group-grid")
   ```

## Styling (`styles.css`)

- `.main-split { display:flex; height:100%; width:100%; }`
- `#map-container { flex:1 1 0; min-width:0; height:100%; }`
- `.group-panel { flex:0 0 34%; height:100%; display:flex; flex-direction:column;
  overflow:hidden; padding:… ; transition:flex-basis .3s ease, width .3s ease; }`
- `.group-grid { --ag-background-color:transparent; --ag-odd-row-background-color:transparent;
  --ag-borders:none; font-size:13px; }` (compact, borderless, blends with panel).
- `.team-cell { display:flex; align-items:center; gap:8px; }`
  `.team-cell__flag { width:20px; height:14px; object-fit:contain; border-radius:2px; }`
- **Mobile** `@media (max-width: 768px)`: `.main-split{flex-direction:column}`,
  `#map-container{height:55vh}`, `.group-panel{flex:1 1 auto; width:100%; overflow:auto}`.
  No horizontal overflow; grid scrolls internally.

## Testing (TDD)

Pure functions first (`pytest tests/ -v`, conda base env):

1. `GroupStanding` defaults — all stats `0`.
2. `build_groups` — returns 12 groups, each 4 teams; all stats `0`.
3. `build_groups` order — Group A standings `team` order ==
   `["Mexico", "South Africa", "Korea Republic", "Czechia"]`.
4. `group_for_team` — known team returns the right group; unknown team returns `None`.
5. `display_name` — "Bosnia and Herzegovina" → "Bosnia & Herzegovina";
   "Korea Republic" → "South Korea"; unmapped name returns unchanged.
6. `group_rows` — ranks `1..4`; `team` applies `display_name`; flag url uses the
   **raw** team name (`asset_url("country_logos/Korea Republic.svg")` even though the
   display name is "South Korea"); numeric fields all `0`.
7. `build_group_panel` — tree contains ids `group-grid`, `group-table-title`,
   `group-extra`; grid `columnDefs` include a `team` column with
   `cellRenderer == "TeamCell"`.
8. `build_group_panel(None, ...)` — renders without error; empty `rowData`; label "—".
9. `group_panel_payload(index)` — for an index whose centred team is in Group A,
   returns `("Group A", rows)` with 4 rows in official order.
10. `build_layout(...)` — tree contains className `main-split` and id `group-panel`
    (the visibility wrapper); `map-container` still present.

Clientside callbacks (visibility/resize, grid theme) and the `TeamCell` renderer are
verified via Playwright (panel appears in Team mode, map re-tiles after resize, theme
follows the switch), not unit tests.

## Non-Goals / Preserved Behavior

- Time mode is byte-for-byte today's experience (full-width map, calendar, filter pin
  & drawer, leaderboard, theme switch, carousel hidden).
- No results/standings logic — every stat is `0` until the future API lands.
- No new Python dependency (dash-ag-grid already installed).
- Map bounds, tiles, stadium-click drawer, carousel navigation unchanged.
- The chevron and the `group-extra` area are placeholders with no behaviour yet.
