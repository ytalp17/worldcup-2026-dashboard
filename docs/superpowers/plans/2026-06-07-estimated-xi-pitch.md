# Estimated Starting XI Pitch — Implementation Plan

> **For agentic workers:** Use superpowers:subagent-driven-development or
> executing-plans. Steps use checkbox (`- [ ]`) syntax. TDD throughout.

**Goal:** Render each team's estimated XI as an mplsoccer pitch PNG (dark+light),
shown in Team-mode bento cell e2, following the carousel team + app theme.

**Architecture:** Pre-rendered static PNGs (build-time, mplsoccer). Data layer
maps scrape slugs → canonical FIFA names. A single server callback owns the
image `src`, keyed on carousel index + theme.

**Tech Stack:** pandas/json, dataclasses, mplsoccer 1.6.1 (build-time),
dash-mantine-components, Dash callbacks. Tests on conda base
(`~/anaconda3/bin/conda run -n base python -m pytest tests/ -v`).

---

### Task 1: Data layer — `src/data/lineups.py`

**Files:** Create `src/data/lineups.py`; Test `tests/test_lineups.py`.

- [ ] **Step 1 — failing tests** (`tests/test_lineups.py`):

```python
from pathlib import Path
from src.data.lineups import (
    LineupRepository, StartingEleven, canonical_team, format_formation,
    lineup_for_team,
)

DATA = Path("assets/data/estimated_starting_eleven.json")

def test_canonical_team_renames():
    assert canonical_team("south-korea") == "Korea Republic"
    assert canonical_team("ivory-coast") == "Côte d'Ivoire"
    assert canonical_team("iran") == "IR Iran"
    assert canonical_team("turkiye") == "Türkiye"
    assert canonical_team("dr-congo") == "Congo DR"
    assert canonical_team("cape-verde") == "Cabo Verde"
    assert canonical_team("usa") == "USA"
    assert canonical_team("brazil") == "Brazil"  # plain title-case fallback

def test_format_formation():
    assert format_formation("433") == "4-3-3"
    assert format_formation("4231") == "4-2-3-1"

def test_repository_loads_all_48():
    lineups = LineupRepository(DATA).load()
    assert len(lineups) == 48
    arg = lineups["Argentina"]
    assert isinstance(arg, StartingEleven)
    assert arg.slug == "argentina"
    assert arg.formation == "433"
    assert len(arg.xi) == 11
    name, number = arg.xi[0]
    assert isinstance(name, str) and isinstance(number, int)

def test_lineup_for_team_hit_and_miss():
    lineups = LineupRepository(DATA).load()
    assert lineup_for_team(lineups, "Korea Republic").slug == "south-korea"
    assert lineup_for_team(lineups, "Nowhere") is None
```

- [ ] **Step 2** — run, verify fail (ImportError).
- [ ] **Step 3 — implement** `src/data/lineups.py`:
  - `_SLUG_TO_CANONICAL` dict for the 9 renamed slugs (south-korea, ivory-coast,
    iran, turkiye, dr-congo, cape-verde, curacao, bosnia-and-herzegovina, usa).
  - `canonical_team(slug)`: dict lookup, else `slug.replace("-"," ").title()`.
  - `format_formation(digits)`: `"-".join(digits)`.
  - `StartingEleven(team, slug, formation, coach, xi)` frozen dataclass; `xi` is
    `tuple[tuple[str,int], ...]`.
  - `LineupRepository(path).load()`: read JSON, build dict keyed by
    `canonical_team(slug)`, `xi` = `tuple((str(n), int(num)) for n,num in v["xi"])`.
  - `lineup_for_team(lineups, team)`: `lineups.get(team)`.
- [ ] **Step 4** — tests pass.
- [ ] **Step 5** — commit.

---

### Task 2: Build script — `wc2026_pitches.py`

**Files:** Create `wc2026_pitches.py` (root, adapted from `tests/wc2026_pitches.py`);
delete `tests/wc2026_pitches.py`; Test `tests/test_wc2026_pitches.py`.

- [ ] **Step 1 — failing test** (`tests/test_wc2026_pitches.py`):

```python
import matplotlib
matplotlib.use("Agg")
from wc2026_pitches import render_team, THEMES

SAMPLE = {"name": "Argentina", "formation": "433", "coach": "",
          "xi": [["Martínez", 23], ["Molina", 26], ["Otamendi", 19],
                 ["Martínez", 6], ["Tagliafico", 3], ["De Paul", 7],
                 ["Fernández", 24], ["Mac Allister", 20], ["González", 15],
                 ["Messi", 10], ["Álvarez", 9]]}

def test_render_team_writes_png_per_theme(tmp_path):
    for theme in ("dark", "light"):
        out = render_team("argentina", SAMPLE, THEMES[theme], theme, tmp_path)
        assert out.exists()
        assert out.suffix == ".png"
        assert out.stat().st_size > 0
        assert out.name == f"argentina-{theme}.png"
```

- [ ] **Step 2** — run, verify fail (ImportError / no render_team).
- [ ] **Step 3 — implement** `wc2026_pitches.py`:
  - `THEMES = {"dark": {...}, "light": {...}}` with keys
    `pitch_color, line_color, node_color, gk_color, text_color, fig_color`.
  - `render_team(key, data, theme, name, outdir) -> Path`: VerticalPitch with
    theme colours, `get_formation` + `formation(kind="scatter")`, number+surname
    annotations, title `name -<formation>`, save
    `outdir/<key>-<name>.png`, `plt.close`. Reuse existing draw logic.
  - `main()`: load `assets/data/estimated_starting_eleven.json`, loop teams ×
    themes → `assets/pitches/`. Print progress.
- [ ] **Step 4** — test passes; `git rm tests/wc2026_pitches.py`.
- [ ] **Step 5** — commit.

---

### Task 3: Generate all PNGs

- [ ] **Step 1** — `~/anaconda3/bin/conda run -n base python wc2026_pitches.py`.
- [ ] **Step 2** — verify `ls assets/pitches | wc -l` == 96, spot-check a dark +
  light image visually (Read the PNG).
- [ ] **Step 3** — commit the generated assets.

---

### Task 4: Component — `src/components/formation_pitch.py`

**Files:** Create `src/components/formation_pitch.py`;
Test `tests/test_formation_pitch.py`.

- [ ] **Step 1 — failing tests**:

```python
import dash_mantine_components as dmc
from src.components.formation_pitch import build_formation_panel, pitch_src
from src.data.lineups import StartingEleven

def _asset(p): return "/assets/" + p
LIN = StartingEleven("Argentina", "argentina", "433", "",
                     (("Messi", 10), ("Álvarez", 9)))

def _walk(n):
    yield n
    ch = getattr(n, "children", None)
    if isinstance(ch, (list, tuple)):
        for c in ch: yield from _walk(c)
    elif ch is not None:
        yield from _walk(ch)

def test_pitch_src_theme():
    assert pitch_src("argentina", _asset, True).endswith("pitches/argentina-dark.png")
    assert pitch_src("argentina", _asset, False).endswith("pitches/argentina-light.png")

def test_panel_has_header_and_image():
    panel = build_formation_panel(LIN, _asset, dark=True)
    img = next(n for n in _walk(panel) if isinstance(n, dmc.Image))
    assert img.id == "formation-img"
    assert img.src.endswith("pitches/argentina-dark.png")
    title = next(n for n in _walk(panel)
                 if getattr(n, "id", None) == "formation-title")
    assert "4-3-3" in title.children

def test_panel_none_placeholder():
    panel = build_formation_panel(None, _asset)
    imgs = [n for n in _walk(panel) if isinstance(n, dmc.Image) and n.src]
    assert not imgs
```

- [ ] **Step 2** — run, verify fail.
- [ ] **Step 3 — implement**: `pitch_src(slug, asset_url, dark)` →
  `asset_url(f"pitches/{slug}-{'dark' if dark else 'light'}.png")`.
  `build_formation_panel(lineup, asset_url, dark=True)`: header Group
  (`bento-card__header`) with `dmc.Text("Formation", fw=700, size="sm")` and
  `dmc.Text(f"{format_formation(lineup.formation)} · {lineup.team}",
  id="formation-title", size="sm", c="dimmed")` (or "—" id-only text when None);
  body `dmc.Box(dmc.Image(id="formation-img", src=..., fit="contain"),
  className="formation-panel__body")`. Return
  `dmc.Box([header, body], className="formation-panel")`.
- [ ] **Step 4** — tests pass.
- [ ] **Step 5** — commit.

---

### Task 5: Wire into layout + app

**Files:** Modify `src/components/layout.py`, `app.py`;
Tests `tests/test_layout.py`, `tests/test_app.py`.

- [ ] **Step 1 — failing tests**:
  - `test_layout.py`: build layout, assert a node with
    `className` containing `bento-card--formation` exists and contains
    `formation-img`; e1/e3/e4 still empty.
  - `test_app.py`: `from app import formation_panel_payload`;
    `disp, team, src = formation_panel_payload(0, True)`; assert
    `src.endswith("-dark.png")` and `disp` matches the centred team's formation;
    `formation_panel_payload(0, False)[2].endswith("-light.png")`.
- [ ] **Step 2** — run, verify fail.
- [ ] **Step 3 — implement**:
  - `layout.py`: add `formation_panel` param; build
    `formation_card = dmc.Box(formation_panel, className="bento-card bento-card--formation")`;
    insert into `main` children; drop e2 from `empty_cards` (range now e1,e3,e4 —
    keep ids `bento-e1`,`bento-e3`,`bento-e4`). Update CSS area mapping note.
  - `app.py`: import `LineupRepository, lineup_for_team`, `build_formation_panel`,
    `format_formation`; `LINEUPS = …load()`;
    `formation_panel_payload(index, dark)`; pass
    `formation_panel=build_formation_panel(lineup_for_team(LINEUPS,
    center_team(TEAM_NAMES,0)), app.get_asset_url, dark=True)` to `build_layout`;
    add `update_formation_panel` callback (Outputs `formation-img.src`,
    `formation-title.children`; Inputs `carousel-index.data`,
    `color-scheme-toggle.checked`).
- [ ] **Step 4** — tests pass.
- [ ] **Step 5** — commit.

---

### Task 6: CSS + verification

**Files:** Modify `assets/styles.css`.

- [ ] **Step 1** — add `.formation-panel` (flex column, height 100%,
  overflow hidden), `.formation-panel__body` (flex 1, display flex,
  align/justify center, min-height 0, padding 6px), `#formation-img` /
  `#formation-img img` (`object-fit:contain; max-height:100%; max-width:100%`).
  Mobile block: give `.bento-card--formation` a sensible min-height.
- [ ] **Step 2** — full suite: `~/anaconda3/bin/conda run -n base python -m
  pytest tests/ -v` (all green, no new warnings).
- [ ] **Step 3** — boot app headless, confirm no callback/exception; Playwright
  (Framework 3.11): Team mode → formation card renders an image in e2; toggle
  theme → src flips dark↔light; advance carousel → image + title update.
  Screenshot.
- [ ] **Step 4** — commit.

---

### Task 7: Finish

- [ ] Use superpowers:finishing-a-development-branch (verify tests → merge).
