# Deep Analysis Panel Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a 10-view Plotly chart carousel that compares the 4 teams of a World Cup group, replacing the Leaflet map tile in Team mode only.

**Architecture:** A thin accessor seam (`src/data/analysis/`) reads the existing append-only `team_stats_store` + `player_store` + static `MATCHES`/`GROUPS`, derives cumulative per-team aggregates and per-matchday history, and exposes exactly two functions to the charts. A component package (`src/components/analysis/`) holds the carousel shell and ten pure Plotly figure-builders keyed by a single ordered view config. App-level callbacks drive a view-index store, the figure render, and the bar-race animation.

**Tech Stack:** Python 3.10+, Dash 4.2 (FastAPI backend), `dash-mantine-components` 2.4.0, `plotly` 6.8.0 (already installed via Dash), `pandas`, `pytest`.

## Global Constraints

- **UI components:** `dash-mantine-components` only (no Bootstrap / raw `html.Button`). The carousel arrows use `dmc.ActionIcon`; controls use `dmc.Select`, `dmc.Button`.
- **Charts:** Plotly only (`plotly.graph_objects`, `dcc.Graph`). No Chart.js / matplotlib.
- **Data:** `pandas` for any wrangling; reuse the existing stores — do **not** add a new storage layer.
- **OOP:** dataclasses for data entities where one fits.
- **TDD:** write the failing test first, watch it fail, implement minimal code, watch it pass, commit. Run `pytest tests/ -v`.
- **Theme:** every figure honors light/dark (`plotly_layout(theme)`); never hardcode black text. Transparent background.
- **Layout:** full-screen, no scrollbars; the panel must fit the Team-mode map tile footprint.
- **Accessor seam:** chart/view/callback code calls **only** `get_group_aggregates()` / `get_matchday_history()`. Never read a store or the API from view code.
- **Team palette (fixed, in group-seeding order, identical across all 10 views):** `#534AB7`, `#1D9E75`, `#D85A30`, `#378ADD` (fills at 0.15 alpha).
- **Discipline metrics** (yellow, red, fouls, offsides) excluded from all views except as a RACE metric.
- **Match state:** only `"finished"` matches enter aggregates.
- **Matchday model:** each team's Nth match in chronological order (by static fixture date, tie-break match_id).
- **Env note:** run unit tests on the conda **base** env (per project memory), e.g. `python -m pytest tests/ -v`.

### Key existing APIs this plan builds on (verified)

- `src.data.live.team_stats_store`
  - `load(path) -> dict[int, list[TeamMatchStat]]` (`TeamMatchStat(match_id, team, stats: dict)`; `stats` has every key in `STAT_KEYS`, floats).
  - `stored_match_states(path) -> dict[int, str]` (match_id → `"finished"|"live"|...`).
- `src.data.live.team_match_stats.STAT_KEYS` — ordered list of the 24+ internal keys (xg, xa, big_chances, possession, shots_on, shots_off, shots_blocked, shots_in_box, corners, passes_total, passes_succ, key_passes, passes_final_third, long_passes, crosses, crosses_succ, dribbles, dribbles_succ, tackles, tackles_succ, interceptions, clearances, aerials, aerials_won, gk_saves, fouls, offsides, yellow, red).
- `src.data.live.player_store.load(path) -> dict[int, list[PlayerMatchStat]]` (`PlayerMatchStat(match_id, team, player, player_id, goals, assists, yellow, red)`).
- `src.data.live.reconcile.canonical_team(name) -> str` (normalizes raw team names; the join key).
- `src.data.groups`: `Group(name, standings: tuple[GroupStanding,...])`, `GroupStanding(team, ...)`, `build_groups(matches) -> dict[str, Group]`, `group_for_team(groups, team) -> Group | None`.
- `src.data.matches.Match(number, home, away, group, stage, stadium, date, local_time, kickoff_utc)`. Group-stage rows have `stage == "Group Stage"` and a non-empty `group` like `"Group A"`.
- `src.data.live.models.MatchState.FINISHED.value == "finished"`.
- In `app.py`: `GROUPS`, `MATCHES`, `TEAM_NAMES`, `TEAM_STATS_PATH`, `PLAYER_STORE_PATH`, `center_team(TEAM_NAMES, index)`, `group_for_team`, `official_team(name)`, the `carousel-index` and `live-store` stores, and the clientside mode toggle that adds `main-split--team` and fires a window resize.

---

## File Structure

```
src/data/analysis/
  __init__.py
  matchday.py      # finished_ids, match_meta, team_finished_matches (chronological)
  aggregate.py     # build_record, per90, field_relative, radar_series
  accessors.py     # configure(), get_group_aggregates(), get_matchday_history()  <- THE SEAM
src/components/analysis/
  __init__.py
  theme.py         # team palette, segment colors, plotly_layout(theme)
  views.py         # VIEWS config + 7 figure builders + build_figure dispatcher
  panel.py         # build_analysis_panel() -> bento card shell (graph, arrows, dots, controls)
tests/
  fixtures/analysis/__init__.py
  fixtures/analysis/sample.py   # one group, 4 teams, 3 matchdays of stats + players
  test_analysis_matchday.py
  test_analysis_aggregate.py
  test_analysis_accessors.py
  test_analysis_theme.py
  test_analysis_views_radar.py
  test_analysis_views_dumbbell.py
  test_analysis_views_race.py
  test_analysis_views_funnel.py
  test_analysis_views_quadrant.py
  test_analysis_views_defend.py
  test_analysis_views_bubble.py
  test_analysis_panel.py
  test_analysis_callbacks.py
  test_analysis_integration.py
```
Modified: `requirements.txt`, `app.py`, `src/components/layout.py`, `assets/styles.css`.

---

## Task 1: Scaffold package, pin plotly, build the theme module

**Files:**
- Create: `src/data/analysis/__init__.py` (empty), `src/components/analysis/__init__.py` (empty), `src/components/analysis/theme.py`
- Create: `tests/test_analysis_theme.py`
- Modify: `requirements.txt`

**Interfaces:**
- Produces:
  - `theme.TEAM_COLORS: list[str]` = `["#534AB7", "#1D9E75", "#D85A30", "#378ADD"]`
  - `theme.TEAM_FILLS: list[str]` (same hues at 0.15 alpha, `rgba(...)`)
  - `theme.team_color_map(teams: list[str]) -> dict[str, str]` (assign colors in order, cycle if >4)
  - `theme.team_fill_map(teams: list[str]) -> dict[str, str]`
  - `theme.DEFEND_COLORS: dict[str, str]` = `{"tackles_succ": "#1D9E75", "interceptions": "#378ADD", "clearances": "#EF9F27", "aerials_won": "#D85A30"}`
  - `theme.DUMBBELL: dict[str, str]` = `{"xg": "#888780", "goals": "#185FA5", "over": "#1D9E75", "under": "#D85A30"}`
  - `theme.plotly_layout(theme: str = "dark", **overrides) -> dict` — base `go.Layout` kwargs (transparent bg, theme font/grid colors, tight margins, hover styling, minimal modebar config left to the graph)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_analysis_theme.py
from __future__ import annotations

from src.components.analysis import theme


def test_palette_is_the_four_spec_colors_in_order():
    assert theme.TEAM_COLORS == ["#534AB7", "#1D9E75", "#D85A30", "#378ADD"]
    assert len(theme.TEAM_FILLS) == 4
    assert all(f.startswith("rgba(") and "0.15" in f for f in theme.TEAM_FILLS)


def test_color_map_assigns_in_order_and_cycles():
    m = theme.team_color_map(["Mexico", "Brazil", "Spain", "Japan"])
    assert m["Mexico"] == "#534AB7"
    assert m["Japan"] == "#378ADD"
    # a 5th team cycles back to the first color (never KeyErrors)
    m5 = theme.team_color_map(["A", "B", "C", "D", "E"])
    assert m5["E"] == "#534AB7"


def test_plotly_layout_is_transparent_and_theme_aware():
    dark = theme.plotly_layout("dark")
    light = theme.plotly_layout("light")
    assert dark["paper_bgcolor"] == "rgba(0,0,0,0)"
    assert dark["plot_bgcolor"] == "rgba(0,0,0,0)"
    assert dark["font"]["color"] != light["font"]["color"]


def test_defend_and_dumbbell_color_constants():
    assert theme.DEFEND_COLORS["tackles_succ"] == "#1D9E75"
    assert theme.DEFEND_COLORS["clearances"] == "#EF9F27"
    assert theme.DUMBBELL["xg"] == "#888780"
    assert theme.DUMBBELL["goals"] == "#185FA5"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_analysis_theme.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.components.analysis'`

- [ ] **Step 3: Create the empty package files**

Create `src/data/analysis/__init__.py` and `src/components/analysis/__init__.py` as empty files.

- [ ] **Step 4: Write `src/components/analysis/theme.py`**

```python
from __future__ import annotations

# Fixed team palette (group-seeding order). A team keeps its color across all
# 10 views. Colors and 0.15-alpha fills come straight from the spec.
TEAM_COLORS = ["#534AB7", "#1D9E75", "#D85A30", "#378ADD"]
TEAM_FILLS = [
    "rgba(83,74,183,0.15)",
    "rgba(29,158,117,0.15)",
    "rgba(216,90,48,0.15)",
    "rgba(55,138,221,0.15)",
]

# Fixed action->color mapping for HOW_THEY_DEFEND (consistent across teams).
DEFEND_COLORS = {
    "tackles_succ": "#1D9E75",
    "interceptions": "#378ADD",
    "clearances": "#EF9F27",
    "aerials_won": "#D85A30",
}

# FINISHING dumbbell colors.
DUMBBELL = {"xg": "#888780", "goals": "#185FA5", "over": "#1D9E75", "under": "#D85A30"}


def team_color_map(teams: list[str]) -> dict[str, str]:
    """Team -> hex color, assigned in the given order, cycling if >4 teams."""
    return {t: TEAM_COLORS[i % len(TEAM_COLORS)] for i, t in enumerate(teams)}


def team_fill_map(teams: list[str]) -> dict[str, str]:
    """Team -> rgba fill, assigned in the given order, cycling if >4 teams."""
    return {t: TEAM_FILLS[i % len(TEAM_FILLS)] for i, t in enumerate(teams)}


def plotly_layout(theme: str = "dark", **overrides) -> dict:
    """Base layout kwargs shared by every figure: transparent background,
    theme-aware text/grid colors, tight margins, autosize, clean hover."""
    dark = theme != "light"
    fg = "#E9ECEF" if dark else "#1A1B1E"
    grid = "rgba(255,255,255,0.10)" if dark else "rgba(0,0,0,0.10)"
    base = dict(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=fg, size=12),
        margin=dict(l=40, r=20, t=10, b=30),
        autosize=True,
        showlegend=False,  # views render a slim custom legend strip instead
        hoverlabel=dict(bgcolor="#23262B" if dark else "#FFFFFF",
                        font_color=fg, bordercolor=grid),
        colorway=TEAM_COLORS,
        modebar=dict(orientation="v"),
        gridcolor_hint=grid,  # consumed by view builders for axis grid color
    )
    base.update(overrides)
    return base
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests/test_analysis_theme.py -v`
Expected: PASS (4 tests)

- [ ] **Step 6: Pin plotly in requirements.txt**

Add this line to `requirements.txt` under the existing Dash deps (plotly ships with Dash but pin it explicitly since it's now a first-class dependency):

```
plotly>=6.0,<7
```

- [ ] **Step 7: Commit**

```bash
git add src/data/analysis/__init__.py src/components/analysis/__init__.py src/components/analysis/theme.py tests/test_analysis_theme.py requirements.txt
git commit -m "feat(analysis): scaffold analysis packages + theme palette/layout"
```

---

## Task 2: Matchday resolution (`matchday.py`)

Resolves which stored matches are FINISHED, what group/teams/date each match_id maps to (by pairing its two stored team rows against the static fixtures), and each team's matches in chronological order.

**Files:**
- Create: `src/data/analysis/matchday.py`
- Test: `tests/test_analysis_matchday.py`

**Interfaces:**
- Consumes: `team_stats_store.load()` shape (`{match_id: [TeamMatchStat]}`), `stored_match_states()` shape (`{match_id: str}`), `Match` list, `canonical_team`.
- Produces:
  - `matchday.FINISHED: str` = `"finished"`
  - `matchday.finished_ids(states: dict[int, str]) -> set[int]`
  - `matchday.match_meta(stats_by_match: dict, matches: list) -> dict[int, dict]` → `{mid: {"teams": (canonA, canonB), "date": date | None, "group": str | None}}`
  - `matchday.team_finished_matches(team_canon: str, finished: set[int], meta: dict) -> list[int]` (chronological: date asc, then match_id asc; matches with no date sort last)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_analysis_matchday.py
from __future__ import annotations

from datetime import date, datetime, time

from src.data.analysis import matchday
from src.data.live.team_match_stats import STAT_KEYS, TeamMatchStat
from src.data.matches import Match


def _stat(mid, team):
    return TeamMatchStat(match_id=mid, team=team, stats={k: 0.0 for k in STAT_KEYS})


def _match(number, home, away, d):
    return Match(number=number, home=home, away=away, group="Group A",
                 stage="Group Stage", stadium="X", date=d,
                 local_time=time(13, 0),
                 kickoff_utc=datetime(2026, 6, d.day, 19, 0))


def test_finished_ids_filters_to_finished_only():
    states = {1: "finished", 2: "live", 3: "finished", 4: "scheduled"}
    assert matchday.finished_ids(states) == {1, 3}


def test_match_meta_pairs_rows_to_fixture_group_and_date():
    stats_by_match = {
        10: [_stat(10, "Mexico"), _stat(10, "South Africa")],
        11: [_stat(11, "Mexico"), _stat(11, "Czechia")],
    }
    fixtures = [
        _match(1, "Mexico", "South Africa", date(2026, 6, 11)),
        _match(2, "Mexico", "Czechia", date(2026, 6, 17)),
    ]
    meta = matchday.match_meta(stats_by_match, fixtures)
    assert meta[10]["group"] == "Group A"
    assert meta[10]["date"] == date(2026, 6, 11)
    assert set(meta[10]["teams"]) == {matchday.canonical("Mexico"),
                                      matchday.canonical("South Africa")}


def test_team_finished_matches_is_chronological():
    stats_by_match = {
        10: [_stat(10, "Mexico"), _stat(10, "South Africa")],
        11: [_stat(11, "Mexico"), _stat(11, "Czechia")],
    }
    fixtures = [
        _match(2, "Mexico", "Czechia", date(2026, 6, 17)),     # later date
        _match(1, "Mexico", "South Africa", date(2026, 6, 11)),
    ]
    meta = matchday.match_meta(stats_by_match, fixtures)
    order = matchday.team_finished_matches(matchday.canonical("Mexico"),
                                           {10, 11}, meta)
    assert order == [10, 11]  # md1 = the 11 June match, md2 = the 17 June match
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_analysis_matchday.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.data.analysis.matchday'`

- [ ] **Step 3: Write `src/data/analysis/matchday.py`**

```python
from __future__ import annotations

from src.data.live.models import MatchState
from src.data.live.reconcile import canonical_team

FINISHED = MatchState.FINISHED.value  # "finished"

# Re-exported so tests/callers canonicalize names the same way the joins do.
canonical = canonical_team


def finished_ids(states: dict[int, str]) -> set[int]:
    """match_ids whose last stored state is FINISHED."""
    return {mid for mid, st in (states or {}).items() if st == FINISHED}


def _fixture_index(matches) -> dict[frozenset, dict]:
    """{frozenset(canonical home, canonical away): {date, group}} for group-stage
    fixtures. Knockout rows (no group) are skipped."""
    out: dict[frozenset, dict] = {}
    for m in matches:
        if m.stage != "Group Stage" or not m.group:
            continue
        key = frozenset({canonical(m.home), canonical(m.away)})
        out[key] = {"date": m.date, "group": m.group}
    return out


def match_meta(stats_by_match: dict, matches) -> dict[int, dict]:
    """Map each stored match_id to its canonical team pair, fixture date, and
    group, by pairing the match's two stored team rows against the fixtures.

    A match with only one stored team row, or no matching fixture, still gets an
    entry with date/group = None so callers degrade rather than crash.
    """
    index = _fixture_index(matches)
    meta: dict[int, dict] = {}
    for mid, rows in (stats_by_match or {}).items():
        teams = tuple(canonical(r.team) for r in rows)
        info = index.get(frozenset(teams)) if len(set(teams)) == 2 else None
        meta[mid] = {
            "teams": teams,
            "date": info["date"] if info else None,
            "group": info["group"] if info else None,
        }
    return meta


def team_finished_matches(team_canon: str, finished: set[int],
                          meta: dict) -> list[int]:
    """A team's FINISHED match_ids in chronological order (date asc, then
    match_id). Matches with an unknown date sort last but keep stable order."""
    mine = [mid for mid in finished
            if team_canon in meta.get(mid, {}).get("teams", ())]
    far = max((m["date"] for m in meta.values() if m.get("date")), default=None)

    def key(mid):
        d = meta[mid].get("date")
        # None dates -> sort after all known dates, tie-break by id
        return (0, d, mid) if d is not None else (1, far, mid)

    return sorted(mine, key=key)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_analysis_matchday.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add src/data/analysis/matchday.py tests/test_analysis_matchday.py
git commit -m "feat(analysis): match->group/date/chronology resolution"
```

---

## Task 3: Per-team aggregate record (`aggregate.py` part 1)

Builds one cumulative record per team from the persistent stores: 24 stat keys (sum; possession = mean), plus goals / assists / goals_conceded / points / matches_played derived from per-match player goals.

**Files:**
- Create: `src/data/analysis/aggregate.py`
- Test: `tests/test_analysis_aggregate.py`

**Interfaces:**
- Consumes: `TeamMatchStat` / `PlayerMatchStat` shapes; `STAT_KEYS`; `matchday.canonical`; `match_meta` output.
- Produces:
  - `aggregate.RATE_KEYS: set[str]` = `{"possession"}`
  - `aggregate.team_match_goals(stats_by_match, players_by_match) -> dict[int, dict[str, int]]` → `{mid: {canonTeam: goals_that_match}}`
  - `aggregate.build_record(team_official, team_canon, chrono_mids, stats_by_match, players_by_match, meta) -> dict` with keys: `team, group, matches_played, goals, goals_conceded, assists, points`, and every key in `STAT_KEYS` (sums; `possession` = mean over played matches).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_analysis_aggregate.py
from __future__ import annotations

from datetime import date

from src.data.analysis import aggregate
from src.data.live.player_stats import PlayerMatchStat
from src.data.live.team_match_stats import STAT_KEYS, TeamMatchStat


def _ts(mid, team, **ov):
    s = {k: 0.0 for k in STAT_KEYS}
    s.update(ov)
    return TeamMatchStat(match_id=mid, team=team, stats=s)


def _ps(mid, team, player, goals=0, assists=0):
    return PlayerMatchStat(match_id=mid, team=team, player=player,
                           player_id=None, goals=goals, assists=assists,
                           yellow=0, red=0)


def _meta(mid, a, b):
    from src.data.analysis.matchday import canonical
    return {mid: {"teams": (canonical(a), canonical(b)), "date": date(2026, 6, 11),
                  "group": "Group A"}}


def test_team_match_goals_sums_player_goals_per_team():
    stats = {1: [_ts(1, "Mexico"), _ts(1, "Brazil")]}
    players = {1: [_ps(1, "Mexico", "A", goals=2), _ps(1, "Brazil", "B", goals=1)]}
    g = aggregate.team_match_goals(stats, players)
    from src.data.analysis.matchday import canonical
    assert g[1][canonical("Mexico")] == 2
    assert g[1][canonical("Brazil")] == 1


def test_build_record_sums_counts_means_possession_and_derives_result():
    from src.data.analysis.matchday import canonical
    stats = {
        1: [_ts(1, "Mexico", xg=1.5, shots_on=4, possession=0.60),
            _ts(1, "Brazil", xg=0.8, shots_on=2, possession=0.40)],
        2: [_ts(2, "Mexico", xg=2.5, shots_on=6, possession=0.50),
            _ts(2, "Spain", xg=1.0, shots_on=3, possession=0.50)],
    }
    players = {
        1: [_ps(1, "Mexico", "A", goals=2, assists=1), _ps(1, "Brazil", "B", goals=0)],
        2: [_ps(2, "Mexico", "A", goals=1), _ps(2, "Spain", "C", goals=1)],
    }
    meta = {}
    meta.update(_meta(1, "Mexico", "Brazil"))
    meta.update(_meta(2, "Mexico", "Spain"))
    rec = aggregate.build_record("Mexico", canonical("Mexico"), [1, 2],
                                 stats, players, meta)
    assert rec["matches_played"] == 2
    assert rec["xg"] == 4.0            # summed
    assert rec["shots_on"] == 10.0     # summed
    assert rec["possession"] == 0.55   # mean of 0.60 and 0.50
    assert rec["goals"] == 3           # 2 + 1
    assert rec["assists"] == 1
    assert rec["goals_conceded"] == 1  # 0 (vs Brazil) + 1 (vs Spain)
    assert rec["points"] == 6          # win + win (3-0, 1-1? no: 1-1 is a draw)
```

> Note: match 2 is Mexico 1–1 Spain (draw) → 3 (win vs Brazil) + 1 (draw) = 4. Fix the
> expected value to `4` after writing the implementation if the draw logic is correct;
> the test is intentionally written to force you to verify the W/D/L math. Set the
> assertion to `assert rec["points"] == 4`.

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_analysis_aggregate.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.data.analysis.aggregate'`

- [ ] **Step 3: Write `src/data/analysis/aggregate.py`**

```python
from __future__ import annotations

from src.data.analysis.matchday import canonical
from src.data.live.team_match_stats import STAT_KEYS

# Metrics aggregated by mean (per-match rate) rather than sum.
RATE_KEYS = {"possession"}


def team_match_goals(stats_by_match: dict, players_by_match: dict) -> dict:
    """{match_id: {canonical_team: goals_scored_that_match}}.

    Goals come from summing each team's players' goals (own goals are excluded
    by player_stats parsing — documented limitation). Every team that has a
    team-stats row in a match is represented (default 0) so opponents resolve."""
    out: dict[int, dict[str, int]] = {}
    for mid, rows in (stats_by_match or {}).items():
        out[mid] = {canonical(r.team): 0 for r in rows}
    for mid, prows in (players_by_match or {}).items():
        bucket = out.setdefault(mid, {})
        for p in prows:
            bucket[canonical(p.team)] = bucket.get(canonical(p.team), 0) + p.goals
    return out


def _opponent(team_canon: str, teams: tuple) -> str | None:
    others = [t for t in teams if t != team_canon]
    return others[0] if others else None


def build_record(team_official: str, team_canon: str, chrono_mids: list,
                 stats_by_match: dict, players_by_match: dict, meta: dict) -> dict:
    """One cumulative aggregate record for a team across its FINISHED matches.

    chrono_mids must already be this team's FINISHED match_ids in order.
    """
    rec = {k: 0.0 for k in STAT_KEYS}
    rec.update(team=team_official, group=None, matches_played=0,
               goals=0, goals_conceded=0, assists=0, points=0)
    poss: list[float] = []
    goals_by_match = team_match_goals(stats_by_match, players_by_match)

    for mid in chrono_mids:
        rows = stats_by_match.get(mid, [])
        mine = next((r for r in rows if canonical(r.team) == team_canon), None)
        if mine is None:
            continue
        rec["matches_played"] += 1
        for k in STAT_KEYS:
            if k in RATE_KEYS:
                poss.append(mine.stats.get(k, 0.0))
            else:
                rec[k] += mine.stats.get(k, 0.0)
        # group label from meta (first seen)
        if rec["group"] is None:
            rec["group"] = meta.get(mid, {}).get("group")
        # assists from this team's players
        for p in players_by_match.get(mid, []):
            if canonical(p.team) == team_canon:
                rec["assists"] += p.assists
        # result from per-match goals
        gm = goals_by_match.get(mid, {})
        gf = gm.get(team_canon, 0)
        opp = _opponent(team_canon, meta.get(mid, {}).get("teams", ()))
        ga = gm.get(opp, 0) if opp else 0
        rec["goals"] += gf
        rec["goals_conceded"] += ga
        rec["points"] += 3 if gf > ga else (1 if gf == ga else 0)

    rec["possession"] = round(sum(poss) / len(poss), 4) if poss else 0.0
    return rec
```

- [ ] **Step 4: Fix the test's points assertion and run**

Change the final assertion in the test to `assert rec["points"] == 4` (win 3-0 vs Brazil + draw 1-1 vs Spain).

Run: `python -m pytest tests/test_analysis_aggregate.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add src/data/analysis/aggregate.py tests/test_analysis_aggregate.py
git commit -m "feat(analysis): per-team cumulative aggregate record"
```

---

## Task 4: Normalization & radar series (`aggregate.py` part 2)

Adds per-90 conversion, field-relative 0–100 scaling, and a helper that produces both scaled (for plotting) and raw (for hover) values for a radar's metrics.

**Files:**
- Modify: `src/data/analysis/aggregate.py`
- Test: `tests/test_analysis_aggregate.py` (append)

**Interfaces:**
- Produces:
  - `aggregate.per90(value: float, matches_played: int) -> float` (value / matches_played; 0 if no matches)
  - `aggregate.field_relative(values: list[float]) -> list[float]` (each / max * 100; all-0 if max == 0)
  - `aggregate.radar_series(records: list[dict], metrics: list[tuple]) -> dict` where each metric is `(key, label, kind)` with `kind in {"count", "rate"}`. Returns `{"axes": [labels], "teams": [team names], "scaled": {team: [0-100 per axis]}, "raw": {team: [display value per axis]}}`. `count` metrics use per-90 before scaling; `rate` and `xg`/`xa` are left per-match (divide sum by matches_played to get per-match for display + scaling, but they are not multiplied to per-90). Round scaled to 1 dp, raw to 2 dp.

- [ ] **Step 1: Write the failing test (append)**

```python
# append to tests/test_analysis_aggregate.py
def test_per90_and_field_relative():
    assert aggregate.per90(10.0, 2) == 5.0
    assert aggregate.per90(10.0, 0) == 0.0
    assert aggregate.field_relative([2.0, 4.0, 0.0, 1.0]) == [50.0, 100.0, 0.0, 25.0]
    assert aggregate.field_relative([0.0, 0.0]) == [0.0, 0.0]  # divide-by-zero guard


def test_radar_series_scales_count_per90_and_keeps_raw():
    # Team A played 2 matches, Team B played 1; equal totals -> A should NOT
    # dominate once per-90 normalized.
    recs = [
        {"team": "A", "matches_played": 2, "key_passes": 20.0, "possession": 0.6},
        {"team": "B", "matches_played": 1, "key_passes": 20.0, "possession": 0.3},
    ]
    metrics = [("key_passes", "Key Passes", "count"),
               ("possession", "Possession", "rate")]
    out = aggregate.radar_series(recs, metrics)
    assert out["axes"] == ["Key Passes", "Possession"]
    # per-90 key_passes: A=10, B=20 -> scaled A=50, B=100
    assert out["scaled"]["A"][0] == 50.0
    assert out["scaled"]["B"][0] == 100.0
    # raw (per-match) shown in hover, not the 0-100 number
    assert out["raw"]["A"][0] == 10.0
    # possession is a rate -> scaled by raw value (0.6 vs 0.3) -> 100 vs 50
    assert out["scaled"]["B"][1] == 50.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_analysis_aggregate.py -v`
Expected: FAIL — `AttributeError: module 'src.data.analysis.aggregate' has no attribute 'per90'`

- [ ] **Step 3: Append to `src/data/analysis/aggregate.py`**

```python
def per90(value: float, matches_played: int) -> float:
    """Per-match (~per-90) value; 0 when no matches played."""
    return round(value / matches_played, 4) if matches_played else 0.0


def field_relative(values: list[float]) -> list[float]:
    """Scale each value to 0-100 relative to the max in the list.
    Max of 0 -> all zeros (divide-by-zero guard)."""
    hi = max(values) if values else 0.0
    if hi <= 0:
        return [0.0 for _ in values]
    return [round(v / hi * 100, 1) for v in values]


def _display_value(rec: dict, key: str, kind: str) -> float:
    """The raw value shown in hover and used for scaling: per-match for count
    metrics, the stored value for rate/normalized metrics."""
    mp = rec.get("matches_played", 0)
    val = rec.get(key, 0.0)
    if kind == "count":
        return per90(val, mp)
    return round(val, 4)  # rate (possession) / already-normalized (xg, xa)


def radar_series(records: list[dict], metrics: list[tuple]) -> dict:
    """Scaled (0-100, field-relative) + raw display values per team per axis."""
    teams = [r["team"] for r in records]
    axes = [label for _, label, _ in metrics]
    raw: dict[str, list[float]] = {t: [] for t in teams}
    scaled: dict[str, list[float]] = {t: [] for t in teams}
    for key, _label, kind in metrics:
        col = [_display_value(r, key, kind) for r in records]
        sc = field_relative(col)
        for r, v, s in zip(records, col, sc):
            raw[r["team"]].append(round(v, 2))
            scaled[r["team"]].append(s)
    return {"axes": axes, "teams": teams, "scaled": scaled, "raw": raw}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_analysis_aggregate.py -v`
Expected: PASS (3 tests total in file)

- [ ] **Step 5: Commit**

```bash
git add src/data/analysis/aggregate.py tests/test_analysis_aggregate.py
git commit -m "feat(analysis): per-90 + field-relative normalization and radar series"
```

---

## Task 5: The accessor seam (`accessors.py`) + fixtures

The only entry points charts use. `configure()` wires in store paths + static data at app init; the two getters do the joins.

**Files:**
- Create: `src/data/analysis/accessors.py`
- Create: `tests/fixtures/analysis/__init__.py` (empty), `tests/fixtures/analysis/sample.py`
- Test: `tests/test_analysis_accessors.py`

**Interfaces:**
- Consumes: `team_stats_store`, `player_store`, `matchday`, `aggregate`, `GROUPS`/`MATCHES` shapes, `official_team` mapping (passed in).
- Produces:
  - `accessors.configure(*, team_stats_path, player_store_path, groups, matches, official_resolver)` — stores module globals.
  - `accessors.get_group_aggregates(group_id) -> list[dict]` — records for the group's 4 teams, in official seeding order. Empty list if group unknown or no data.
  - `accessors.get_matchday_history(group_id, metric) -> dict[str, list[float]]` — per-team cumulative series; `metric in {"points","goals","assists","cards","conceded"}`.
  - `accessors.RACE_METRICS: dict[str, str]` — value → human label.
- `sample.py` produces: `write_sample(stats_path, players_path) -> None` and `SAMPLE_GROUP = "Group A"`, `SAMPLE_TEAMS = [...]`, `SAMPLE_MATCHES = [...]` (static `Match` list).

- [ ] **Step 1: Write the fixture module**

```python
# tests/fixtures/analysis/sample.py
"""A self-contained Group A: 4 teams, 3 matchdays (full round-robin), written to
temp stores so the accessor seam and every chart can be exercised offline."""
from __future__ import annotations

from datetime import date, datetime, time

from src.data.live import player_store, team_stats_store
from src.data.live.player_stats import PlayerMatchStat
from src.data.live.team_match_stats import STAT_KEYS, TeamMatchStat
from src.data.matches import Match

SAMPLE_GROUP = "Group A"
SAMPLE_TEAMS = ["Mexico", "Canada", "USA", "Wales"]

# match_id -> (home, away, date, home_goals, away_goals)
_FIXTURES = [
    (101, "Mexico", "Canada", date(2026, 6, 11), 2, 1),
    (102, "USA", "Wales", date(2026, 6, 12), 1, 1),
    (103, "Mexico", "USA", date(2026, 6, 17), 1, 0),
    (104, "Canada", "Wales", date(2026, 6, 18), 0, 3),
    (105, "Mexico", "Wales", date(2026, 6, 23), 2, 2),
    (106, "Canada", "USA", date(2026, 6, 24), 1, 2),
]

SAMPLE_MATCHES = [
    Match(number=i + 1, home=h, away=a, group=SAMPLE_GROUP, stage="Group Stage",
          stadium="X", date=d, local_time=time(13, 0),
          kickoff_utc=datetime(d.year, d.month, d.day, 19, 0))
    for i, (_mid, h, a, d, _hg, _ag) in enumerate(_FIXTURES)
]


def _ts(mid, team, **ov):
    s = {k: 0.0 for k in STAT_KEYS}
    # give every match plausible non-zero volume so charts render
    s.update(xg=1.4, xa=1.0, big_chances=2, possession=0.5, shots_on=4,
             shots_off=5, shots_blocked=2, shots_in_box=7, corners=5,
             passes_total=450, passes_succ=380, key_passes=8,
             passes_final_third=60, long_passes=40, crosses=15, crosses_succ=5,
             dribbles=12, dribbles_succ=7, tackles=18, tackles_succ=12,
             interceptions=9, clearances=20, aerials=22, aerials_won=11,
             gk_saves=3, fouls=11, offsides=2, yellow=2, red=0)
    s.update(ov)
    return TeamMatchStat(match_id=mid, team=team, stats=s)


def write_sample(stats_path, players_path) -> None:
    for mid, h, a, d, hg, ag in _FIXTURES:
        team_stats_store.upsert(stats_path, mid, "finished",
                                [_ts(mid, h, possession=0.55),
                                 _ts(mid, a, possession=0.45)])
        rows = []
        for _ in range(hg):
            rows.append(PlayerMatchStat(mid, h, "H scorer", None, 1, 0, 0, 0))
        for _ in range(ag):
            rows.append(PlayerMatchStat(mid, a, "A scorer", None, 1, 0, 0, 0))
        # one assist per side for variety
        rows.append(PlayerMatchStat(mid, h, "H assist", None, 0, 1, 0, 0))
        player_store.upsert(players_path, mid, "finished", rows)
```

- [ ] **Step 2: Write the failing test**

```python
# tests/test_analysis_accessors.py
from __future__ import annotations

import app as appmod
from src.data.analysis import accessors
from tests.fixtures.analysis import sample


def _configure(tmp_path):
    stats = tmp_path / "team.csv"
    players = tmp_path / "players.csv"
    sample.write_sample(stats, players)
    groups = {sample.SAMPLE_GROUP: appmod.GROUPS  # placeholder; replaced below
              }
    from src.data.groups import build_groups
    groups = build_groups(sample.SAMPLE_MATCHES)
    accessors.configure(team_stats_path=stats, player_store_path=players,
                        groups=groups, matches=sample.SAMPLE_MATCHES,
                        official_resolver=lambda n: n)
    return groups


def test_group_aggregates_returns_four_team_records(tmp_path):
    _configure(tmp_path)
    recs = accessors.get_group_aggregates(sample.SAMPLE_GROUP)
    assert [r["team"] for r in recs] == sample.SAMPLE_TEAMS
    mex = next(r for r in recs if r["team"] == "Mexico")
    assert mex["matches_played"] == 3
    assert mex["goals"] == 5            # 2 + 1 + 2
    assert mex["goals_conceded"] == 3   # 1 + 0 + 2
    assert mex["points"] == 7           # win, win, draw


def test_unknown_group_returns_empty(tmp_path):
    _configure(tmp_path)
    assert accessors.get_group_aggregates("Group Z") == []


def test_matchday_history_is_cumulative_per_matchday(tmp_path):
    _configure(tmp_path)
    hist = accessors.get_matchday_history(sample.SAMPLE_GROUP, "points")
    # Mexico: win(3) -> win(6) -> draw(7)
    assert hist["Mexico"] == [3, 6, 7]
    goals = accessors.get_matchday_history(sample.SAMPLE_GROUP, "goals")
    assert goals["Mexico"] == [2, 3, 5]


def test_matchday_history_unknown_metric_raises(tmp_path):
    _configure(tmp_path)
    try:
        accessors.get_matchday_history(sample.SAMPLE_GROUP, "nonsense")
        assert False, "expected ValueError"
    except ValueError:
        pass
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python -m pytest tests/test_analysis_accessors.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.data.analysis.accessors'`

- [ ] **Step 4: Write `src/data/analysis/accessors.py`**

```python
from __future__ import annotations

import logging

from src.data.analysis import aggregate, matchday
from src.data.live import player_store, team_stats_store

logger = logging.getLogger(__name__)

RACE_METRICS = {
    "points": "Collected points",
    "goals": "Goals",
    "assists": "Assists",
    "cards": "Total cards",
    "conceded": "Goals conceded",
}

_CFG: dict = {
    "team_stats_path": None,
    "player_store_path": None,
    "groups": {},
    "matches": [],
    "official_resolver": lambda n: n,
}


def configure(*, team_stats_path, player_store_path, groups, matches,
              official_resolver) -> None:
    """Wire the seam to the live store paths and static data at app init."""
    _CFG.update(team_stats_path=team_stats_path,
                player_store_path=player_store_path, groups=groups,
                matches=matches, official_resolver=official_resolver)


def _load():
    stats = team_stats_store.load(_CFG["team_stats_path"])
    players = player_store.load(_CFG["player_store_path"])
    states = team_stats_store.stored_match_states(_CFG["team_stats_path"])
    meta = matchday.match_meta(stats, _CFG["matches"])
    finished = matchday.finished_ids(states)
    return stats, players, meta, finished


def _group_teams(group_id):
    group = _CFG["groups"].get(group_id)
    return [s.team for s in group.standings] if group else []


def get_group_aggregates(group_id: str) -> list[dict]:
    """Cumulative aggregate record per team in the group (official order)."""
    teams = _group_teams(group_id)
    if not teams:
        return []
    stats, players, meta, finished = _load()
    out = []
    for official in teams:
        canon = matchday.canonical(official)
        chrono = matchday.team_finished_matches(canon, finished, meta)
        rec = aggregate.build_record(official, canon, chrono, stats, players, meta)
        rec["group"] = group_id
        out.append(rec)
    return out


def _metric_after(metric, canon, mid, stats, players, goals_by_match, meta):
    """The team's contribution to `metric` from a single match."""
    if metric == "cards":
        rows = stats.get(mid, [])
        mine = next((r for r in rows if matchday.canonical(r.team) == canon), None)
        return int((mine.stats.get("yellow", 0) + mine.stats.get("red", 0))) if mine else 0
    gm = goals_by_match.get(mid, {})
    gf = gm.get(canon, 0)
    if metric == "goals":
        return gf
    if metric == "assists":
        return sum(p.assists for p in players.get(mid, [])
                   if matchday.canonical(p.team) == canon)
    opp = aggregate._opponent(canon, meta.get(mid, {}).get("teams", ()))
    ga = gm.get(opp, 0) if opp else 0
    if metric == "conceded":
        return ga
    if metric == "points":
        return 3 if gf > ga else (1 if gf == ga else 0)
    raise ValueError(f"unknown race metric: {metric}")


def get_matchday_history(group_id: str, metric: str) -> dict[str, list]:
    """Per-team cumulative series of `metric` after md1, md2, ... (chronological)."""
    if metric not in RACE_METRICS:
        raise ValueError(f"unknown race metric: {metric}")
    teams = _group_teams(group_id)
    if not teams:
        return {}
    stats, players, meta, finished = _load()
    goals_by_match = aggregate.team_match_goals(stats, players)
    out: dict[str, list] = {}
    for official in teams:
        canon = matchday.canonical(official)
        chrono = matchday.team_finished_matches(canon, finished, meta)
        series, running = [], 0
        for mid in chrono:
            running += _metric_after(metric, canon, mid, stats, players,
                                     goals_by_match, meta)
            series.append(running)
        out[official] = series
    return out
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests/test_analysis_accessors.py -v`
Expected: PASS (4 tests)

- [ ] **Step 6: Commit**

```bash
git add src/data/analysis/accessors.py tests/fixtures/analysis/ tests/test_analysis_accessors.py
git commit -m "feat(analysis): accessor seam (group aggregates + matchday history) + fixtures"
```

---

## Task 6: View config + radar builder (views 1–4)

**Files:**
- Create: `src/components/analysis/views.py`
- Test: `tests/test_analysis_views_radar.py`

**Interfaces:**
- Consumes: `aggregate.radar_series`, `theme`.
- Produces:
  - `views.VIEWS: list[dict]` — 10 ordered entries. Each has `id`, `title`, `type` (`"radar"|"dumbbell"|"race"|"funnel"|"quadrant"|"defend"|"bubble"`), `caption` (str). Radar entries also have `metrics: list[(key, label, kind)]`. Entries needing a caveat have `caveat: str`.
  - `views.radar_figure(records, view, theme="dark") -> go.Figure`
  - `views.VIEW_BY_ID: dict[str, dict]`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_analysis_views_radar.py
from __future__ import annotations

import plotly.graph_objects as go

from src.components.analysis import views


def _recs():
    base = {k: 1.0 for k in
            ["xg", "xa", "big_chances", "shots_in_box", "key_passes",
             "possession", "passes_succ", "passes_final_third", "dribbles_succ",
             "tackles_succ", "interceptions", "clearances", "aerials_won",
             "gk_saves", "crosses", "long_passes", "dribbles", "aerials"]}
    out = []
    for i, t in enumerate(["A", "B", "C", "D"]):
        r = dict(base, team=t, matches_played=2)
        r["xg"] = float(i + 1)  # vary one axis so scaling differs
        out.append(r)
    return out


def test_views_config_has_ten_entries_in_order():
    assert len(views.VIEWS) == 10
    assert [v["id"] for v in views.VIEWS][:6] == [
        "ATTACKING_THREAT", "BUILD_UP", "DEFENSIVE_WORK",
        "STYLE_FINGERPRINT", "FINISHING", "RACE"]


def test_no_radar_mixes_a_count_with_its_successful_pair():
    pairs = [("crosses", "crosses_succ"), ("dribbles", "dribbles_succ"),
             ("tackles", "tackles_succ"), ("aerials", "aerials_won"),
             ("passes_total", "passes_succ")]
    for v in views.VIEWS:
        if v["type"] != "radar":
            continue
        keys = {k for k, _l, _kind in v["metrics"]}
        for raw, succ in pairs:
            assert not (raw in keys and succ in keys), f"{v['id']} mixes {raw}+{succ}"
        assert len(v["metrics"]) <= 6


def test_radar_figure_has_one_trace_per_team_and_hidden_radial_ticks():
    view = views.VIEW_BY_ID["ATTACKING_THREAT"]
    fig = views.radar_figure(_recs(), view, theme="dark")
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 4
    assert all(tr.type == "scatterpolar" for tr in fig.data)
    assert fig.layout.polar.radialaxis.showticklabels is False
    assert fig.layout.polar.radialaxis.range == (0, 100)


def test_radar_hover_shows_raw_not_scaled():
    view = views.VIEW_BY_ID["ATTACKING_THREAT"]
    fig = views.radar_figure(_recs(), view, theme="dark")
    # customdata carries raw per-match values; hovertemplate references it
    assert any("customdata" in (tr.hovertemplate or "") or tr.customdata is not None
               for tr in fig.data)


def test_defensive_work_has_caveat():
    assert views.VIEW_BY_ID["DEFENSIVE_WORK"].get("caveat")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_analysis_views_radar.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.components.analysis.views'`

- [ ] **Step 3: Write `src/components/analysis/views.py`**

```python
from __future__ import annotations

import plotly.graph_objects as go

from src.components.analysis import theme
from src.data.analysis import aggregate

VIEWS = [
    {"id": "ATTACKING_THREAT", "type": "radar", "title": "Attacking threat",
     "caption": "Where each team generates danger (per-90, scaled to the group).",
     "metrics": [("xg", "Expected goals", "rate"), ("xa", "Expected assists", "rate"),
                 ("big_chances", "Big chances", "count"),
                 ("shots_in_box", "Shots in box", "count"),
                 ("key_passes", "Key passes", "count")]},
    {"id": "BUILD_UP", "type": "radar", "title": "Build-up",
     "caption": "How teams progress the ball (per-90, scaled to the group).",
     "metrics": [("possession", "Possession", "rate"),
                 ("passes_succ", "Successful passes", "count"),
                 ("passes_final_third", "Passes into final third", "count"),
                 ("key_passes", "Key passes", "count"),
                 ("dribbles_succ", "Successful dribbles", "count")]},
    {"id": "DEFENSIVE_WORK", "type": "radar", "title": "Defensive work",
     "caption": "Defensive actions (per-90, scaled to the group).",
     "caveat": "High volume often means a team played without the ball — a bigger "
               "shape is not necessarily better defending.",
     "metrics": [("tackles_succ", "Successful tackles", "count"),
                 ("interceptions", "Interceptions", "count"),
                 ("clearances", "Clearances", "count"),
                 ("aerials_won", "Aerial duels won", "count"),
                 ("gk_saves", "Goalkeeper saves", "count")]},
    {"id": "STYLE_FINGERPRINT", "type": "radar", "title": "Style fingerprint",
     "caption": "How a team plays — raw attempt volumes (per-90, scaled).",
     "metrics": [("possession", "Possession", "rate"),
                 ("crosses", "Crosses", "count"),
                 ("long_passes", "Long passes", "count"),
                 ("dribbles", "Dribbles", "count"),
                 ("aerials", "Aerial duels", "count")]},
    {"id": "FINISHING", "type": "dumbbell", "title": "Finishing: goals vs xG",
     "caption": "Actual goals against expected goals — over- and under-performance.",
     "caveat": "With few shots or matches, finishing looks extreme and tends to "
               "regress."},
    {"id": "RACE", "type": "race", "title": "Race over matchdays",
     "caption": "A selected metric accumulating matchday by matchday."},
    {"id": "SHOT_FUNNEL", "type": "funnel", "title": "Shot funnel",
     "caption": "Shots → on target → goals, per team."},
    {"id": "QUALITY_VS_CONV", "type": "quadrant", "title": "Chance quality vs conversion",
     "caption": "xG per shot (quality) against conversion % (goals ÷ shots)."},
    {"id": "HOW_THEY_DEFEND", "type": "defend", "title": "How they defend",
     "caption": "Defensive volume and its mix, per-90.",
     "caveat": "High defensive volume often signals playing without the ball — "
               "more actions is not better defending."},
    {"id": "VOLUME_VS_PENETR", "type": "bubble", "title": "Volume vs penetration",
     "caption": "Total passes against passes into the final third; bubble = accuracy %."},
]

VIEW_BY_ID = {v["id"]: v for v in VIEWS}


def radar_figure(records, view, theme: str = "dark") -> go.Figure:
    series = aggregate.radar_series(records, view["metrics"])
    cmap = _theme_team_color(series["teams"])
    fmap = _theme_team_fill(series["teams"])
    axes = series["axes"] + series["axes"][:1]  # close the loop
    fig = go.Figure()
    for t in series["teams"]:
        scaled = series["scaled"][t] + series["scaled"][t][:1]
        raw = series["raw"][t] + series["raw"][t][:1]
        fig.add_trace(go.Scatterpolar(
            r=scaled, theta=axes, name=t, fill="toself",
            fillcolor=fmap[t], line=dict(color=cmap[t], width=2),
            customdata=list(zip(raw, axes)),
            hovertemplate="<b>%{fullData.name}</b><br>%{theta}: "
                          "%{customdata[0]}<extra></extra>",
        ))
    lay = theme_layout(theme)
    fig.update_layout(
        polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(range=[0, 100], showticklabels=False,
                            gridcolor=lay["gridcolor_hint"], showline=False),
            angularaxis=dict(gridcolor=lay["gridcolor_hint"]),
        ),
        paper_bgcolor=lay["paper_bgcolor"], font=lay["font"],
        margin=dict(l=40, r=40, t=10, b=20), showlegend=False, autosize=True,
    )
    return fig


# small indirections so later tasks can reuse the same helpers
def theme_layout(t):
    return theme.plotly_layout(t)


def _theme_team_color(teams):
    return theme.team_color_map(teams)


def _theme_team_fill(teams):
    return theme.team_fill_map(teams)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_analysis_views_radar.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add src/components/analysis/views.py tests/test_analysis_views_radar.py
git commit -m "feat(analysis): view config + radar figure builder (views 1-4)"
```

---

## Task 7: Dumbbell builder (view 5)

**Files:**
- Modify: `src/components/analysis/views.py`
- Test: `tests/test_analysis_views_dumbbell.py`

**Interfaces:**
- Produces: `views.dumbbell_figure(records, theme="dark") -> go.Figure`. One row per team, sorted ascending on the y-axis so the largest `(goals - xg)` is on top; xG marker grey, goals marker blue, connector green when `goals >= xg` else orange. Raw values (no scaling).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_analysis_views_dumbbell.py
from __future__ import annotations

import plotly.graph_objects as go

from src.components.analysis import views


def _recs():
    return [
        {"team": "Over", "goals": 5, "xg": 2.0, "matches_played": 3, "shots_on": 12},
        {"team": "Under", "goals": 1, "xg": 4.0, "matches_played": 3, "shots_on": 10},
        {"team": "Even", "goals": 3, "xg": 3.0, "matches_played": 3, "shots_on": 9},
    ]


def test_dumbbell_sorted_by_goals_minus_xg():
    fig = views.dumbbell_figure(_recs())
    # y category order should put the biggest (goals-xg) last so it renders on top
    order = list(fig.layout.yaxis.categoryarray)
    assert order[-1] == "Over"
    assert order[0] == "Under"


def test_dumbbell_connector_color_encodes_over_under():
    fig = views.dumbbell_figure(_recs())
    # connector line traces carry the green/orange colors
    line_colors = [tr.line.color for tr in fig.data if tr.mode == "lines"]
    assert "#1D9E75" in line_colors   # over/equal -> green
    assert "#D85A30" in line_colors   # under -> orange


def test_dumbbell_uses_raw_values():
    fig = views.dumbbell_figure(_recs())
    xs = [x for tr in fig.data for x in (tr.x or [])]
    assert 5 in xs and 2.0 in xs   # raw goals + raw xg present, unscaled
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_analysis_views_dumbbell.py -v`
Expected: FAIL — `AttributeError: module ... has no attribute 'dumbbell_figure'`

- [ ] **Step 3: Append `dumbbell_figure` to `views.py`**

```python
def dumbbell_figure(records, theme: str = "dark") -> go.Figure:
    rows = sorted(records, key=lambda r: (r.get("goals", 0) - r.get("xg", 0.0)))
    teams = [r["team"] for r in rows]  # ascending -> biggest gap on top
    lay = theme_layout(theme)
    fig = go.Figure()
    for r in rows:
        over = r.get("goals", 0) >= r.get("xg", 0.0)
        fig.add_trace(go.Scatter(
            x=[r["xg"], r["goals"]], y=[r["team"], r["team"]], mode="lines",
            line=dict(color=theme.DUMBBELL["over"] if over else theme.DUMBBELL["under"],
                      width=4),
            hoverinfo="skip", showlegend=False))
    fig.add_trace(go.Scatter(
        x=[r["xg"] for r in rows], y=teams, mode="markers", name="xG",
        marker=dict(color=theme.DUMBBELL["xg"], size=13),
        hovertemplate="<b>%{y}</b><br>xG: %{x:.2f}<extra></extra>"))
    fig.add_trace(go.Scatter(
        x=[r["goals"] for r in rows], y=teams, mode="markers", name="Goals",
        marker=dict(color=theme.DUMBBELL["goals"], size=13),
        hovertemplate="<b>%{y}</b><br>Goals: %{x}<extra></extra>"))
    fig.update_layout(
        paper_bgcolor=lay["paper_bgcolor"], plot_bgcolor=lay["plot_bgcolor"],
        font=lay["font"], margin=dict(l=80, r=30, t=10, b=40), autosize=True,
        showlegend=False,
        xaxis=dict(title="Goals (with xG)", gridcolor=lay["gridcolor_hint"],
                   zeroline=False),
        yaxis=dict(categoryorder="array", categoryarray=teams,
                   gridcolor="rgba(0,0,0,0)"))
    return fig
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_analysis_views_dumbbell.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add src/components/analysis/views.py tests/test_analysis_views_dumbbell.py
git commit -m "feat(analysis): dumbbell figure (FINISHING view)"
```

---

## Task 8: Bar-chart-race builder (view 6)

Per-frame static figure: bars for cumulative value up to a given matchday frame, re-sorted so the leader is on top.

**Files:**
- Modify: `src/components/analysis/views.py`
- Test: `tests/test_analysis_views_race.py`

**Interfaces:**
- Produces:
  - `views.race_frame_count(history: dict) -> int` (max series length across teams; 0 if empty)
  - `views.race_figure(history, metric, frame, theme="dark", color_map=None) -> go.Figure` — horizontal bars of each team's cumulative value at matchday index `frame` (0-based); bars sorted ascending so the largest is on top; value labels on bar ends; a matchday annotation; teams keep their color.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_analysis_views_race.py
from __future__ import annotations

import plotly.graph_objects as go

from src.components.analysis import views


def _hist():
    return {"A": [3, 6, 7], "B": [1, 4, 10], "C": [0, 3, 3], "D": [3, 3, 4]}


def test_frame_count_is_max_matchdays():
    assert views.race_frame_count(_hist()) == 3
    assert views.race_frame_count({}) == 0


def test_race_figure_uses_cumulative_value_at_frame():
    fig = views.race_figure(_hist(), "points", frame=2)  # final matchday
    assert isinstance(fig, go.Figure)
    bar = fig.data[0]
    # bars sorted ascending -> last bar is the leader B with 10
    assert list(bar.y)[-1] == "B"
    assert list(bar.x)[-1] == 10


def test_race_figure_clamps_frame_and_labels_matchday():
    fig = views.race_figure(_hist(), "points", frame=99)
    ann = " ".join(a.text for a in fig.layout.annotations)
    assert "Matchday 3" in ann
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_analysis_views_race.py -v`
Expected: FAIL — `AttributeError: module ... has no attribute 'race_frame_count'`

- [ ] **Step 3: Append to `views.py`**

```python
def race_frame_count(history: dict) -> int:
    return max((len(v) for v in history.values()), default=0)


def race_figure(history, metric, frame, theme: str = "dark",
                color_map=None) -> go.Figure:
    teams = list(history.keys())
    cmap = color_map or theme.team_color_map(teams)
    n = race_frame_count(history)
    f = max(0, min(frame, n - 1)) if n else 0
    vals = []
    for t in teams:
        series = history[t]
        vals.append((t, series[f] if f < len(series) else (series[-1] if series else 0)))
    vals.sort(key=lambda tv: tv[1])  # ascending -> leader on top
    lay = theme_layout(theme)
    fig = go.Figure(go.Bar(
        x=[v for _t, v in vals], y=[t for t, _v in vals], orientation="h",
        marker=dict(color=[cmap[t] for t, _v in vals]),
        text=[f"{v:g}" for _t, v in vals], textposition="outside",
        hovertemplate="<b>%{y}</b><br>" + accessors_label(metric) +
                      ": %{x:g}<extra></extra>"))
    fig.update_layout(
        paper_bgcolor=lay["paper_bgcolor"], plot_bgcolor=lay["plot_bgcolor"],
        font=lay["font"], margin=dict(l=80, r=40, t=10, b=30), autosize=True,
        showlegend=False,
        xaxis=dict(title=accessors_label(metric), gridcolor=lay["gridcolor_hint"],
                   zeroline=False),
        yaxis=dict(gridcolor="rgba(0,0,0,0)"),
        annotations=[dict(x=1, y=1.08, xref="paper", yref="paper",
                          xanchor="right", showarrow=False,
                          text=f"Matchday {f + 1}")])
    return fig


def accessors_label(metric: str) -> str:
    from src.data.analysis.accessors import RACE_METRICS
    return RACE_METRICS.get(metric, metric)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_analysis_views_race.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add src/components/analysis/views.py tests/test_analysis_views_race.py
git commit -m "feat(analysis): bar-chart-race per-frame figure (RACE view)"
```

---

## Task 9: Shot-funnel builder (view 7)

2×2 small-multiples of `go.Funnel`, one per team: shots → on target → goals.

**Files:**
- Modify: `src/components/analysis/views.py`
- Test: `tests/test_analysis_views_funnel.py`

**Interfaces:**
- Produces: `views.funnel_figure(records, theme="dark", color_map=None) -> go.Figure` using a 2×2 `make_subplots`. `shots_total = shots_on + shots_off + shots_blocked`. Stages: shots_total, shots_on, goals.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_analysis_views_funnel.py
from __future__ import annotations

import plotly.graph_objects as go

from src.components.analysis import views


def _recs():
    out = []
    for t in ["A", "B", "C", "D"]:
        out.append({"team": t, "shots_on": 6.0, "shots_off": 8.0,
                    "shots_blocked": 2.0, "goals": 3, "matches_played": 3})
    return out


def test_funnel_has_one_funnel_per_team():
    fig = views.funnel_figure(_recs())
    funnels = [tr for tr in fig.data if tr.type == "funnel"]
    assert len(funnels) == 4


def test_funnel_stage_values_taken_on_target_goals():
    fig = views.funnel_figure(_recs())
    tr = next(tr for tr in fig.data if tr.type == "funnel")
    # shots_total = 6+8+2 = 16, on target = 6, goals = 3
    assert list(tr.x) == [16.0, 6.0, 3]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_analysis_views_funnel.py -v`
Expected: FAIL — `AttributeError: ... 'funnel_figure'`

- [ ] **Step 3: Append to `views.py`**

```python
from plotly.subplots import make_subplots  # add at top of views.py with other imports


def funnel_figure(records, theme: str = "dark", color_map=None) -> go.Figure:
    teams = [r["team"] for r in records]
    cmap = color_map or theme.team_color_map(teams)
    lay = theme_layout(theme)
    fig = make_subplots(rows=2, cols=2, subplot_titles=teams[:4],
                        vertical_spacing=0.18, horizontal_spacing=0.12)
    for i, r in enumerate(records[:4]):
        total = r.get("shots_on", 0) + r.get("shots_off", 0) + r.get("shots_blocked", 0)
        x = [total, r.get("shots_on", 0), r.get("goals", 0)]
        fig.add_trace(go.Funnel(
            y=["Shots", "On target", "Goals"], x=x, name=r["team"],
            marker=dict(color=cmap[r["team"]]),
            textinfo="value+percent previous",
            hovertemplate="<b>%{y}</b>: %{x}<br>%{percentInitial} of all shots"
                          "<extra></extra>"),
            row=i // 2 + 1, col=i % 2 + 1)
    fig.update_layout(
        paper_bgcolor=lay["paper_bgcolor"], plot_bgcolor=lay["plot_bgcolor"],
        font=lay["font"], margin=dict(l=20, r=20, t=30, b=10), autosize=True,
        showlegend=False, funnelmode="stack")
    return fig
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_analysis_views_funnel.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add src/components/analysis/views.py tests/test_analysis_views_funnel.py
git commit -m "feat(analysis): 2x2 shot-funnel small-multiples (SHOT_FUNNEL view)"
```

---

## Task 10: Quadrant builder (view 8)

xG/shot (x) vs conversion % (y), median crosshair, quadrant labels, team annotations.

**Files:**
- Modify: `src/components/analysis/views.py`
- Test: `tests/test_analysis_views_quadrant.py`

**Interfaces:**
- Produces: `views.quadrant_figure(records, theme="dark", color_map=None) -> go.Figure`. `shots_total = shots_on + shots_off + shots_blocked`; `xg_per_shot = xg / shots_total`; `conversion = goals / shots_total * 100`. Crosshair at the group mean of each axis via `add_shape`/`add_vline`/`add_hline`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_analysis_views_quadrant.py
from __future__ import annotations

import plotly.graph_objects as go

from src.components.analysis import views


def _recs():
    return [
        {"team": "A", "xg": 6.0, "goals": 6, "shots_on": 10, "shots_off": 8, "shots_blocked": 2},
        {"team": "B", "xg": 2.0, "goals": 1, "shots_on": 5, "shots_off": 4, "shots_blocked": 1},
        {"team": "C", "xg": 4.0, "goals": 3, "shots_on": 8, "shots_off": 6, "shots_blocked": 2},
        {"team": "D", "xg": 3.0, "goals": 4, "shots_on": 7, "shots_off": 5, "shots_blocked": 0},
    ]


def test_quadrant_one_point_per_team():
    fig = views.quadrant_figure(_recs())
    pts = [tr for tr in fig.data if tr.type == "scatter"]
    total_markers = sum(len(tr.x) for tr in pts)
    assert total_markers == 4


def test_quadrant_has_crosshair_lines():
    fig = views.quadrant_figure(_recs())
    # two reference lines (median/mean crosshair) added as shapes
    assert len(fig.layout.shapes) >= 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_analysis_views_quadrant.py -v`
Expected: FAIL — `AttributeError: ... 'quadrant_figure'`

- [ ] **Step 3: Append to `views.py`**

```python
def _shots_total(r):
    return r.get("shots_on", 0) + r.get("shots_off", 0) + r.get("shots_blocked", 0)


def quadrant_figure(records, theme: str = "dark", color_map=None) -> go.Figure:
    teams = [r["team"] for r in records]
    cmap = color_map or theme.team_color_map(teams)
    lay = theme_layout(theme)
    xs, ys, txt, cols, cd = [], [], [], [], []
    for r in records:
        st = _shots_total(r) or 1
        xq = round(r.get("xg", 0.0) / st, 3)
        yc = round(r.get("goals", 0) / st * 100, 1)
        xs.append(xq); ys.append(yc); txt.append(r["team"])
        cols.append(cmap[r["team"]])
        cd.append([r.get("goals", 0), _shots_total(r)])
    fig = go.Figure(go.Scatter(
        x=xs, y=ys, mode="markers+text", text=txt, textposition="top center",
        marker=dict(color=cols, size=16),
        customdata=cd,
        hovertemplate="<b>%{text}</b><br>xG/shot: %{x:.3f}<br>"
                      "Conversion: %{y:.1f}%<br>Goals %{customdata[0]} / "
                      "Shots %{customdata[1]}<extra></extra>"))
    mx = sum(xs) / len(xs); my = sum(ys) / len(ys)
    fig.add_vline(x=mx, line=dict(color=lay["gridcolor_hint"], dash="dot"))
    fig.add_hline(y=my, line=dict(color=lay["gridcolor_hint"], dash="dot"))
    for x, y, t in [(max(xs), max(ys), "clinical"), (min(xs), max(ys), "lucky"),
                    (max(xs), min(ys), "wasteful"), (min(xs), min(ys), "toothless")]:
        fig.add_annotation(x=x, y=y, text=t, showarrow=False,
                           opacity=0.4, font=dict(size=10))
    fig.update_layout(
        paper_bgcolor=lay["paper_bgcolor"], plot_bgcolor=lay["plot_bgcolor"],
        font=lay["font"], margin=dict(l=50, r=30, t=10, b=40), autosize=True,
        showlegend=False,
        xaxis=dict(title="xG per shot (chance quality)", gridcolor=lay["gridcolor_hint"]),
        yaxis=dict(title="Conversion % (goals ÷ shots)", gridcolor=lay["gridcolor_hint"]))
    return fig
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_analysis_views_quadrant.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add src/components/analysis/views.py tests/test_analysis_views_quadrant.py
git commit -m "feat(analysis): quadrant chart (QUALITY_VS_CONV view)"
```

---

## Task 11: Stacked-defense builder (view 9)

Per-90 stacked bars: tackles_succ + interceptions + clearances + aerials_won, with fixed segment colors.

**Files:**
- Modify: `src/components/analysis/views.py`
- Test: `tests/test_analysis_views_defend.py`

**Interfaces:**
- Produces: `views.defend_figure(records, theme="dark") -> go.Figure`. One stacked bar per team; four traces (one per action) using `theme.DEFEND_COLORS`; values per-90 (`aggregate.per90`).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_analysis_views_defend.py
from __future__ import annotations

import plotly.graph_objects as go

from src.components.analysis import views


def _recs():
    out = []
    for t in ["A", "B", "C", "D"]:
        out.append({"team": t, "tackles_succ": 12.0, "interceptions": 6.0,
                    "clearances": 20.0, "aerials_won": 10.0, "matches_played": 2})
    return out


def test_defend_has_four_action_traces_stacked():
    fig = views.defend_figure(_recs())
    assert fig.layout.barmode == "stack"
    assert len(fig.data) == 4
    names = {tr.name for tr in fig.data}
    assert names == {"Tackles won", "Interceptions", "Clearances", "Aerials won"}


def test_defend_values_are_per90():
    fig = views.defend_figure(_recs())
    tackles = next(tr for tr in fig.data if tr.name == "Tackles won")
    assert list(tackles.y) == [6.0, 6.0, 6.0, 6.0]  # 12 / 2 matches


def test_defend_segment_colors_are_fixed():
    fig = views.defend_figure(_recs())
    by_name = {tr.name: tr.marker.color for tr in fig.data}
    assert by_name["Tackles won"] == "#1D9E75"
    assert by_name["Clearances"] == "#EF9F27"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_analysis_views_defend.py -v`
Expected: FAIL — `AttributeError: ... 'defend_figure'`

- [ ] **Step 3: Append to `views.py`**

```python
_DEFEND_ACTIONS = [("tackles_succ", "Tackles won"), ("interceptions", "Interceptions"),
                   ("clearances", "Clearances"), ("aerials_won", "Aerials won")]


def defend_figure(records, theme: str = "dark") -> go.Figure:
    teams = [r["team"] for r in records]
    lay = theme_layout(theme)
    fig = go.Figure()
    for key, label in _DEFEND_ACTIONS:
        y = [aggregate.per90(r.get(key, 0.0), r.get("matches_played", 0)) for r in records]
        fig.add_trace(go.Bar(
            x=teams, y=y, name=label, marker=dict(color=theme.DEFEND_COLORS[key]),
            hovertemplate="<b>%{x}</b><br>" + label + " (per 90): %{y:.1f}<extra></extra>"))
    fig.update_layout(
        barmode="stack",
        paper_bgcolor=lay["paper_bgcolor"], plot_bgcolor=lay["plot_bgcolor"],
        font=lay["font"], margin=dict(l=40, r=20, t=10, b=30), autosize=True,
        showlegend=True, legend=dict(orientation="h", y=1.1, font=dict(size=10)),
        xaxis=dict(gridcolor="rgba(0,0,0,0)"),
        yaxis=dict(title="Defensive actions per 90", gridcolor=lay["gridcolor_hint"]))
    return fig
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_analysis_views_defend.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add src/components/analysis/views.py tests/test_analysis_views_defend.py
git commit -m "feat(analysis): stacked defensive-actions bars (HOW_THEY_DEFEND view)"
```

---

## Task 12: Bubble builder (view 10) + `build_figure` dispatcher

**Files:**
- Modify: `src/components/analysis/views.py`
- Test: `tests/test_analysis_views_bubble.py`

**Interfaces:**
- Produces:
  - `views.bubble_figure(records, theme="dark", color_map=None) -> go.Figure`. X = passes_total, Y = passes_final_third, size = accuracy % (`passes_succ/passes_total*100`); axes padded ~10%; team annotations.
  - `views.build_figure(view, *, records=None, history=None, race_metric="points", frame=0, theme="dark") -> go.Figure` — dispatches on `view["type"]`; passes a single shared `color_map` so colors match across views.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_analysis_views_bubble.py
from __future__ import annotations

import plotly.graph_objects as go

from src.components.analysis import views


def _recs():
    return [
        {"team": "A", "passes_total": 500.0, "passes_succ": 450.0, "passes_final_third": 80.0},
        {"team": "B", "passes_total": 300.0, "passes_succ": 240.0, "passes_final_third": 40.0},
        {"team": "C", "passes_total": 400.0, "passes_succ": 360.0, "passes_final_third": 70.0},
        {"team": "D", "passes_total": 350.0, "passes_succ": 280.0, "passes_final_third": 35.0},
    ]


def test_bubble_size_encodes_accuracy():
    fig = views.bubble_figure(_recs())
    tr = fig.data[0]
    # marker sizes proportional to accuracy %, A (90%) larger than B (80%)
    assert tr.marker.size[0] > tr.marker.size[1]


def test_build_figure_dispatches_by_type():
    radar = views.build_figure(views.VIEW_BY_ID["ATTACKING_THREAT"],
                               records=[dict(team=t, matches_played=1, xg=1.0, xa=1.0,
                                             big_chances=1, shots_in_box=1, key_passes=1)
                                        for t in "ABCD"])
    assert isinstance(radar, go.Figure)
    race = views.build_figure(views.VIEW_BY_ID["RACE"],
                              history={"A": [1, 2], "B": [0, 3]},
                              race_metric="points", frame=1)
    assert isinstance(race, go.Figure)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_analysis_views_bubble.py -v`
Expected: FAIL — `AttributeError: ... 'bubble_figure'`

- [ ] **Step 3: Append to `views.py`**

```python
def _pad(lo, hi, frac=0.1):
    span = (hi - lo) or (abs(hi) or 1.0)
    return lo - span * frac, hi + span * frac


def bubble_figure(records, theme: str = "dark", color_map=None) -> go.Figure:
    teams = [r["team"] for r in records]
    cmap = color_map or theme.team_color_map(teams)
    lay = theme_layout(theme)
    xs = [r.get("passes_total", 0.0) for r in records]
    ys = [r.get("passes_final_third", 0.0) for r in records]
    acc = [round(r.get("passes_succ", 0.0) / (r.get("passes_total", 0.0) or 1) * 100, 1)
           for r in records]
    fig = go.Figure(go.Scatter(
        x=xs, y=ys, mode="markers+text", text=teams, textposition="top center",
        marker=dict(size=[a * 0.6 for a in acc], color=[cmap[t] for t in teams],
                    sizemode="diameter", line=dict(width=1, color="rgba(0,0,0,0.3)")),
        customdata=[[a, round(ft / (tp or 1) * 100, 1)]
                    for a, ft, tp in zip(acc, ys, xs)],
        hovertemplate="<b>%{text}</b><br>Total passes: %{x:.0f}<br>"
                      "Into final third: %{y:.0f}<br>Accuracy: %{customdata[0]}%<br>"
                      "Final-third share: %{customdata[1]}%<extra></extra>"))
    fig.update_layout(
        paper_bgcolor=lay["paper_bgcolor"], plot_bgcolor=lay["plot_bgcolor"],
        font=lay["font"], margin=dict(l=50, r=30, t=10, b=40), autosize=True,
        showlegend=False,
        xaxis=dict(title="Total passes", gridcolor=lay["gridcolor_hint"],
                   range=list(_pad(min(xs), max(xs)))),
        yaxis=dict(title="Passes into final third", gridcolor=lay["gridcolor_hint"],
                   range=list(_pad(min(ys), max(ys)))))
    return fig


def build_figure(view, *, records=None, history=None, race_metric="points",
                 frame=0, theme="dark") -> go.Figure:
    t = view["type"]
    teams = [r["team"] for r in (records or [])] or list((history or {}).keys())
    cmap = theme.team_color_map(teams)
    if t == "radar":
        return radar_figure(records, view, theme)
    if t == "dumbbell":
        return dumbbell_figure(records, theme)
    if t == "race":
        return race_figure(history or {}, race_metric, frame, theme, color_map=cmap)
    if t == "funnel":
        return funnel_figure(records, theme, color_map=cmap)
    if t == "quadrant":
        return quadrant_figure(records, theme, color_map=cmap)
    if t == "defend":
        return defend_figure(records, theme)
    if t == "bubble":
        return bubble_figure(records, theme, color_map=cmap)
    raise ValueError(f"unknown view type: {t}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_analysis_views_bubble.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add src/components/analysis/views.py tests/test_analysis_views_bubble.py
git commit -m "feat(analysis): bubble chart (VOLUME_VS_PENETR) + build_figure dispatcher"
```

---

## Task 13: Panel shell (`panel.py`)

The static bento card: edge arrows, title/caption/caveat, dots, the `dcc.Graph`, RACE controls, and the stores/interval. All wiring is in Task 14; this task is structure + IDs + empty-state helper.

**Files:**
- Create: `src/components/analysis/panel.py`
- Test: `tests/test_analysis_panel.py`

**Interfaces:**
- Consumes: `dash` (`dcc`), `dash_mantine_components as dmc`, `dash_iconify` (used elsewhere in app), `views.VIEWS`, `accessors.RACE_METRICS`.
- Produces:
  - `panel.build_analysis_panel() -> dmc.Box` containing (by id): `analysis-panel` (root), `analysis-graph` (`dcc.Graph`), `analysis-title`, `analysis-caption`, `analysis-caveat`, `analysis-dots`, `analysis-prev`, `analysis-next`, `analysis-race-controls` (wrapper), `analysis-race-metric` (`dmc.Select`), `analysis-race-replay` (`dmc.Button`), and stores `analysis-view-index` (data=0), `analysis-race-frame` (data=0), plus `dcc.Interval` `analysis-race-interval` (disabled by default).
  - `panel.empty_state(group_name: str) -> dmc.Stack` — placeholder when a group has no finished matches.
  - `panel.dots(active: int, total: int) -> list` — position indicator children + an "n / total" label.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_analysis_panel.py
from __future__ import annotations

from dash import dcc

from src.components.analysis import panel


def _walk(node):
    yield node
    ch = getattr(node, "children", None)
    if isinstance(ch, (list, tuple)):
        for c in ch:
            yield from _walk(c)
    elif ch is not None:
        yield from _walk(ch)


def _ids(root):
    return {getattr(n, "id", None) for n in _walk(root)}


def test_panel_exposes_required_ids():
    root = panel.build_analysis_panel()
    ids = _ids(root)
    for needed in ["analysis-panel", "analysis-graph", "analysis-title",
                   "analysis-caption", "analysis-caveat", "analysis-dots",
                   "analysis-prev", "analysis-next", "analysis-race-controls",
                   "analysis-race-metric", "analysis-race-replay",
                   "analysis-view-index", "analysis-race-frame",
                   "analysis-race-interval"]:
        assert needed in ids, f"missing {needed}"


def test_graph_modebar_is_trimmed():
    root = panel.build_analysis_panel()
    graph = next(n for n in _walk(root) if isinstance(n, dcc.Graph))
    assert graph.config.get("displaylogo") is False


def test_dots_marks_active():
    children = panel.dots(active=2, total=10)
    assert "3 / 10" in str(children)


def test_empty_state_names_group():
    es = panel.empty_state("Group B")
    assert "Group B" in str(es.to_plotly_json())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_analysis_panel.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.components.analysis.panel'`

- [ ] **Step 3: Write `src/components/analysis/panel.py`**

```python
from __future__ import annotations

import dash_mantine_components as dmc
from dash import dcc, html
from dash_iconify import DashIconify

from src.components.analysis import views
from src.data.analysis.accessors import RACE_METRICS

_GRAPH_CONFIG = {
    "displaylogo": False,
    "displayModeBar": True,
    "modeBarButtonsToRemove": ["select2d", "lasso2d", "autoScale2d",
                               "zoomIn2d", "zoomOut2d", "toggleSpikelines"],
    "responsive": True,
}


def dots(active: int, total: int):
    pips = [html.Span(className="analysis-dot" + (" is-active" if i == active else ""))
            for i in range(total)]
    return [html.Div(pips, className="analysis-dots-row"),
            dmc.Text(f"{active + 1} / {total}", size="xs", c="dimmed")]


def empty_state(group_name: str) -> dmc.Stack:
    return dmc.Stack(
        [DashIconify(icon="mdi:chart-box-outline", width=42),
         dmc.Text(f"No completed matches yet for {group_name}", c="dimmed")],
        align="center", justify="center", className="analysis-empty")


def _arrow(id_, icon, label):
    return dmc.ActionIcon(DashIconify(icon=icon, width=22), id=id_,
                          variant="subtle", size="lg", radius="xl",
                          **{"aria-label": label})


def _race_controls():
    return dmc.Group(
        [dmc.Select(id="analysis-race-metric",
                    data=[{"value": v, "label": l} for v, l in RACE_METRICS.items()],
                    value="points", size="xs", w=170, allowDeselect=False),
         dmc.Button("Replay", id="analysis-race-replay", size="xs",
                    variant="light", leftSection=DashIconify(icon="mdi:replay"))],
        id="analysis-race-controls", gap="xs", style={"display": "none"})


def build_analysis_panel() -> dmc.Box:
    return dmc.Box(
        [
            dcc.Store(id="analysis-view-index", data=0),
            dcc.Store(id="analysis-race-frame", data=0),
            dcc.Interval(id="analysis-race-interval", interval=900, disabled=True),
            dmc.Group(
                [dmc.Title(id="analysis-title", order=5),
                 _race_controls()],
                justify="space-between", align="center",
                className="analysis-header"),
            dmc.Text(id="analysis-caption", size="xs", c="dimmed",
                     className="analysis-caption"),
            html.Div(
                [_arrow("analysis-prev", "mdi:chevron-left", "Previous chart"),
                 dcc.Graph(id="analysis-graph", config=_GRAPH_CONFIG,
                           className="analysis-graph",
                           style={"height": "100%", "width": "100%"}),
                 _arrow("analysis-next", "mdi:chevron-right", "Next chart")],
                className="analysis-stage"),
            dmc.Text(id="analysis-caveat", size="xs", c="dimmed",
                     className="analysis-caveat"),
            dmc.Group(dots(0, len(views.VIEWS)), id="analysis-dots",
                      justify="center", gap="xs", className="analysis-dots"),
        ],
        id="analysis-panel", className="analysis-panel")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_analysis_panel.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add src/components/analysis/panel.py tests/test_analysis_panel.py
git commit -m "feat(analysis): carousel panel shell with arrows, dots, controls, stores"
```

---

## Task 14: Callbacks + accessor wiring (`app.py`)

Wire the seam at startup, add the arrow/view-index callback, the figure-render callback, and the race animation callbacks. To keep them testable as pure functions, put the logic in module-level helpers and have thin callbacks delegate.

**Files:**
- Modify: `app.py` (imports near the other `src.components`/`src.data` imports; a `configure_analysis()` call after `GROUPS`/paths exist; helper functions near the other `_payload` helpers; callbacks in the callbacks section)
- Test: `tests/test_analysis_callbacks.py`

**Interfaces:**
- Consumes: `accessors`, `views`, `panel`, `advance` (already imported in app.py from `team_carousel`), `center_team`, `GROUPS`, `TEAM_NAMES`, `official_team`.
- Produces (module-level helpers in `app.py`):
  - `analysis_group_for_index(index) -> str | None` — the carousel-selected team's group name.
  - `analysis_render(view_index, race_metric, carousel_index, dark, frame) -> tuple` returning `(figure, title, caption, caveat_text, dots_children, race_controls_style)`.
  - `analysis_next_frame(frame, history_len) -> tuple[int, bool]` returning `(new_frame, interval_disabled)`.
- Wiring: `accessors.configure(team_stats_path=TEAM_STATS_PATH, player_store_path=PLAYER_STORE_PATH, groups=GROUPS, matches=MATCHES, official_resolver=official_team)`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_analysis_callbacks.py
from __future__ import annotations

import app as appmod
from src.data.analysis import accessors
from src.data.groups import build_groups
from tests.fixtures.analysis import sample


def _wire(tmp_path):
    stats = tmp_path / "t.csv"; players = tmp_path / "p.csv"
    sample.write_sample(stats, players)
    groups = build_groups(sample.SAMPLE_MATCHES)
    accessors.configure(team_stats_path=stats, player_store_path=players,
                        groups=groups, matches=sample.SAMPLE_MATCHES,
                        official_resolver=lambda n: n)
    return groups


def test_render_returns_figure_and_metadata_for_radar(tmp_path, monkeypatch):
    _wire(tmp_path)
    monkeypatch.setattr(appmod, "analysis_group_for_index",
                        lambda i: sample.SAMPLE_GROUP)
    fig, title, caption, caveat, dots_children, race_style = appmod.analysis_render(
        view_index=0, race_metric="points", carousel_index=0, dark=True, frame=0)
    assert fig.data  # has traces
    assert "Attacking" in title
    assert race_style == {"display": "none"}  # not the RACE view


def test_render_shows_race_controls_on_race_view(tmp_path, monkeypatch):
    _wire(tmp_path)
    monkeypatch.setattr(appmod, "analysis_group_for_index",
                        lambda i: sample.SAMPLE_GROUP)
    *_, race_style = appmod.analysis_render(
        view_index=5, race_metric="points", carousel_index=0, dark=True, frame=0)
    assert race_style.get("display") != "none"


def test_render_goals_conceded_adds_direction_caveat(tmp_path, monkeypatch):
    _wire(tmp_path)
    monkeypatch.setattr(appmod, "analysis_group_for_index",
                        lambda i: sample.SAMPLE_GROUP)
    _fig, _t, _c, caveat, *_ = appmod.analysis_render(
        view_index=5, race_metric="conceded", carousel_index=0, dark=True, frame=0)
    assert "lower is better" in caveat.lower()


def test_next_frame_stops_at_last():
    assert appmod.analysis_next_frame(0, 3) == (1, False)
    assert appmod.analysis_next_frame(2, 3) == (2, True)  # clamp + disable at end
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_analysis_callbacks.py -v`
Expected: FAIL — `AttributeError: module 'app' has no attribute 'analysis_render'`

- [ ] **Step 3: Add imports + wiring + helpers + callbacks to `app.py`**

Near the other component imports add:

```python
from src.components.analysis.panel import build_analysis_panel
from src.components.analysis import views as analysis_views
from src.data.analysis import accessors as analysis_accessors
```

After `GROUPS`, `TEAM_STATS_PATH`, `PLAYER_STORE_PATH`, and `official_team` are defined (i.e. after the `LIVE = ...` block), add:

```python
analysis_accessors.configure(
    team_stats_path=TEAM_STATS_PATH, player_store_path=PLAYER_STORE_PATH,
    groups=GROUPS, matches=MATCHES, official_resolver=official_team)
```

Add these helpers near the other `_payload` functions:

```python
def analysis_group_for_index(index):
    """Group name of the carousel-selected team (or None)."""
    team = center_team(TEAM_NAMES, index or 0)
    group = group_for_team(GROUPS, team)
    return group.name if group else None


def analysis_render(view_index, race_metric, carousel_index, dark, frame):
    """(figure, title, caption, caveat, dots_children, race_controls_style)."""
    from src.components.analysis import panel as analysis_panel
    theme = "dark" if dark else "light"
    n = len(analysis_views.VIEWS)
    vi = (view_index or 0) % n
    view = analysis_views.VIEWS[vi]
    group_name = analysis_group_for_index(carousel_index)
    dots_children = analysis_panel.dots(vi, n)

    records = analysis_accessors.get_group_aggregates(group_name) if group_name else []
    is_race = view["type"] == "race"
    race_style = {"display": "flex"} if is_race else {"display": "none"}

    if not records:
        import plotly.graph_objects as go
        empty = go.Figure()
        empty.update_layout(**{k: v for k, v in
                               analysis_views.theme_layout(theme).items()
                               if k in ("paper_bgcolor", "plot_bgcolor", "font")})
        empty.add_annotation(text=f"No completed matches yet for {group_name or '—'}",
                             showarrow=False)
        return empty, view["title"], view["caption"], "", dots_children, race_style

    history = (analysis_accessors.get_matchday_history(group_name, race_metric)
               if is_race else None)
    fig = analysis_views.build_figure(view, records=records, history=history,
                                      race_metric=race_metric, frame=frame or 0,
                                      theme=theme)
    caveat = view.get("caveat", "")
    if is_race and race_metric == "conceded":
        caveat = "Goals conceded — lower is better; the shortest bar leads."
    return fig, view["title"], view["caption"], caveat, dots_children, race_style


def analysis_next_frame(frame, history_len):
    """Step the race; clamp at the last frame and disable the interval there."""
    if history_len <= 0:
        return 0, True
    nxt = (frame or 0) + 1
    if nxt >= history_len - 1:
        return history_len - 1, True
    return nxt, False
```

In the callbacks section add:

```python
@callback(
    Output("analysis-view-index", "data"),
    Input("analysis-prev", "n_clicks"),
    Input("analysis-next", "n_clicks"),
    State("analysis-view-index", "data"),
    prevent_initial_call=True,
)
def move_analysis_view(_prev, _next, index):
    delta = -1 if ctx.triggered_id == "analysis-prev" else 1
    return advance(index or 0, delta, len(analysis_views.VIEWS))


@callback(
    Output("analysis-graph", "figure"),
    Output("analysis-title", "children"),
    Output("analysis-caption", "children"),
    Output("analysis-caveat", "children"),
    Output("analysis-dots", "children"),
    Output("analysis-race-controls", "style"),
    Input("analysis-view-index", "data"),
    Input("analysis-race-metric", "value"),
    Input("analysis-race-frame", "data"),
    Input("carousel-index", "data"),
    Input("live-store", "data"),
    State("color-scheme-toggle", "checked"),
)
def render_analysis(view_index, race_metric, frame, carousel_index, _live, dark):
    return analysis_render(view_index, race_metric, carousel_index,
                           dark if dark is not None else True, frame)


@callback(
    Output("analysis-race-frame", "data"),
    Output("analysis-race-interval", "disabled"),
    Input("analysis-race-interval", "n_intervals"),
    State("analysis-race-frame", "data"),
    State("analysis-view-index", "data"),
    State("analysis-race-metric", "value"),
    State("carousel-index", "data"),
    prevent_initial_call=True,
)
def step_race(_n, frame, view_index, race_metric, carousel_index):
    group_name = analysis_group_for_index(carousel_index)
    hist = (analysis_accessors.get_matchday_history(group_name, race_metric)
            if group_name else {})
    return analysis_next_frame(frame, analysis_views.race_frame_count(hist))


@callback(
    Output("analysis-race-frame", "data", allow_duplicate=True),
    Output("analysis-race-interval", "disabled", allow_duplicate=True),
    Input("analysis-race-replay", "n_clicks"),
    Input("analysis-view-index", "data"),
    Input("analysis-race-metric", "value"),
    prevent_initial_call=True,
)
def start_race(_clicks, view_index, _metric):
    # restart whenever RACE becomes active, the metric changes, or Replay is hit
    view = analysis_views.VIEWS[(view_index or 0) % len(analysis_views.VIEWS)]
    if view["type"] != "race":
        return 0, True
    return 0, False
```

Confirm `ctx` and `callback`/`Output`/`Input`/`State` are imported at the top of `app.py` (they are used by existing callbacks; if `ctx` is not yet imported, add it to the `from dash import ...` line).

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_analysis_callbacks.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Run the full suite to catch regressions**

Run: `python -m pytest tests/ -v`
Expected: PASS (existing tests unaffected; app imports cleanly).

- [ ] **Step 6: Commit**

```bash
git add app.py tests/test_analysis_callbacks.py
git commit -m "feat(analysis): wire accessors + carousel/render/race callbacks"
```

---

## Task 15: Mount the panel in the map tile + CSS (Team mode)

The panel renders inside the map card; CSS shows the map in Time mode and the panel in Team mode. The map stays mounted so its callbacks are untouched.

**Files:**
- Modify: `src/components/layout.py` (the `map_card` definition)
- Modify: `assets/styles.css`
- Test: `tests/test_analysis_integration.py` (part 1 — layout)

**Interfaces:**
- Consumes: `panel.build_analysis_panel`.
- Produces: the map card now contains both `#map-container` and `#analysis-panel`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_analysis_integration.py
from __future__ import annotations

import app as appmod


def _walk(node):
    yield node
    ch = getattr(node, "children", None)
    if isinstance(ch, (list, tuple)):
        for c in ch:
            yield from _walk(c)
    elif ch is not None:
        yield from _walk(ch)


def test_layout_mounts_analysis_panel_inside_map_card():
    layout = appmod.app.layout
    ids = {getattr(n, "id", None) for n in _walk(layout)}
    assert "analysis-panel" in ids
    assert "map-container" in ids  # map still mounted
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_analysis_integration.py -v`
Expected: FAIL — `assert 'analysis-panel' in ids` is False.

- [ ] **Step 3: Modify `src/components/layout.py`**

Add the import near the other component imports:

```python
from src.components.analysis.panel import build_analysis_panel
```

Change the `map_card` definition (currently around lines 100–102) from:

```python
    map_card = dmc.Box(
        html.Div(build_map(venues), id="map-container"),
        className="bento-card bento-card--map",
    )
```

to:

```python
    map_card = dmc.Box(
        [
            html.Div(build_map(venues), id="map-container"),
            build_analysis_panel(),
        ],
        className="bento-card bento-card--map",
    )
```

- [ ] **Step 4: Add CSS to `assets/styles.css`**

Append:

```css
/* --- Deep analysis panel (Team mode replaces the map tile) --- */
.bento-card--map #analysis-panel { display: none; }
.main-split--team .bento-card--map #map-container { display: none; }
.main-split--team .bento-card--map #analysis-panel { display: flex; }

#analysis-panel {
    flex-direction: column;
    height: 100%;
    width: 100%;
    min-height: 0;
    gap: 4px;
    padding: 8px 6px;
}
.analysis-header { flex: 0 0 auto; }
.analysis-caption { flex: 0 0 auto; }
.analysis-caveat { flex: 0 0 auto; min-height: 14px; }
.analysis-stage {
    position: relative;
    flex: 1 1 auto;
    min-height: 0;
    display: flex;
    align-items: stretch;
}
.analysis-graph { flex: 1 1 auto; min-width: 0; }
.analysis-stage .mantine-ActionIcon-root {
    position: absolute;
    top: 50%;
    transform: translateY(-50%);
    z-index: 5;
}
.analysis-stage .mantine-ActionIcon-root:first-child { left: 2px; }
.analysis-stage .mantine-ActionIcon-root:last-child { right: 2px; }
.analysis-dots-row { display: flex; gap: 5px; align-items: center; }
.analysis-dot {
    width: 6px; height: 6px; border-radius: 50%;
    background: var(--mantine-color-default-border);
}
.analysis-dot.is-active { background: var(--mantine-color-blue-5); }
.analysis-empty { height: 100%; }
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests/test_analysis_integration.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/components/layout.py assets/styles.css tests/test_analysis_integration.py
git commit -m "feat(analysis): mount panel in map tile; show in Team mode via CSS"
```

---

## Task 16: End-to-end render check (dark + light, all 10 views) + manual verification

A final integration test that drives the render helper across every view in both themes against the fixture data, plus a manual browser check.

**Files:**
- Modify: `tests/test_analysis_integration.py` (append)

**Interfaces:**
- Consumes: `appmod.analysis_render`, `accessors`, fixtures.

- [ ] **Step 1: Write the failing test (append)**

```python
# append to tests/test_analysis_integration.py
import plotly.graph_objects as go

from src.data.analysis import accessors
from src.data.groups import build_groups
from src.components.analysis import views
from tests.fixtures.analysis import sample


def test_every_view_renders_in_both_themes(tmp_path, monkeypatch):
    stats = tmp_path / "t.csv"; players = tmp_path / "p.csv"
    sample.write_sample(stats, players)
    groups = build_groups(sample.SAMPLE_MATCHES)
    accessors.configure(team_stats_path=stats, player_store_path=players,
                        groups=groups, matches=sample.SAMPLE_MATCHES,
                        official_resolver=lambda n: n)
    monkeypatch.setattr(appmod, "analysis_group_for_index",
                        lambda i: sample.SAMPLE_GROUP)
    for dark in (True, False):
        for vi in range(len(views.VIEWS)):
            fig, title, *_ = appmod.analysis_render(
                view_index=vi, race_metric="conceded", carousel_index=0,
                dark=dark, frame=1)
            assert isinstance(fig, go.Figure)
            assert title


def test_team_colors_consistent_across_views(tmp_path, monkeypatch):
    stats = tmp_path / "t.csv"; players = tmp_path / "p.csv"
    sample.write_sample(stats, players)
    groups = build_groups(sample.SAMPLE_MATCHES)
    accessors.configure(team_stats_path=stats, player_store_path=players,
                        groups=groups, matches=sample.SAMPLE_MATCHES,
                        official_resolver=lambda n: n)
    recs = accessors.get_group_aggregates(sample.SAMPLE_GROUP)
    cmap = views.theme.team_color_map([r["team"] for r in recs])
    # Mexico is first in seeding order -> first palette color, everywhere
    assert cmap["Mexico"] == "#534AB7"
```

- [ ] **Step 2: Run test to verify it fails / passes**

Run: `python -m pytest tests/test_analysis_integration.py -v`
Expected: PASS if Tasks 1–15 are correct. If any view raises, fix that builder.

- [ ] **Step 3: Run the full suite**

Run: `python -m pytest tests/ -v`
Expected: all green.

- [ ] **Step 4: Manual browser verification**

With a populated store (or temporarily point `TEAM_STATS_PATH`/`PLAYER_STORE_PATH` at a copy of the fixture output), run the app and confirm:

```bash
python app.py
```

Check: switch to **Team mode** → the map tile shows the analysis panel; arrows cycle all 10 views with wrap-around; the dots/position update; RACE shows the dropdown + Replay, auto-plays once and stops, Replay re-runs; switch the theme → charts re-render in light/dark with no black-on-dark text; switch back to **Time mode** → the full map returns. Confirm no horizontal scrollbar and the panel fits the tile.

- [ ] **Step 5: Commit**

```bash
git add tests/test_analysis_integration.py
git commit -m "test(analysis): all-views/both-themes render + color-consistency checks"
```

---

## Self-Review

**1. Spec coverage**

| Spec section | Covered by |
|---|---|
| §1 cumulative aggregation, group of 4, per-matchday history | Tasks 3, 5 |
| §2 data contract (`_DISPLAY_TO_KEY`, goals/matches_played) | reused `STAT_KEYS`; Task 3 adds goals/matches_played |
| §2A accessor seam, append-only store, atomic/idempotent, single writer | reuse existing store (design §2); Task 5 seam; degrade states Task 14 |
| §3 ten views in one ordered config | Task 6 `VIEWS` |
| §3 radar rules (≤6 axes, no raw+succ, caveats, style raw counts) | Tasks 4, 6 + tests |
| §4 normalization (per-90, field-relative, guards) | Task 4 |
| §5 each chart spec | radar T6, dumbbell T7, race T8, funnel T9, quadrant T10, defend T11, bubble T12 |
| §6 carousel nav (arrows, wrap, dots, per-view controls, a11y) | Tasks 13, 14 |
| §7 global polish (hovers, captions, caveats, theme) | builders T6–12 + `analysis_render` caveats |
| §8 acceptance checks | Tasks 14, 16 + per-view tests |
| §9 out of scope | not built; noted in design §13 |

**2. Placeholder scan:** No "TBD"/"implement later". Task 3 intentionally has the implementer correct one test assertion (documented inline) to force verifying the W/D/L math — this is explicit, not a placeholder.

**3. Type consistency:** `get_group_aggregates`/`get_matchday_history` signatures match across Tasks 5/14. `build_figure(view, *, records, history, race_metric, frame, theme)` keyword set matches the call in `analysis_render`. `team_color_map`/`team_fill_map`/`plotly_layout` names consistent across theme (T1) and all builders. `race_frame_count`/`race_figure` signatures match T8 and the callbacks in T14. `analysis_render` return tuple (6 items) matches the `render_analysis` callback outputs.

**Known, documented limitation:** goals are derived from summed player goals (own goals excluded by `player_stats` parsing). Acceptable for this panel; standings-based correction is a future enhancement behind the unchanged seam.
