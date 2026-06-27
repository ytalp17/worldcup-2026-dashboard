# Goal-mouth map — Design Spec

> Per-team aggregate visualization of where a team's shots finished, added as a
> new bento box in the per-team view. Built on Highlightly match-detail shot
> data (`goalTarget` zones), NOT pitch x/y coordinates — so it is a **placement**
> map, deliberately not called a "shot map".

**Date:** 2026-06-28
**Status:** Approved (design); pending spec review → implementation plan.

---

## 1. Goal & scope

Add a **Goal-mouth map** bento box to the per-team view. It shows, for the
team currently selected in the header carousel, an aggregate picture of where
that team's shots finished (on the goal grid, in the near-miss margins, or
off-target), cumulatively across the matches played so far.

- Display title: **Goal-mouth map**; subtitle "where each team's shots finished".
- Never labelled "shot map" (the API gives goal-target zones, not pitch
  coordinates).
- One team at a time, driven by the existing carousel — **no per-box team
  dropdown** (every other per-team card already follows the carousel; a second
  team control would be redundant and incoherent).
- Built with Dash + Plotly + dash-mantine-components only. No new charting
  library.

### Out of scope (TODO hooks only — do not build)
- Pitch-coordinate shot map (API has no x/y).
- Per-shot xG / xGOT weighting (future, via box-score `expectedGoalsOnTarget`).
- Per-match (non-aggregate) version.

---

## 2. Global constraints (binding)

- **UI components:** dash-mantine-components only. Verify each DMC component's
  current API via the context7 MCP before use (`Drawer`, `SegmentedControl`,
  `Stack`, `Group`, `Text`, `ScrollArea`).
- **Data wrangling:** pandas where aggregation benefits; plain dataclasses for
  records.
- **OOP:** dataclasses for data entities (`ShotRecord`); service methods on the
  existing `LiveDataService`.
- **TDD:** write failing tests first, then implement. Run `pytest tests/ -v`.
- **Design:** elegant/clean; dark+light mode safe (no hardcoded black text);
  full-screen, no scrollbars; responsive/mobile with **no horizontal overflow**.
- **Data files:** caches go in `assets/data/` (gitignored), mirroring the
  existing live stores.
- **Design coherence:** reuse existing patterns — `.bento-card`,
  `.bento-card__header`, the leaders-card header control pattern, the
  stadium/tournament drawer pattern, and `analysis/theme.py` for figure theming.
- **Group-stage switch parity:** aggregation honors a `group_only` flag the same
  way `tournament_*_leaders` already do (group vs all).

---

## 3. Data contract (confirmed by probe)

Source: Highlightly match-detail endpoint `client.match(match_id)`, which
carries `homeTeam.shots[]` and `awayTeam.shots[]`. Each shot has exactly four
fields:

```json
{ "playerName": "Kieron Bowie", "time": "15'", "outcome": "Blocked", "goalTarget": "Low Centre" }
```

- `time` is a string: `"15'"` or `"45+1"` (stoppage). Parse to a sortable
  `(base, extra)` minute; never assume integer.
- `goalTarget` is `null` for shots with no on-goal trajectory.

Confirmed vocabulary (536-shot probe over 20 WC2026 group matches):

- **`outcome`** is a clean 5-value enum: `Missed`, `Blocked`, `Saved`, `Goal`,
  `Post` (`Post` = woodwork).
- **`goalTarget`** families:
  1. **On-target grid — 2×3, NOT 3×3.** Vertical band is only {Low, High}
     (no middle row). Six cells: `High Left`, `High Centre`, `High Right`,
     `Low Left`, `Low Centre`, `Low Right`.
  2. **Near-miss margins (outside the frame).** Only four occur — note the
     inconsistent spacing and the compound: `Close High`, `CloseLeft`
     (no space), `Close Right`, `Close Right And High` (compound).
  3. **`null` → off-target.** Every null shot was `Missed` or `Post`. No
     directional info — shown as a separate tally, never placed on the frame.

`Post` is an `outcome`, not a `goalTarget`; a post shot can have
`goalTarget: null`. Render woodwork by color.

**Today's data reality:** as of 2026-06-28 (knockouts beginning), the store may
hold few finished matches for some teams. The box must render an empty state
("No shots yet") cleanly when a team has no stored shots.

---

## 4. Zone model — explicit lookup, never string-split

A single explicit mapping is the only place `goalTarget` strings are
interpreted. Defensive against the `CloseLeft` spacing, the
`Close Right And High` compound, and any value a wider sample surfaces.

```python
# src/data/live/goal_mouth_zones.py
ON_TARGET = ["high_left", "high_centre", "high_right",
             "low_left", "low_centre", "low_right"]
MARGINS   = ["close_high", "close_left", "close_right", "close_right_high"]

ZONE_MAP = {
    "High Left": "high_left",   "High Centre": "high_centre", "High Right": "high_right",
    "Low Left":  "low_left",    "Low Centre":  "low_centre",  "Low Right":  "low_right",
    "Close High": "close_high", "CloseLeft": "close_left",
    "Close Right": "close_right","Close Right And High": "close_right_high",
}

def classify_target(goal_target: str | None) -> str:
    """None -> 'off_target'; known string -> region id; unknown -> 'other'."""
    if goal_target is None:
        return "off_target"
    return ZONE_MAP.get(goal_target, "other")
```

- `off_target` and `other` are **buckets**, not frame regions.
- `other` is logged (so a new string is noticed) but **never silently dropped**.
- Reconciliation invariant: on-target + near-miss + off-target + other = total
  shots. Tested.

---

## 5. Data layer (mirrors existing live stores)

Follows `team_stats_store.py` / `update_team_stats` conventions exactly.

### 5.1 `src/data/live/shots.py`
```python
@dataclass(frozen=True)
class ShotRecord:
    match_id: int
    team: str
    player: str
    time: str          # raw "15'" / "45+1"
    outcome: str       # one of the 5-value enum (str as received)
    goal_target: str | None

def parse_shots(match_id: int, detail) -> list[ShotRecord]:
    """Read homeTeam.shots[]/awayTeam.shots[] from a match-detail object
    (detail may be a 1-element list or a dict). Defensive: skip non-dict
    shots; team name from the side's team object."""
```

### 5.2 `src/data/live/shots_store.py`
- Gitignored CSV: `assets/data/live_shots.csv`.
- `FIELDS = ["match_id","team","state","stage","player","time","outcome","goal_target"]`.
- `load(path) -> dict[int, list[ShotRecord]]`, `stored_match_states(path)`,
  `upsert(path, match_id, state, rows, stage="group")` — same atomic
  replace-by-match-id pattern as `team_stats_store`.

### 5.3 `LiveDataService.update_shot_stats(matches, now)`
Mirrors `update_team_stats`: skip finished-and-already-stored; for finished-new
or live, fetch `self._client.match(mid)`, `parse_shots`, compute
`stage = classify_stage(m.get("kickoff"), self._knockout_start)`, and
`shots_store.upsert(...)`. Per-match try/except logs and continues.
Constructor gains a `shots_store=None` path stored as `self._shots_store`
(wired to `assets/data/live_shots.csv` in `app.py`).

Wire into the snapshot updater in `app.py` next to
`update_player_stats`/`update_team_stats` (both the sync warm-up at ~line 1097
and the async path at ~line 1120).

### 5.4 `LiveDataService.team_goal_mouth(team, group_only=False) -> dict`
Loads the store, filters to `canonical_team(team)`, skips
`group_only and r.stage != "group"`, classifies each shot via
`classify_target`, and returns:

```python
{
  "zones": {                       # all 6 grid cells + only the present margins
     "low_centre": {
        "count": 151,
        "outcomes": {"Goal": 28, "Saved": 60, "Blocked": 63, ...},
        "shooters": [{"time": "15'", "player": "K. Bowie", "outcome": "Blocked"}, ...],
     }, ...
  },
  "off_target": {"count": 12, "outcomes": {"Missed": 9, "Post": 3}},
  "other":      {"count": 0,  "outcomes": {}},
  "totals": {"on_target": N, "near_miss": N, "woodwork": N,
             "off_target": N, "total": N},
}
```

- All six grid cells always present (zero-count cells render empty/faint).
- Margins present only when count > 0 (so empty bottom / top-left never draw).
- `woodwork` total = count of shots whose `outcome == "Post"` (across buckets).
- Shooters sorted by parsed time ascending.

---

## 6. Component — `src/components/goal_mouth.py`

A `dcc.Graph` (config `{displayModeBar: False, responsive: True}`) in a
`.bento-card--goalmouth` card whose header matches `.bento-card__header`.

### 6.1 Frame & regions
- Goal frame wider than tall (real proportions) inside a slightly larger bounds.
- **Inside the posts:** 2×3 grid (cols Left/Centre/Right, rows High top / Low
  bottom).
- **Outer band:** top = `close_high`, left = `close_left`, right = `close_right`,
  top-right corner = `close_right_high` — **drawn only where count > 0**. No
  bottom margin, no top-left corner ever.
- **Posts/crossbar** drawn as the divider between inside and outer band.
- **Beside the frame:** compact readout — off-target count + totals (on target /
  near miss / woodwork / total). pandas/plain builders, unit-tested.

### 6.2 Fill modes (SegmentedControl in the card header)
- **Volume intensity (default):** each on-target cell shaded by shot count
  (opacity ramp on a single hue).
- **Dominant outcome (toggle):** each cell colored by its most common outcome.

### 6.3 Color — 5-value outcome enum (consistent everywhere)
`Goal #1D9E75` · `Saved #378ADD` · `Blocked #888780` ·
near-miss/Close family `#EF9F27` · `Post`/woodwork `#D85A30`.
Resolved through `analysis/theme.py` so paper/plot backgrounds are transparent
and text color follows dark/light. Never rely on color alone — every hover and
the drawer list pair color with the text label.

### 6.4 Hover (zone gist)
Per zone (grid cell or margin): zone name, total shots, outcome breakdown,
single headline detail (top shooter), and "click to see all {n}" appended when
count > 6. Hover never lists every shot. Built with explicit `hovertemplate` +
`customdata` — never raw Plotly defaults.

### 6.5 Copy & accessibility
- Title "Goal-mouth map"; subtitle "where each team's shots finished".
- One-line caption: "inside the posts = on target · outer band = near miss".
- Honest-limitation note in-UI: placement map (where shots finished), not a
  pitch-location map, because the API gives goal-target zones, not coordinates.
- Descriptive `aria` summary on the graph container.

---

## 7. Click → app-level LEFT drawer (full shot list)

A `dmc.Drawer position="left"` (sibling of the stadium drawer; reuse the frosted
class pattern), driven by a `dcc.Store(id="goal-mouth-zone")` holding the open
zone id (or `None`).

- Click a zone → set the store → drawer opens with that zone's contents.
- **Self-contained header:** repeats the zone summary (name, total, outcome
  breakdown).
- **Scrollable list:** one row per shot, sorted by `time` ascending —
  `minute · shooter · outcome` (e.g. "15' — K. Bowie — Blocked"), outcome shown
  in its enum color (`dmc.ScrollArea`).
- Clicking another zone replaces the contents; clicking the same zone again or
  the close control dismisses (clears the store).
- Drawer is app-level (not inside the tile), so it is never cramped by the tile
  and never covers the carousel/team controls.

---

## 8. Layout integration

Per-team grid is a packed 4×3. Narrow the group table 2 cols → 1; the freed cell
takes the new box.

`assets/styles.css` `.main-split--team`:
```css
grid-template-columns: 1.0fr 1.0fr 0.85fr 1.2fr;   /* was 1.3 0.85 0.85 1.25 */
grid-template-areas:
    "kpi      kpi        kpi        kpi"
    "table    goalmouth  formation  squad"   /* table=group card, now 1 col */
    "leaders  map        map        squad";
```
Keep the existing `table` area token (the group card already uses
`.bento-card--table`) to minimize churn — only its column span changes from 2→1.
Add a new `goalmouth` area in the freed cell and
`.main-split--team .bento-card--goalmouth { grid-area: goalmouth; }`. The visible
result: group table narrower, new box immediately to its right.

Mobile (`@media max-width:768px`): insert `goalmouth` into the single-column
stack right after `table`, with a sensible `min-height` (≈ the formation card's),
preserving no-horizontal-overflow.

`src/components/layout.py`: add the `goal_mouth_panel` to `build_layout`'s
children with class `bento-card bento-card--goalmouth`, and add the left drawer +
its `dcc.Store` to the layout tree.

`app.py`: callback firing on `carousel-index` (+ the group-stage switch + live
store) builds the figure & readout via `team_goal_mouth(...)`; a second callback
maps zone clicks (`clickData`) + close into `goal-mouth-zone`; a third renders
the drawer body from the open zone.

---

## 9. Probe (verification only)

Widen `scratchpad/probe_shots.py` to additionally emit, per team:
- **zone × outcome** counts, and
- **zone × shooter** lists.
Confirms the runtime aggregation against live data. Runtime aggregation lives in
`service.py`, never imported from the probe.

---

## 10. Testing (TDD)

Unit tests first, for the pure functions:
- `classify_target` — every known string (incl. `CloseLeft`,
  `Close Right And High`) → correct region; `None` → `off_target`; unknown →
  `other`.
- `parse_shots` — 1-element-list and dict detail; both sides; skips malformed;
  null `goalTarget` preserved.
- `team_goal_mouth` — aggregation correctness; `group_only` filtering;
  reconciliation invariant (on-target + near-miss + off-target + other = total);
  empty store → empty-but-valid structure; margins absent when zero; all six
  cells always present.
- time parsing/sort — `"45+1"` sorts after `"45'"`, before `"46'"`.
- figure-data / readout / hover-text builders — values and "click to see all n"
  threshold.
- component construction — card has `.bento-card__header`, the header
  SegmentedControl, and the graph; left drawer + store present in the layout.

Then implement to green. Browser/e2e (Framework 3.11 python w/ Playwright,
`channel="chrome"`): per-team view shows the box, group table is narrower, no
horizontal overflow desktop + 390px mobile, dark+light both render, clicking a
zone opens the left drawer with the shot list, fill-mode toggle switches.

---

## 11. Acceptance checks

- [ ] Title is "Goal-mouth map"; never "shot map".
- [ ] On-target grid is 2×3 ({High,Low} × {Left,Centre,Right}); no middle row.
- [ ] Near-miss margins render only for the four present families; no empty
      bottom or top-left.
- [ ] `goalTarget` parsed by explicit lookup, not string-split; `CloseLeft` and
      `Close Right And High` map correctly; unknown → visible `other`, never
      dropped.
- [ ] null `goalTarget` → off-target tally beside the diagram, not a zone.
- [ ] Color uses the 5-value outcome enum consistently; Post = woodwork color.
- [ ] Volume-intensity default; dominant-outcome toggle in the header.
- [ ] Box follows the carousel team; only one team's frame shown at a time; no
      per-box team dropdown.
- [ ] Hover shows zone summary (total + breakdown + top shooter); "click to see
      all n" when >6.
- [ ] Clicking a zone opens an app-level LEFT drawer with the full shot list
      (minute · shooter · outcome), sorted by time, scrollable, self-contained
      header; replaces on new zone; dismisses on close/re-click.
- [ ] Counts reconcile: on-target + near-miss + off-target + other = total.
- [ ] Probe extended to emit zone×outcome and zone×shooter cross-tabs.
- [ ] Group table is visibly narrower; new box sits to its right; no horizontal
      overflow desktop or mobile; renders in dark AND light mode; DMC-only
      controls.
- [ ] Empty/no-shots state renders cleanly.
