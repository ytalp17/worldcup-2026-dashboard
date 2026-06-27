# Detail Improvements — Design

> Date: 2026-06-27
> Status: Approved (brainstorming). Small, independent UI polish tasks.
> Source: "FIFA World Cup Dashboard — Detail Improvements Spec".

Three independent pieces: (1) info-box header tweaks, (2) group-table fit,
(3) derived qualification/elimination markers on the group table.

---

## Decisions locked
- **Info boxes are team/squad-level**, not single-player. Tooltip copy is phrased
  at squad/team level. Existing "Avg age"/"Avg height" labels are kept (accurate);
  only "Foot" → "Foot Preference" is renamed.
- **Group table fit:** the grid fills the card with no scroll for a 4-row table
  (scroll only if a group ever has >4 rows).
- **Qualification status is derived** (the parsed standings carry no qualified/
  eliminated flag) and rendered as a subtle **inset left-border accent** per row
  (green = advancing, red = eliminated).

---

## 1. Info boxes (`src/components/team_kpis.py`)

- Rename the foot box header "Foot" → **"Foot Preference"** (line ~129).
- Reorder the 7 cards to: **Value · Avg age · Avg height · Foot Preference ·
  FIFA rank · Federation · Manager**.
- Add a header tooltip to every box. Wrap each card's `_head()` element in
  `dmc.Tooltip(label=..., position="top", withArrow=True, ...)`, matching the
  existing pattern in `src/components/map_view.py`. Add a `tip` parameter to
  `_head()` / `stat_card()`.
- Tooltip copy:
  | Box | Tooltip |
  |---|---|
  | Value | Estimated total market value of the squad. |
  | Avg age | Average age of the squad. |
  | Avg height | Average height of the squad. |
  | Foot Preference | Share of the squad that is left- vs right-footed. |
  | FIFA rank | The team's current FIFA world ranking. |
  | Federation | The continental football federation the team belongs to. |
  | Manager | The team's current head coach. |

## 2. Group-table fit (`src/components/group_table.py` + `assets/styles.css`)

- Change AgGrid `_GRID_OPTIONS` `domLayout` from `"autoHeight"` to `"normal"` so
  the grid respects its parent height.
- CSS: `.group-grid` becomes `flex: 1 1 auto; min-height: 0;` so it fills the card
  body; remove the leftover `#group-extra` spacer usage if present.
- Net: a 4-row group table fills the card cleanly with no scrollbar; the grid
  scrolls internally only if rows ever exceed the visible area.

## 3. Qualification markers

### 3a. Derivation — new pure module `src/data/qualification.py`
- `qualification_status(standings: dict[str, list[dict]]) -> dict[str, dict[str, str]]`
  returning `{group_name: {team: "qualified"|"eliminated"|""}}`, computed from the
  full live-standings dict (all groups keyed by name; each value a list of row
  dicts with `team`, `points`, `goal_diff`, `goals_for`).
- Rules (WC2026: 12 groups of 4 → 32 advance):
  1. Within each group, order teams by `points` → `goal_diff` → `goals_for`
     (descending). Positions 1–2 → **qualified**; position 4 → **eliminated**;
     position 3 → candidate.
  2. Collect every group's 3rd-placed team; rank them across groups by the same
     keys; the **best 8 → qualified**, the rest → **eliminated**.
  3. Fallback: if fewer than 12 groups have data, still take the best 8 (or all,
     if fewer than 8 exist) of whatever 3rd-placed teams are present.
- Documented approximation: FIFA's later tiebreakers (head-to-head, fair-play,
  drawing of lots) are not derivable from standings alone; points → GD → GF is used.
- Pure and offline-testable; no API/store access.

### 3b. Row data (`group_table.py`)
- `live_group_rows(...)` accepts a per-group `status` map (`{team: status}`) and
  attaches a `status` key to each row dict. Static `group_rows(...)` sets
  `status=""` (no markers pre-tournament).
- Add `rowClassRules` to the grid (in `dashGridOptions`):
  `{"group-row--q": "params.data.status === 'qualified'",
    "group-row--e": "params.data.status === 'eliminated'"}`.

### 3c. Styling (`assets/styles.css`)
- `.ag-row.group-row--q { box-shadow: inset 3px 0 0 0 <green>; }`
- `.ag-row.group-row--e { box-shadow: inset 3px 0 0 0 <red>; }`
- Use theme-coherent colors (e.g. green `#1D9E75`, red `#e03131` / theme red);
  no layout shift (inset box-shadow, not border). Honor light/dark.

### 3d. Wiring (`app.py`)
- `group_panel_payload(index, live_standings)` computes
  `qualification_status(live_standings)` once, looks up the centered team's group,
  and passes that group's `{team: status}` map into `live_group_rows`.
- Team-name canonicalization: reuse the existing `official_team` / resolve path so
  the status map keys match the row team names.

---

## 4. Testing (TDD)
- `tests/test_qualification.py`: top-2 qualify; 4th eliminated; best-8 third-placed
  selection across 12 groups; tiebreaker ordering (points → GD → GF); partial-data
  fallback (<12 groups, <8 thirds).
- `tests/test_team_kpis.py` (extend): card order, "Foot Preference" label, a
  `dmc.Tooltip` on every header with non-empty label.
- `tests/test_group_table.py` (extend): rows include `status`; `rowClassRules`
  present in options; `domLayout == "normal"`.

## 5. Out of scope
- No API/model change to add a real qualified flag (derive instead).
- No new info-box data fields; no architectural changes.
