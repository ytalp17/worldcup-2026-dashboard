# Estimated Starting XI Pitch — Design

**Date:** 2026-06-07

## Goal

Show each team's estimated starting XI as a football-pitch infographic in a
Team-mode bento cell. The pitch follows the carousel-selected team and the
app's dark/light theme.

## Data

`scrape_mylineups.py` (already run) produced
`assets/data/estimated_starting_eleven.json`: a dict keyed by team slug, each
entry `{name, formation, coach, xi:[[surname, number] × 11]}`. All 48 teams
parsed cleanly (11 players + a valid mplsoccer formation each). Seven distinct
formations occur (4231, 433, 3421, 442, 343, 4141, 4411) — all supported by
mplsoccer 1.6.1's `pitch.formation()`.

## Architecture

Static, pre-rendered PNGs (chosen over an interactive Plotly/SVG pitch). A
build-time script renders one pitch image per team **per theme**; the Dash app
serves them as static assets and swaps the `src` on carousel/theme change. No
new app runtime dependency — mplsoccer/matplotlib are build-time only.

### Components

1. **`src/data/lineups.py`** — data layer (mirrors `squads.py`).
   - `_SLUG_TO_CANONICAL`: 48-entry map from scrape slug → the app's canonical
     FIFA team name (`south-korea`→`Korea Republic`, `iran`→`IR Iran`,
     `ivory-coast`→`Côte d'Ivoire`, `turkiye`→`Türkiye`, `cape-verde`→`Cabo
     Verde`, `dr-congo`→`Congo DR`, `curacao`→`Curaçao`,
     `bosnia-and-herzegovina`→`Bosnia and Herzegovina`, `usa`→`USA`, rest are a
     direct title-case of the slug).
   - `StartingEleven` frozen dataclass: `team` (canonical), `slug`,
     `formation` (digits, e.g. `"433"`), `coach`, `xi` (tuple of
     `(surname:str, number:int)`).
   - `format_formation(digits) -> "4-3-3"` (hyphenate digits).
   - `LineupRepository(path).load() -> dict[canonical_name, StartingEleven]`.
   - `lineup_for_team(lineups, team) -> StartingEleven | None`.

2. **`wc2026_pitches.py`** (root; relocated from `tests/`) — build script.
   - Reads `assets/data/estimated_starting_eleven.json`.
   - For each team: `VerticalPitch(pitch_type="opta", …)`,
     `pitch.get_formation(formation)` for slot positions,
     `pitch.formation(formation, kind="scatter")` for nodes; shirt number inside
     each node, surname below; GK node a distinct colour; title = team +
     hyphenated formation.
   - Renders **two themed variants** (`THEMES` dict: dark + light) differing in
     pitch/line/node/text colours and figure facecolor.
   - Writes `assets/pitches/<slug>-dark.png` and `assets/pitches/<slug>-light.png`.
   - `render_team(key, data, theme, outdir) -> path` is unit-testable
     (renders to a tmp dir, returns the written path).

3. **`src/components/formation_pitch.py`** — view.
   - `pitch_src(slug, asset_url, dark) -> str` builds
     `pitches/<slug>-{dark|light}.png` via `asset_url`.
   - `build_formation_panel(lineup, asset_url, dark=True) -> dmc.Box`
     (`className="formation-panel"`): a `bento-card__header` ("Formation" left,
     hyphenated formation + team name right, header id `formation-title`) and a
     body `dmc.Image(id="formation-img", fit="contain")` with the pitch src.
     `lineup=None` → header "—", no image src.

### Wiring

- `layout.py`: cell **e2** carries the formation panel
  (`className="bento-card bento-card--formation"`); e1/e3/e4 stay empty.
  `build_layout(..., formation_panel=...)`.
- `app.py`:
  - `LINEUPS = LineupRepository(DATA_DIR / "estimated_starting_eleven.json").load()`.
  - `formation_panel_payload(index, dark) -> (formation_display, team, img_src)`
    for the centred team.
  - Callback `update_formation_panel(index, dark)` — Inputs
    `carousel-index.data` + `color-scheme-toggle.checked` — Outputs
    `formation-img.src`, `formation-title.children`. Single owner of the src
    (no carousel/theme conflict). Mirrors `update_squad_panel`.

### Styling

`.formation-panel` — flex column, full height, `overflow:hidden` (like
`.squad-panel`). Body centers the image; `#formation-img img` →
`object-fit:contain; max-height:100%; max-width:100%`. No horizontal overflow;
mobile stack inherits existing `bento-card--empty`-style rules (formation card
gets an explicit min-height in the mobile block).

## Theme handling

PNGs don't theme themselves, so two sets are rendered. A transparent figure
background lets the card colour show through the margins; pitch/line/text
colours are chosen per theme for contrast. The existing
`color-scheme-toggle.checked` boolean drives the variant.

## Error handling

- Slug missing from `_SLUG_TO_CANONICAL` → fall back to title-cased slug
  (logged at load; never crashes).
- `lineup_for_team` returns `None` for unknown team → panel renders the "—"
  placeholder, no image.
- Generator raises if `len(xi)` ≠ formation slot count (data integrity guard).

## Testing

- `tests/test_lineups.py`: slug→canonical mapping (incl. the accented/renamed
  ones), `format_formation`, repository load count (48), `xi` parsed as
  `(str,int)` tuples, `lineup_for_team` hit/miss.
- `tests/test_formation_pitch.py`: `pitch_src` dark vs light filenames;
  `build_formation_panel` has the header (id `formation-title`, hyphenated
  formation text) and `dmc.Image` id `formation-img`; `None` placeholder.
- `tests/test_wc2026_pitches.py`: `render_team` writes a non-empty PNG for both
  themes into a tmp dir (uses one sample team; Agg backend).
- `tests/test_layout.py`: e2 holds the formation card; `tests/test_app.py`:
  `formation_panel_payload` returns the centred team's formation + a
  theme-correct src.

Out of scope: re-scraping in CI, interactivity on the pitch, coach display
(kept in data, not shown in v1).
