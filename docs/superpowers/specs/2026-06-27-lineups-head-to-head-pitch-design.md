# Head-to-Head Lineup Pitch — Design

**Date:** 2026-06-27

## Goal

Add a single pitch to the match-detail modal's **Lineups** tab showing both
teams facing each other — home on the left half (attacking right), away on the
right half (attacking left), meeting at the centre line — like a broadcast
lineup graphic. Player names are shown on the pitch. Replaces the current
two-column starter lists.

## Why this is straightforward

The live API returns `initialLineup` already grouped into **rows**, one per
formation line, GK → forwards, per team, plus a hyphenated `formation` string.
Verified from `tests/fixtures/live/finished_lineups.json`:

- USA `4-2-3-1` → rows of `[1, 4, 2, 3, 1]`
- Paraguay `4-4-2` → rows of `[1, 4, 4, 2]`

So no mplsoccer, scipy, or position-guessing is needed at runtime — the rows
*are* the lines, already correctly ordered. (`position` is coarse here:
Goalkeeper/Defender/Midfielder/Forward; we don't need it for placement.)

## Components

### 1. Data — `src/data/live/models.py::parse_lineups`

Add a `rows` field per team, preserving the `initialLineup` grouping:

```python
"rows": [
    [{"name": ..., "number": ..., "position": ...}, ...],  # one row per line
    ...
]
```

Keep `starters`, `subs`, `formation` unchanged (other callers/tests rely on
them). `rows` is empty when `initialLineup` is empty (e.g. pre-match,
formation `"Unknown"`).

### 2. Layout — new pure module `src/components/lineup_pitch.py`

`pitch_nodes(rows, side) -> list[(player, x, y)]`, x/y in 0–100:

- `side="home"`: GK at x≈4, successive lines march right; forwards near the
  centre line (x≈46).
- `side="away"`: mirrored — GK at x≈96, forwards near x≈54.
- Within a line of N players, spread vertically across [12, 88]; a single
  player (GK, lone striker) centres at y=50.
- A team with one row (degenerate) centres at the mid-x of its half.

`_surname(name)` → last whitespace token (e.g. "Christian Pulišić" →
"Pulišić").

`build_lineup_pitch(lineups) -> dmc.Box | None`:
- Reads `home`/`away` `rows`; returns `None` if both are empty (caller then
  shows the "not available" text).
- Emits a relative-positioned `dmc.Box.lu-pitch` containing one
  absolutely-positioned node per player: a colored shirt-number badge +
  surname label, placed via `left%`/`top%`.
- Home nodes use Mantine `blue`, away nodes use `orange`
  (`var(--mantine-color-blue-6)` / `-orange-6`).

### 3. Rendering — `src/components/live_match_modal.py::_lineups_tab`

Replace the two-column starter lists with the pitch. If
`build_lineup_pitch` returns `None`, show the existing "Lineups not
available." text.

### 4. Styling — `assets/styles.css`

- `.lu-pitch`: `position: relative`, `width: 100%`, fixed `aspect-ratio`
  (~16/10), rounded, pitch-green background with a centre line and centre
  circle drawn in CSS. Theme-reactive via the app's existing pattern:
  light green by default, darker green under
  `[data-mantine-color-scheme="dark"] .lu-pitch` (mirroring the team-view PNG
  palettes). No callback needed — CSS variables/selectors swap live on the
  dark/light toggle, which matters because the modal body is built once and
  cannot see the current scheme.
- `.lu-node`: `position: absolute`, `transform: translate(-50%, -50%)`,
  flex column, centered.
- `.lu-node__badge`: circular shirt-number chip; size in relative units so it
  scales with the pitch.
- `.lu-node__name`: small white label with a subtle text-shadow for legibility
  on green; never causes horizontal overflow on mobile.

## Data flow

`fill_live_modal` (Phase 2) → `modal_body(..., lineups)` → `_lineups_tab` →
`build_lineup_pitch(lineups)` → positioned nodes. All server-side, built once
per modal open.

## Error handling / edge cases

- Empty `rows` (pre-match / `Unknown` formation) → no pitch, "Lineups not
  available." text.
- Odd line counts → vertical distribution handles any N.
- 22 nodes on a small modal → small surnames, relative sizing; responsive,
  no horizontal overflow.

## Testing (TDD)

`tests/test_live_models.py`:
- `parse_lineups` includes `rows` grouped as `[1,4,2,3,1]` (home) and
  `[1,4,4,2]` (away) from the finished fixture; empty `rows` for the
  empty fixture.

`tests/test_lineup_pitch.py` (new, pure):
- `_surname` returns the last token.
- `pitch_nodes`: home GK x is small, away GK x is large; both forward lines
  sit near the centre (home x < 50 < away x but both within a few units of
  50); single-player line centres at y=50; multi-player line spreads
  (distinct, ordered y's); every player placed exactly once.
- `build_lineup_pitch` returns a `dmc.Box` whose descendants include all 22
  surnames and 22 number badges; home badges blue, away badges orange.
- `build_lineup_pitch` returns `None` for empty lineups.

`tests/test_live_match_modal.py`:
- `_lineups_tab` renders the pitch (a `.lu-pitch` node) when rows exist;
  shows "Lineups not available." when empty.

## Verification

Run the app, open a finished match's modal, switch to Lineups, confirm the
head-to-head pitch renders with both teams, names legible, correct colors, and
that it re-themes on the dark/light toggle and holds up at phone width.
