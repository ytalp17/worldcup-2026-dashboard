# Deep Analysis Panel — Design

> Date: 2026-06-25
> Status: Approved (brainstorming). Next step: implementation plan (writing-plans).
> Source spec: `DEEP_ANALYSIS_PANEL_SPEC (2).md` (build spec), reconciled with the
> existing WC2026 Dash codebase.

A horizontally-navigable carousel of 10 Plotly chart views that compares the 4
teams of a World Cup group, replacing the Leaflet map tile **in Team mode only**.
Every chart reflects each team's cumulative aggregate across all FINISHED matches
played so far, and updates as new results arrive.

---

## 1. Locked decisions (from brainstorming)

| Decision | Choice | Rationale |
|---|---|---|
| **Placement** | Team-mode map tile only | Map stays the heart of the app; Time mode keeps the full-screen Leaflet map untouched. Panel replaces the map's content in Team mode. |
| **Data store** | Reuse existing `team_stats_store` | The store already implements the spec's append-only / atomic / idempotent-by-`(match_id, team)` design. New work is the accessor seam only — no new storage layer. |
| **Matchday model** | Each team's Nth match, chronological | Robust to staggered kickoffs; every team's race frames line up 1, 2, 3. |
| **Match state** | FINISHED matches only enter aggregates | Stable charts; a live match appears once final. Matches the spec's "completed matches" phrasing. |
| **Group shown** | Group of the carousel-selected team | Reuses the existing team selector (`carousel-index`); no separate group picker. |

---

## 2. Why reuse the existing store

The build spec's §2A ("append-only, no database") describes infrastructure that
**already exists** in the codebase:

- [src/data/live/team_stats_store.py](../../../src/data/live/team_stats_store.py)
  persists **one row per `(match_id, team)`** — that team's stats from that single
  match. `upsert()` writes a `.tmp` file then `os.replace()`s it (atomic), and
  re-fetching a match replaces only that match's rows (idempotent by match key,
  no double-counting). Single writer = `LiveDataService.update_team_stats`.
- [src/data/live/team_match_stats.py](../../../src/data/live/team_match_stats.py)
  already defines the **exact `_DISPLAY_TO_KEY`** dictionary from the spec's §2
  data contract (the 24 stat keys + discipline keys).

The spec *prefers* Parquet "because CSV loses types" — but this store casts every
value to `float` on read, so that concern does not apply. We keep CSV and reuse
the store as-is. The genuinely new work is the **accessor seam** and the
**match → group / matchday / canonical-team resolution**.

---

## 3. Module layout

```
src/data/analysis/
  accessors.py     # THE SEAM — charts call only these two functions:
                   #   get_group_aggregates(group_id) -> list[team record]
                   #   get_matchday_history(group_id, metric) -> {team: [cum md1, md2, ...]}
  aggregate.py     # pure rollup: sum counts/xg/xa, mean possession; per-90; field-relative 0-100
  matchday.py      # match_id -> (group, team's-Nth-match) from static MATCHES/GROUPS

src/components/analysis/
  panel.py         # build_analysis_panel() -> the bento card: carousel shell, edge arrows,
                   #   dots/position indicator, dcc.Graph, per-view controls
  views.py         # VIEWS config (ordered list of 10) + pure figure-builder fns keyed by view id
  theme.py         # team palette, segment colors, plotly_layout(theme) light/dark helper
```

**Seam rule:** chart/view code calls **only** `accessors.py`. `aggregate.py` and
`matchday.py` are the implementation behind the seam. Swapping to a DB later means
reimplementing the two accessor functions only — no view, layout, or callback
change. (Leave a TODO hook noting this.)

---

## 4. Data contract & sources

Each team record returned by `get_group_aggregates` is one team's cumulative
aggregate keyed by the internal metric keys (the 24 in `_DISPLAY_TO_KEY`), plus:

| Field | Source |
|---|---|
| 24 stat keys (xg, xa, possession, shots_*, passes_*, tackles_*, …) | `team_stats_store.load()`, filtered to the team's FINISHED matches; **sum** for counts/xg/xa, **mean** for `possession`. |
| `goals`, `goals_conceded` | Match **results** (live snapshot `matches` scores; fallback to standings GD). Not in the stat store. |
| `assists` | Sum of the team's players' assists from `player_store`. |
| `points` | Live `standings`. |
| `matches_played` | Count of the team's FINISHED matches in the store. |
| `team`, `group` | Static `GROUPS` membership. |

Raw live team names are mapped to official names via the existing
`canonical_team()` ([src/data/live/reconcile.py](../../../src/data/live/reconcile.py)).

`get_matchday_history(group_id, metric)` walks each team's FINISHED matches in
chronological order, accumulating the selected RACE metric per matchday. Metrics
and their sources:

| RACE metric | Source |
|---|---|
| Collected points | results/standings (3 win / 1 draw, accumulated) |
| Goals | match results |
| Assists | player_store |
| Total cards | stat store (`yellow + red`, simple count) |
| Goals conceded | match results (opponent goals); lower is better |

If `matches_played` is missing, fall back to raw totals and log a warning (spec §2).

---

## 5. Normalization (radars only — `aggregate.py`)

1. **Per-90 first.** When `matches_played` is present, convert `count`-type metrics
   to per-match (≈ per-90) before scaling, so a team that played more matches does
   not dominate count axes. `rate` metrics (possession) and already-normalized
   metrics (xg, xa) stay per-match. Each metric is tagged `count` or `rate` in the
   view config.
2. **Field-relative scaling.** Per axis, `scaled = value / max(value across the 4
   teams) * 100`; the group's strongest team hits 100. Guard divide-by-zero
   (max 0 → all 0). Recompute per group.
3. Round derived numbers to kill float artifacts.

The dumbbell (view 5) uses **raw** goals/xG — no scaling.

---

## 6. The 10 views (single ordered config in `views.py`)

View 1 is the default on load. All 4 group teams appear on every view. One config
list drives the carousel; adding/reordering a view touches only this list.

| # | id | type | metrics / notes |
|---|----|----|----|
| 1 | ATTACKING_THREAT | radar | xg, xa, big_chances, shots_in_box, key_passes |
| 2 | BUILD_UP | radar | possession, passes_succ, passes_final_third, key_passes, dribbles_succ |
| 3 | DEFENSIVE_WORK | radar | tackles_succ, interceptions, clearances, aerials_won, gk_saves · caveat note |
| 4 | STYLE_FINGERPRINT | radar | possession, crosses, long_passes, dribbles, aerials (raw attempts on purpose) |
| 5 | FINISHING | dumbbell | goals vs xg (raw), sorted by (goals−xg); connector green/orange; small-sample caveat |
| 6 | RACE | bar race | metric dropdown + replay; animated md1→latest |
| 7 | SHOT_FUNNEL | funnel | 2×2 small-multiples: shots → on target → goals, step conversion % |
| 8 | QUALITY_VS_CONV | quadrant | xG/shot (x) vs conversion % (y); median crosshair + quadrant labels |
| 9 | HOW_THEY_DEFEND | stacked bar | tackles_succ+interceptions+clearances+aerials_won; fixed seg colors; per-90; caveat |
| 10 | VOLUME_VS_PENETR | bubble | total passes (x) vs final-third passes (y); size = pass accuracy % |

### Shared radar rules (preserve — these are the point)
- 5 axes each, never more than 6.
- Never put a raw count and its `*_succ` counterpart on the same radar.
- `DEFENSIVE_WORK`: high values often mean a team played *without* the ball — a big
  shape ≠ better defense. Show a one-line caveat under this view.
- `STYLE_FINGERPRINT` uses raw attempt counts on purpose — it characterizes *how* a
  team plays, not how well.
- Discipline metrics (yellow, red, fouls, offsides) are excluded from all views
  except as a RACE metric.

### Per-view chart specs
Radars (`go.Scatterpolar`): one trace/team, `fill='toself'` ~15% opacity; radial
range fixed [0,100], tick labels hidden, rings + spokes shown; angular labels =
display names; hover shows the **raw** (pre-normalization, per-match if per-90)
value + metric name, never the 0–100 number.

Dumbbell (`go.Scatter`): one row/team sorted desc by `(goals − xg)`; xG marker grey
`#888780`, goals marker blue `#185FA5`, connector green `#1D9E75` if `goals ≥ xg`
else orange `#D85A30`; X = goals, Y = team names; per-marker hover; small-sample
caveat for teams with very few shots/matches.

Bar race (`go.Bar`, animated): horizontal bars, length = cumulative metric to the
current matchday frame; bars re-sort each frame (leader on top); value labels on
bar ends; matchday label updates per frame; auto-play once on activation / metric
change, **stop at last frame**, Replay button, no loop; goals-conceded shows a
"lower is better" direction caveat.

Shot funnel (`go.Funnel`): 2×2 small-multiples, one funnel/team — shots → on target
→ goals (`shots_total = shots_on + shots_off + shots_blocked` or stored total);
annotate each stage with count + step conversion %; per-stage hover shows % of
previous stage and % of all shots; light→dark shade ramp of the team's hue.

Chance quality vs conversion (`go.Scatter` quadrant): one point/team, X = xG/shot,
Y = conversion % (goals ÷ shots); median/group-average crosshair into four
quadrants with faint labels (clinical / lucky / wasteful / toothless); team name
annotated beside each marker; hover = xG/shot, conversion %, raw goals & shots.

How they defend (stacked `go.Bar`): one stacked bar/team — tackles_succ,
interceptions, clearances, aerials_won; fixed segment colors (tackles `#1D9E75`,
interceptions `#378ADD`, clearances `#EF9F27`, aerials won `#D85A30`); per-90
normalized; hover shows count, per-90 value, and share of the team's total
defensive actions; misleading-volume caveat.

Volume vs penetration (bubble `go.Scatter`): one bubble/team, X = total passes,
Y = passes into final third, size = pass accuracy % (`passes_succ ÷ passes_total`);
axis ranges padded ~10% so bubbles don't clip; team name annotated; hover shows
final-third share.

---

## 7. Carousel navigation & layout fit

- One `dcc.Graph` visible at a time inside the `map` tile.
- Arrows on the tile's **left/right edges** with `aria-label="Previous chart"` /
  `"Next chart"`; **wrap-around** (right from last → first, left from first → last).
- Current view title + one-line "what this shows" caption above; muted caveat below
  where a chart can mislead; "n / 10" + dots position indicator.
- View-specific controls (RACE metric dropdown, Replay) live inside their view and
  render only when that view is active.
- Figure-building is pure functions keyed by view config, so adding a view needs no
  callback change.

**Fit constraint (CLAUDE.md: full-screen, no scrollbars, fits viewport):** the
Team-mode map tile is a moderate landscape cell (`leaders | map map | squad` row).
Graph is `autosize=True` and fills the tile; caption/caveat/controls are compact
single lines; a slim custom 4-team legend strip (consistent across all views)
replaces Plotly's default legend; the modebar is trimmed to the minimum.

---

## 8. Integration with the existing app

- **Layout** ([src/components/layout.py](../../../src/components/layout.py)): the
  map tile (`bento-card--map`, grid area `map`) renders the **analysis panel** in
  Team mode and the **Leaflet map** in Time mode. The map stays mounted; its
  existing callbacks (pulse/live/flow layers, tile theme swap) are untouched — in
  Team mode the map simply isn't shown, as today. Mechanism: a swap driven by the
  existing `mode-toggle` signal (reusing the `main-split--team` class path).
- **Callbacks** ([app.py](../../../app.py)):
  - `update_analysis_panel(view_index, race_metric, carousel_index, live_store)`
    → `dcc.Graph` figure + view title + caption + dots.
  - Arrow callbacks advancing/retreating `analysis-view-index` (wrap-around).
  - RACE animation: a `dcc.Interval` stepping `analysis-race-frame`, stopped at the
    last frame; Replay restarts.
- **New `dcc.Store`s / Interval** (namespaced to avoid colliding with the existing
  team carousel `carousel-index` / `move_carousel`): `analysis-view-index`,
  `analysis-race-frame`, `analysis-race-interval`.
- **Dependency:** first Plotly usage in the app — add `plotly` to
  [requirements.txt](../../../requirements.txt). Figures use a transparent
  background and a `plotly_layout(theme)` helper that reads the active light/dark
  scheme; no hardcoded black text.

---

## 9. Styling / theme (`theme.py`)

- Team palette, fixed & consistent across all 10 views (assigned in group-seeding
  order so a team keeps its color): `#534AB7` / `rgba(83,74,183,0.15)`,
  `#1D9E75` / `rgba(29,158,117,0.15)`, `#D85A30` / `rgba(216,90,48,0.15)`,
  `#378ADD` / `rgba(55,138,221,0.15)`.
- Dumbbell: xG `#888780`, goals `#185FA5`, connector green `#1D9E75` / orange
  `#D85A30`. Defensive segments: tackles `#1D9E75`, interceptions `#378ADD`,
  clearances `#EF9F27`, aerials won `#D85A30`.
- Transparent Plotly background; honor the app's light/dark theme.
- **Global polish standard (every view):** rich custom hovers (real raw value + a
  derived context number — per-90, % of total, step conversion, share); plain-
  language axis labels with units; direct on-chart team annotations; one-line
  caption; muted caveat where a chart can mislead; clean flat style, transparent
  background, subtle gridlines; consistent type scale; rounded numbers; legend-click
  to isolate a team; never rely on color alone (pair with label/position).

---

## 10. Empty / degraded states

The live `team_stats_store` is gitignored and may be empty in dev, so these are
first-class:

- **No FINISHED matches for a group** → clean "No completed matches yet for
  Group X" placeholder, not a broken chart.
- **Partial / failed fetch** → keep last-known store rows (never blank or zero good
  data); show an "as of MD{n} · updated {t} ago" label and a quiet "showing last
  known data" state.
- **Validation:** records are checked (fields present, numeric) before being trusted
  — already enforced by `parse_team_match_stats` (defaults to 0.0); the accessor
  adds a guard so a glitched feed cannot zero a team.

---

## 11. Testing (TDD — mirrors the existing pure-function style)

Tests assert on returned objects (`go.Figure`, component trees via
`.to_plotly_json()`); no browser in the core loop.

- **accessors / aggregate / matchday:** sum vs mean rollup; per-90; field-relative
  scaling incl. divide-by-zero; chronological matchday cumulation; canonical
  team-name mapping; FINISHED-only filter; goals/points/assists/conceded join;
  empty store → placeholder path.
- **views:** each builder returns the expected trace count (4 teams); radar axes ≤ 6
  and no raw+`_succ` pair; dumbbell sort order + connector color logic; race frame
  count = matchdays and re-sort per frame; funnel stages; quadrant crosshair;
  stacked segments/colors; bubble size mapping.
- **panel / carousel:** wrap-around index math; dots/position; RACE controls present
  only when active; caveat notes present on DEFENSIVE_WORK / goals-conceded /
  small-sample finishing.
- **integration:** Team mode renders the panel in the map tile; theme passes
  through; runs against the fixture dataset.
- **Fixtures:** `tests/fixtures/analysis/` — one group, 4 teams, 3 matchdays of
  stats + results — so all 10 charts are TDD-able and demoable without the live API.
- **E2E** (Playwright, Framework 3.11 env per project memory): optional / manual,
  not in the core TDD loop.

Environment note: run unit tests on the conda base env (per project memory).

---

## 12. Acceptance checks

Carried from the build spec §8 — all must pass:

- [ ] Panel resolves a group id to its 4 teams and renders their aggregates.
- [ ] Stats reflect cumulative aggregate across FINISHED matches; update on new data.
- [ ] Arrows cycle all 10 views; wrap-around works; position indicator updates.
- [ ] Each team keeps the same color across all 10 views.
- [ ] Radars normalize 0–100 field-relative; per-90 applied to count metrics; a team
      with more matches doesn't dominate count axes.
- [ ] No raw+successful pair on the same radar; DEFENSIVE_WORK shows its caveat.
- [ ] Dumbbell sorted by (goals−xg); connector color matches over/underperformance;
      raw values; small-sample caveat.
- [ ] RACE: dropdown switches metric (points, goals, assists, total cards, goals
      conceded) and restarts; per-matchday history derived chronologically;
      auto-plays once, bars re-sort per frame, matchday label updates, stops at the
      latest matchday, Replay re-runs, no infinite loop; goals-conceded direction
      caveat.
- [ ] Radar hover shows raw values, not normalized; ticks hidden, rings visible.
- [ ] SHOT_FUNNEL stage counts + step conversion %; hover shows % of previous and of
      all shots.
- [ ] QUALITY_VS_CONV crosshair + labels; hover shows xG/shot, conversion, raw goals
      & shots; team names annotated.
- [ ] HOW_THEY_DEFEND stacked, fixed colors + legend, per-90; hover shows share;
      misleading-volume caveat.
- [ ] VOLUME_VS_PENETR bubble size = accuracy %; axes padded; hover shows final-third
      share; team names annotated.
- [ ] Every view has custom rich hovers, plain-language axes, a one-line caption,
      and direct on-chart annotations.
- [ ] Renders in dark mode and light mode; fits the bento tile; uses only
      Plotly/Dash across all 10 views.

### Data handling (§2A)
- [ ] Charts read only through `get_group_aggregates()` / `get_matchday_history()`.
- [ ] Store is append-only, one row per (team, match_id); aggregates derived, not
      overwritten; matchday history survives a restart.
- [ ] Writes atomic (temp + replace); reads never see a partial file.
- [ ] Re-fetching a match upserts by (team, match_id) — no double-counting.
- [ ] Partial/empty fetch keeps last known good data; panel shows staleness.
- [ ] Records validated (numeric) before use.
- [ ] Data file path is a config/env setting on a persistent path, not the code
      folder.

---

## 13. Out of scope (TODO hooks only — do not build)

- Per-player radars.
- Team picker / cross-group comparison (membership fixed by group).
- Standalone discipline/cards view (cards already appear as a RACE metric).
- Exporting charts as images.
- DB migration — the accessor seam is the swap point.
