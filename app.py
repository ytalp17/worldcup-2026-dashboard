from __future__ import annotations

import asyncio
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

from dash import ALL, Dash, Input, Output, State, callback, clientside_callback, ctx, no_update, set_props

from src.components.detail_panel import stadium_detail
from src.components.flow_layer import flows_for
from src.components.group_table import build_group_panel, group_rows, live_group_rows
from src.components.header_calendar import build_match_calendar, format_selected_day
from src.components.third_place import third_place_rows
from src.components.layout import build_layout
from src.components.map_view import DARK_TILE, LIGHT_TILE, MARKER_TYPE, live_score_markers, map_controls_style, pulse_markers
from src.data.distances import DistanceRepository
from src.data.flows import build_team_flows, team_cities
from src.data.groups import build_groups, group_for_team
from src.data.qualification import qualification_status
from src.data.third_place import groups_to_standings
from src.data.match_calendar import MatchCalendar
from src.data.matches import MatchRepository, is_placeholder, matches_by_stadium
from src.data.bracket import STAGE_PAGES, build_bracket
from src.components.knockout import page_dots, render_page
from src.components.formation_pitch import build_formation_panel, formation_title, pitch_src
from src.components.leaders_card import (
    build_leaders_card,
    leaders_columns,
    leaders_row_data,
)
from src.components.squad_table import build_squad_panel, squad_rows
from src.components.tournament_stats import (
    tab_options, tourn_columns, tourn_row_data)
from src.components.live_match_modal import build_modal, loading_body, modal_body
from src.components.live_strip import overlay_style, strip_items
from src.components.team_kpis import build_kpi_strip, kpi_cards
from src.data.team_form import recent_form
from src.components.team_carousel import advance, build_team_carousel, carousel_view, center_team, display_name, team_order
from src.components.analysis.panel import build_analysis_panel
from src.components.analysis import views as analysis_views
from src.data.analysis import accessors as analysis_accessors
from src.data.lineups import LineupRepository, lineup_for_team
from src.data.squads import Squad, SquadRepository, squad_for_team
from src.data.team_stats import compute_team_stats
from src.data.team_continents import (
    confederation_continent,
    confederation_for,
    fifa_rank_for,
    grouped_team_options,
    manager_age_for,
    manager_for,
    manager_nationality_for,
)
from src.components.goal_mouth import (
    build_goal_mouth_figure, build_goal_mouth_panel, drawer_body, ZONE_LABEL,
)
from src.data.live.client import HighlightlyClient
from src.data.live.reconcile import build_stadium_index, canonical_team
from src.data.env_config import load_env_file
from src.data.live.service import LiveDataService, next_delay
from src.data.venues import VenueRepository

DATA_DIR = Path(__file__).parent / "assets" / "data"
IMAGE_DIR = Path(__file__).parent / "assets" / "stadiums"
MANAGER_FLAGS_DIR = Path(__file__).parent / "assets" / "manager_flags"
CONFED_LOGOS_DIR = Path(__file__).parent / "assets" / "confederation_logos"

VENUES = VenueRepository(DATA_DIR / "venues.csv", IMAGE_DIR).load()
VENUES_BY_CITY = {v.city: v for v in VENUES}
DISTANCES = DistanceRepository(DATA_DIR / "teams.csv").load()

MATCHES = MatchRepository(DATA_DIR / "matches.csv").load()
MATCHES_BY_STADIUM = matches_by_stadium(MATCHES)
KO_MATCHES = [m for m in MATCHES if m.stage != "Group Stage"]

TEAM_FLOWS = build_team_flows(MATCHES, VENUES, distances=DISTANCES)
TEAM_OPTIONS = grouped_team_options(sorted(TEAM_FLOWS))
TEAM_NAMES = team_order(TEAM_FLOWS)
# Canonical (normalized) team name -> official cased name, so a raw/aliased live
# team name resolves to the country_logos/<official>.svg filename and display name.
_NORM_TO_OFFICIAL = {canonical_team(t): t for t in TEAM_NAMES}


def official_team(name: str) -> str:
    """Map a raw/aliased (e.g. live-feed) team name to its official cased name,
    which matches the country_logos/<official>.svg files and display_name."""
    return _NORM_TO_OFFICIAL.get(canonical_team(name), name)


GROUPS = build_groups(MATCHES)
SQUADS = SquadRepository(DATA_DIR / "squads.csv").load()
LINEUPS = LineupRepository(DATA_DIR / "estimated_starting_eleven.json").load()

STADIUM_TO_CITY = {v.stadium_name: v.city for v in VENUES}
# Friendly venue label per generic stadium name, for the knockout bracket cards.
VENUE_LABELS = {v.stadium_name: f"{v.official_name}, {v.city}" for v in VENUES}
MATCH_CALENDAR = MatchCalendar(MATCHES, STADIUM_TO_CITY, today=date.today())

STADIUM_INDEX = build_stadium_index(MATCHES)
# Load HIGHLIGHTLY_API_KEY (and any other vars) from a local .env so running
# `python app.py` picks up the key without a manual export. An already-exported
# value still wins (setdefault). Without a key, the app runs static-only.
load_env_file(Path(__file__).parent / ".env")
_API_KEY = os.environ.get("HIGHLIGHTLY_API_KEY")
# Per-match player-stats cache (gitignored). The live_feed loop maintains it;
# team_leaders reads it for the leaders card.
PLAYER_STORE_PATH = DATA_DIR / "live_player_stats.csv"
TEAM_STATS_PATH = DATA_DIR / "live_team_stats.csv"
SHOTS_STORE_PATH = DATA_DIR / "live_shots.csv"
# No-key mode: when the env var is unset the app runs purely on static data,
# so dev and the whole test suite work offline.
KNOCKOUT_START = min((m.kickoff_utc for m in KO_MATCHES), default=None)
LIVE = (
    LiveDataService(HighlightlyClient(api_key=_API_KEY), STADIUM_INDEX,
                    player_store=PLAYER_STORE_PATH, team_store=TEAM_STATS_PATH,
                    knockout_start=KNOCKOUT_START, shots_store=SHOTS_STORE_PATH)
    if _API_KEY else None
)

# Wire the Deep Analysis accessor seam now that the stats paths, groups, matches,
# and the official-name resolver all exist.
analysis_accessors.configure(
    team_stats_path=TEAM_STATS_PATH, player_store_path=PLAYER_STORE_PATH,
    groups=GROUPS, matches=MATCHES, official_resolver=official_team)


def flow_children(selected):
    return flows_for(selected, TEAM_FLOWS)


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


app = Dash(
    __name__,
    backend="fastapi",
    websocket_callbacks=True,
    suppress_callback_exceptions=True,
)
app.title = "FIFA World Cup 2026"
TEAM_CAROUSEL = build_team_carousel(TEAM_NAMES, app.get_asset_url, index=0)


def group_panel_payload(index, live_standings=None):
    """(group_name, rowData) for the centred team at `index`. Uses LIVE standings
    when available for that group, else the static (zeroed) standings."""
    team = center_team(TEAM_NAMES, index or 0)
    group = group_for_team(GROUPS, team)
    name = group.name if group else "—"
    rows = []
    if group:
        status_map = (qualification_status(live_standings).get(name, {})
                      if live_standings else {})
        rows = (live_group_rows(name, live_standings, app.get_asset_url,
                                resolve_team=official_team, status_map=status_map)
                or group_rows(group, app.get_asset_url))
    return name, rows


def third_place_payload(live_standings=None):
    """rowData for the third-place ranking grid. Uses LIVE standings when present
    (so the top-8 Round-of-32 marks reflect real results); otherwise seeds the
    static groups so the grid isn't empty pre-tournament (no green marks then)."""
    standings = live_standings or groups_to_standings(GROUPS)
    return third_place_rows(standings, app.get_asset_url, resolve_team=official_team)


def squad_panel_payload(index):
    """(team_name, rowData) for the centred team at `index`."""
    team = center_team(TEAM_NAMES, index or 0)
    squad = squad_for_team(SQUADS, team)
    name = squad.name if squad else "—"
    rows = squad_rows(squad) if squad else []
    return name, rows


def leaders_payload(stat, index):
    """(rowData, columnDefs, team_name) for the leaders grid: the centred team's
    player leaders for the active stat tab. Empty rows when there's no live data."""
    team = center_team(TEAM_NAMES, index or 0)
    leaders = LIVE.team_leaders(team) if LIVE is not None else {}
    return leaders_row_data(leaders, stat), leaders_columns(stat), team


def attach_team_flags(rows):
    """Add a `flag` asset URL to each row and swap the raw API team name for its
    display name, so the tournament grid's Team column can render the flag next
    to the label (via the TeamCell cellRenderer). The flag filename uses the
    canonical team name, matching assets/country_logos/<canonical>.svg."""
    out = []
    for r in rows:
        official = official_team(r.get("team", ""))
        out.append({**r, "team": display_name(official),
                    "flag": app.get_asset_url(f"country_logos/{official}.svg")})
    return out


def tournament_grid_payload(scope, tab, live, group_only=False):
    """(rowData, columnDefs) for the tournament grid. Empty rows when offline."""
    standings = (live or {}).get("standings") or {}
    tl = (LIVE.tournament_team_leaders(standings, group_only=group_only)
          if LIVE is not None else {})
    pl = (LIVE.tournament_player_leaders(group_only=group_only)
          if LIVE is not None else {})
    rows = attach_team_flags(tourn_row_data(scope, tab, tl, pl))
    return rows, tourn_columns(scope, tab)


_EMPTY_GM = {
    "zones": {z: {"count": 0, "outcomes": {}, "shooters": []}
              for z in ["high_left", "high_centre", "high_right",
                        "low_left", "low_centre", "low_right"]},
    "off_target": {"count": 0, "outcomes": {}},
    "other": {"count": 0, "outcomes": {}},
    "totals": {"on_target": 0, "near_miss": 0, "woodwork": 0,
               "off_target": 0, "other": 0, "total": 0},
}


def goal_mouth_figure_payload(index, live, dark, mode):
    """Figure for the carousel-selected team. `live` is the trigger only; data
    comes from the shot store via LIVE."""
    if LIVE is None:
        agg = _EMPTY_GM
    else:
        agg = LIVE.team_goal_mouth(center_team(TEAM_NAMES, index or 0))
    theme = "dark" if (dark is None or dark) else "light"
    fig_mode = "dominant" if mode == "Dominant" else "volume"
    return build_goal_mouth_figure(agg, mode=fig_mode, theme=theme)


def goal_mouth_drawer_payload(zone_id, index, live):
    """(title, children) for the zone drawer. Title doubles the zone name."""
    agg = _EMPTY_GM if LIVE is None else LIVE.team_goal_mouth(
        center_team(TEAM_NAMES, index or 0))
    title = ZONE_LABEL.get(zone_id, zone_id)
    return title, drawer_body(zone_id, agg)


def team_stats_payload(index):
    """TeamStats (KPI strip values) for the centred team at `index`."""
    team = center_team(TEAM_NAMES, index or 0)
    squad = squad_for_team(SQUADS, team) or Squad(team, ())
    nationality = manager_nationality_for(team)
    flag = None
    if nationality and (MANAGER_FLAGS_DIR / f"{nationality}.png").exists():
        flag = app.get_asset_url(f"manager_flags/{nationality}.png")
    confederation = confederation_for(team)
    confed_logo = None
    if confederation and (CONFED_LOGOS_DIR / f"{confederation}.svg").exists():
        confed_logo = app.get_asset_url(f"confederation_logos/{confederation}.svg")
    return compute_team_stats(
        squad,
        fifa_rank=fifa_rank_for(team),
        manager=manager_for(team),
        manager_nationality=nationality,
        manager_flag=flag,
        manager_age=manager_age_for(team),
        confederation=confederation,
        confederation_logo=confed_logo,
        confederation_region=confederation_continent(confederation),
    )


def _finished_tournament_matches(now):
    """All finished WC-2026 match dicts, read from the per-date caches that
    `_backfill_live_stats` warms on connect (so this stays a cheap cache read,
    not a burst of API calls). Empty when there's no live service."""
    if LIVE is None:
        return []
    today = date.today()
    matches = []
    for d in sorted({m.date for m in MATCHES if m.date <= today}):
        matches.extend(LIVE.matches_on(d.isoformat(), now))
    return matches


def team_form_payload(index, now=None):
    """The centred team's recent W/D/L in this tournament (oldest → newest),
    as a tuple of at most five tokens — for the Form KPI card."""
    team = center_team(TEAM_NAMES, index or 0)
    matches = _finished_tournament_matches(
        now if now is not None else time.monotonic())
    return tuple(recent_form(team, matches, canonical_team, limit=5))


def _bracket_standings(live):
    """({group: [official team names ordered by position]}, {complete groups}).
    A group is 'complete' once all four teams have played their three games, so
    we only resolve its winner/runner-up into the bracket then."""
    raw = (live or {}).get("standings") or {}
    standings, complete = {}, set()
    for group, rows in raw.items():
        standings[group] = [official_team(r["team"]) for r in rows]
        if len(rows) >= 4 and all(r.get("played", 0) >= 3 for r in rows):
            complete.add(group)
    return standings, complete


def _knockout_live(now):
    """({number: (home, away, home_score, away_score)}, {number: live match_id})
    for knockout matches the live feed carries. Matched to the schedule by
    kickoff instant. The feed publishes the knockout fixtures (real teams + ids,
    scheduled) ahead of kickoff, so we read every knockout date — not just past
    ones — which both fills the bracket with real matchups and makes the cards
    clickable. A card is clickable only once its teams are resolved (not
    placeholders), so there is always something to show in the modal."""
    if LIVE is None:
        return {}, {}
    # Pool every knockout date's live matches into one kickoff-keyed index. The
    # API groups a match under its own date, which can differ from the schedule's
    # match_date by a day (UTC vs local), so matching globally by kickoff instant
    # is more reliable than matching within a single date.
    by_kickoff = {}
    for date_iso in sorted({m.date.isoformat() for m in KO_MATCHES}):
        for lm in LIVE.matches_on(date_iso, now):
            if lm.get("kickoff"):
                by_kickoff[lm["kickoff"]] = lm
    results, match_ids = {}, {}
    for m in KO_MATCHES:
        lm = by_kickoff.get(m.kickoff_utc.isoformat())
        if not lm:
            continue
        home, away = lm.get("home", ""), lm.get("away", "")
        if is_placeholder(home) or is_placeholder(away):
            continue
        results[m.number] = (official_team(home), official_team(away),
                             lm.get("home_score"), lm.get("away_score"))
        if lm.get("match_id") is not None:
            match_ids[m.number] = lm["match_id"]
    return results, match_ids


def knockout_payload(page, live, user_tz):
    """(bracket body, page dots) for the knockout drawer at the given carousel
    page, resolved as far as the live data allows."""
    standings, complete = _bracket_standings(live)
    results, match_ids = _knockout_live(time.monotonic())
    bracket = build_bracket(KO_MATCHES, standings=standings,
                            complete_groups=complete, results=results,
                            match_ids=match_ids,
                            venues=VENUE_LABELS)
    page = max(0, min(page or 0, len(STAGE_PAGES) - 1))
    body = render_page(bracket, page, app.get_asset_url, user_tz, date.today())
    return body, page_dots(page)


def formation_panel_payload(index, dark):
    """(header_title, team, image_src) for the centred team's estimated XI.
    `dark` (the color-scheme-toggle state) picks the dark/light pitch image."""
    team = center_team(TEAM_NAMES, index or 0)
    lineup = lineup_for_team(LINEUPS, team)
    title = formation_title(lineup)
    src = pitch_src(lineup.slug, app.get_asset_url, dark) if lineup else ""
    return title, team, src


def strip_day_matches(selected_date, today, live, matches_on):
    """Match dicts for the strip on the selected day. Today -> the live-store
    matches (auto-updating); any other valid day -> matches_on(day); when the
    fetcher is None (no key) or the date is unparseable -> the live-store matches."""
    from datetime import date as _date
    if selected_date:
        try:
            day = _date.fromisoformat(selected_date)
        except (ValueError, TypeError):
            day = today
        if day != today and matches_on is not None:
            return matches_on(selected_date)
    return (live or {}).get("matches", [])


app.layout = build_layout(
    VENUES,
    TEAM_OPTIONS,
    TEAM_FLOWS,
    match_calendar=build_match_calendar(MATCH_CALENDAR),
    team_carousel=TEAM_CAROUSEL,
    group_panel=build_group_panel(group_for_team(GROUPS, center_team(TEAM_NAMES, 0)), app.get_asset_url),
    squad_panel=build_squad_panel(squad_for_team(SQUADS, center_team(TEAM_NAMES, 0))),
    formation_panel=build_formation_panel(
        lineup_for_team(LINEUPS, center_team(TEAM_NAMES, 0)),
        app.get_asset_url,
        dark=True,
    ),
    kpi_strip=build_kpi_strip(team_stats_payload(0), team_form_payload(0)),
    leaders_panel=build_leaders_card(),
    goal_mouth_panel=build_goal_mouth_panel(),
    asset_url=app.get_asset_url,
)

# Use the white FIFA logo as the browser tab icon (SVG favicon, modern browsers).
_FAVICON = app.get_asset_url("logos/fifa_logo_white.cc.svg")
app.index_string = f"""<!DOCTYPE html>
<html>
    <head>
        {{%metas%}}
        <title>{{%title%}}</title>
        <link rel="icon" type="image/svg+xml" href="{_FAVICON}">
        {{%css%}}
    </head>
    <body>
        {{%app_entry%}}
        <footer>
            {{%config%}}
            {{%scripts%}}
            {{%renderer%}}
        </footer>
    </body>
</html>"""


def _venue_match_links(matches, now):
    """{match_number: api_match_id} for a venue's matches, resolved per date."""
    if LIVE is None:
        return {}
    from src.data.live.reconcile import canonical_team, index_matches_by_pair
    links = {}
    by_date = {}
    for m in matches:
        by_date.setdefault(m.date.isoformat(), []).append(m)
    for date_iso, day_matches in by_date.items():
        idx = index_matches_by_pair(LIVE.matches_on(date_iso, now))
        for m in day_matches:
            mid = idx.get((canonical_team(m.home), canonical_team(m.away)))
            if mid is not None:
                links[m.number] = mid
    return links


def drawer_for_city(city: str | None, user_tz: str | None = None, live: dict | None = None):
    """Compute the (opened, title, children) drawer state for a clicked city."""
    venue = VENUES_BY_CITY.get(city) if city else None
    if venue is None:
        return False, no_update, no_update
    matches = MATCHES_BY_STADIUM.get(venue.stadium_name, [])
    links = _venue_match_links(matches, time.monotonic())
    return True, venue.official_name, stadium_detail(venue, matches, user_tz, live=live, match_links=links)


@callback(
    Output("stadium-drawer", "opened"),
    Output("stadium-drawer", "title"),
    Output("stadium-drawer", "children"),
    Output("filter-drawer", "opened", allow_duplicate=True),
    Output("tournament-drawer", "opened", allow_duplicate=True),
    Output("knockout-drawer", "opened", allow_duplicate=True),
    Output("third-place-drawer", "opened", allow_duplicate=True),
    Input({"type": MARKER_TYPE, "index": ALL}, "n_clicks"),
    State("user-tz", "data"),
    State("live-store", "data"),
    prevent_initial_call=True,
)
def open_stadium_drawer(n_clicks, user_tz, live):
    # user_tz is a State snapshot: if the tz probe hasn't resolved yet, the drawer falls back to venue-local time (window is brief, acceptable per design).
    # Ignore the callback firing when markers mount with n_clicks=None.
    if not any(n_clicks):
        return no_update, no_update, no_update, no_update, no_update, no_update, no_update
    triggered = ctx.triggered_id
    city = triggered.get("index") if isinstance(triggered, dict) else None
    opened, title, children = drawer_for_city(city, user_tz, live)
    # Opening the stadium drawer closes the filter, tournament, knockout and
    # third-place drawers.
    return opened, title, children, (False if opened else no_update), False, False, False


@callback(
    Output("filter-drawer", "opened"),
    Output("stadium-drawer", "opened", allow_duplicate=True),
    Output("tournament-drawer", "opened", allow_duplicate=True),
    Output("knockout-drawer", "opened", allow_duplicate=True),
    Output("third-place-drawer", "opened", allow_duplicate=True),
    Input("filter-control", "n_clicks"),
    prevent_initial_call=True,
)
def open_filter_drawer(n_clicks):
    if not n_clicks:
        return no_update, no_update, no_update, no_update, no_update
    return True, False, False, False, False  # open filter; close the others


@callback(
    Output("tournament-drawer", "opened"),
    Output("filter-drawer", "opened", allow_duplicate=True),
    Output("stadium-drawer", "opened", allow_duplicate=True),
    Output("knockout-drawer", "opened", allow_duplicate=True),
    Output("third-place-drawer", "opened", allow_duplicate=True),
    Input("tournament-control", "n_clicks"),
    prevent_initial_call=True,
)
def open_tournament_drawer(n_clicks):
    if not n_clicks:
        return no_update, no_update, no_update, no_update, no_update
    return True, False, False, False, False


@callback(
    Output("third-place-drawer", "opened"),
    Output("filter-drawer", "opened", allow_duplicate=True),
    Output("stadium-drawer", "opened", allow_duplicate=True),
    Output("tournament-drawer", "opened", allow_duplicate=True),
    Output("knockout-drawer", "opened", allow_duplicate=True),
    Input("third-place-control", "n_clicks"),
    prevent_initial_call=True,
)
def open_third_place_drawer(n_clicks):
    if not n_clicks:
        return no_update, no_update, no_update, no_update, no_update
    return True, False, False, False, False  # open third-place; close the others


@callback(
    Output("knockout-drawer", "opened"),
    Output("filter-drawer", "opened", allow_duplicate=True),
    Output("tournament-drawer", "opened", allow_duplicate=True),
    Output("stadium-drawer", "opened", allow_duplicate=True),
    Output("third-place-drawer", "opened", allow_duplicate=True),
    Input("knockout-control", "n_clicks"),
    prevent_initial_call=True,
)
def open_knockout_drawer(n_clicks):
    if not n_clicks:
        return no_update, no_update, no_update, no_update, no_update
    return True, False, False, False, False  # open knockout; close the other four


@callback(
    Output("knockout-page", "data"),
    Input("knockout-prev", "n_clicks"),
    Input("knockout-next", "n_clicks"),
    State("knockout-page", "data"),
    prevent_initial_call=True,
)
def move_knockout_page(_prev, _next, page):
    delta = -1 if ctx.triggered_id == "knockout-prev" else 1
    return max(0, min((page or 0) + delta, len(STAGE_PAGES) - 1))


@callback(
    Output("knockout-body", "children"),
    Output("knockout-dots", "children"),
    Input("knockout-page", "data"),
    Input("live-store", "data"),
    Input("user-tz", "data"),  # re-render kickoff times once the browser tz resolves
)
def render_knockout(page, live, user_tz):
    return knockout_payload(page, live, user_tz)


@callback(
    Output("third-place-grid", "rowData"),
    Input("live-store", "data"),
    Input("third-place-control", "n_clicks"),
)
def render_third_place(live, n_clicks):
    # An explicit click hits the API for fresh standings (teams may have just
    # finished their three group games), bypassing the long standings cache;
    # otherwise use the latest snapshot the store already holds.
    if ctx.triggered_id == "third-place-control" and n_clicks and LIVE is not None:
        fresh = LIVE.standings(time.monotonic(), force=True)
        if fresh:
            return third_place_payload(fresh)
    return third_place_payload((live or {}).get("standings") or None)


@callback(
    Output("flow-layer", "children"),
    Input("mode-toggle", "checked"),
    Input("journey-grid", "selectedRows"),
    Input("carousel-index", "data"),
)
def update_flow_layer(team_mode, selected_rows, index):
    # Time mode: the teams selected in the journey grid drive the map flows.
    selected = [r["team_raw"] for r in (selected_rows or [])]
    return flow_children_for_mode(team_mode, selected, index)


def _active_cities_for_date(selected_date: str | None, user_tz: str | None) -> set[str]:
    """Host cities with a match on the selected date, in the user's timezone
    (falls back to venue dates when the timezone is unknown)."""
    if not selected_date:
        return set()
    try:
        day = date.fromisoformat(str(selected_date)[:10])
    except ValueError:
        return set()
    return MATCH_CALENDAR.active_cities(day, user_tz)


def flow_children_for_mode(
    team_mode: bool, filter_value: list[str] | None, index: int | None
) -> list:
    """Flow-layer children: Team mode uses the centred team; Time mode uses filter_value."""
    if team_mode:
        selected = [center_team(TEAM_NAMES, index if index is not None else 0)]
    else:
        selected = filter_value
    return flow_children(selected)


def pulse_children_for_mode(
    team_mode: bool, selected_date: str | None, index: int | None, user_tz: str | None = None
) -> list:
    """Team mode → centered team's cities; Time mode → the date's active cities
    in the user's timezone. `user_tz` defaults to None so existing 3-arg callers
    keep the venue-date behavior."""
    if team_mode:
        center = center_team(TEAM_NAMES, index if index is not None else 0)
        active = team_cities(TEAM_FLOWS[center], STADIUM_TO_CITY)
    else:
        active = _active_cities_for_date(selected_date, user_tz)
    return pulse_markers(VENUES, active)


@callback(
    Output("pulse-layer", "children"),
    Input("mode-toggle", "checked"),
    Input("match-calendar", "value"),
    Input("carousel-index", "data"),
    Input("user-tz", "data"),
)
def update_pulse_layer(team_mode, selected_date, index, user_tz):
    return pulse_children_for_mode(team_mode, selected_date, index, user_tz)


@callback(
    Output("live-layer", "children"),
    Input("live-store", "data"),
)
def update_live_layer(live):
    return live_score_markers(VENUES, live)


@callback(
    Output("calendar-selected-date", "children"),
    Input("match-calendar", "value"),
)
def render_selected_date(selected_date):
    return format_selected_day(selected_date)


@callback(
    Output("live-strip", "children"),
    Input("match-calendar", "value"),
    Input("live-store", "data"),
    State("user-tz", "data"),
)
def render_live_strip(selected_date, live, user_tz):
    fetch = (lambda d: LIVE.matches_on(d, time.monotonic())) if LIVE is not None else None
    matches = strip_day_matches(selected_date, date.today(), live, fetch)
    return strip_items({"matches": matches}, user_tz=user_tz)


def _modal_match_id(triggered_id, triggered_value):
    """Resolve the match_id to open, or ``None`` to do nothing.

    The modal must open ONLY on a real click. Pattern-matching callbacks also
    fire when new matching components are mounted — e.g. when the venue drawer
    renders its match cards — and those carry a falsy ``n_clicks`` value. We
    gate on that value so a drawer-open never pops a stray modal.
    """
    if not isinstance(triggered_id, dict):
        return None
    if not triggered_value:
        return None
    return triggered_id.get("index")


def _modal_target_id(target):
    """Extract the match_id from the Phase-1 → Phase-2 handoff payload."""
    if not isinstance(target, dict):
        return None
    return target.get("id")


def _fetch_modal_payload(match_id, now):
    """Fetch the four match-detail datasets concurrently.

    They hit four independent, distinct-keyed caches, so running them in
    parallel turns first-open latency from ~4 round-trips into ~1.
    """
    if LIVE is None:
        return None, [], {}, {}
    with ThreadPoolExecutor(max_workers=4) as ex:
        f_match = ex.submit(LIVE.match_summary, match_id, now)
        f_events = ex.submit(LIVE.match_events, match_id, now)
        f_stats = ex.submit(LIVE.match_statistics, match_id, now)
        f_lineups = ex.submit(LIVE.match_lineups, match_id, now)
        return f_match.result(), f_events.result(), f_stats.result(), f_lineups.result()


@callback(
    Output("live-match-modal", "opened"),
    Output("live-modal-target", "data"),
    Output("live-modal-content", "children"),
    Input({"type": "live-strip-item", "index": ALL}, "n_clicks"),
    Input({"type": "open-live-modal", "index": ALL}, "n_clicks"),
    prevent_initial_call=True,
)
def open_live_modal(strip_clicks, drawer_clicks):
    # Phase 1 — instant, zero network: open the modal on a real click, show the
    # skeleton, and hand the match_id (with a nonce so re-opens always re-fill)
    # to the fill callback.
    trig_value = ctx.triggered[0]["value"] if ctx.triggered else None
    match_id = _modal_match_id(ctx.triggered_id, trig_value)
    if match_id is None:
        return no_update, no_update, no_update
    return True, {"id": match_id, "t": time.monotonic()}, loading_body()


@callback(
    Output("live-modal-content", "children", allow_duplicate=True),
    Input("live-modal-target", "data"),
    prevent_initial_call=True,
)
def fill_live_modal(target):
    # Phase 2 — fetch in the background and swap the real body in for the skeleton.
    match_id = _modal_target_id(target)
    if match_id is None:
        return no_update
    match, events, stats, lineups = _fetch_modal_payload(match_id, time.monotonic())
    return modal_body(match, events, stats, lineups)


@callback(
    Output("calendar-wrapper", "style"),
    Output("carousel-wrapper", "style"),
    Input("mode-toggle", "checked"),
)
def toggle_center_widget(team_mode):
    hidden = {"display": "none"}
    shown = {"display": "block"}
    return (hidden, shown) if team_mode else (shown, hidden)


@callback(
    Output("map-controls-overlay", "style"),
    Input("mode-toggle", "checked"),
)
def toggle_map_controls(team_mode):
    # The Tournament Stats / Team Travel Map controls belong to the calendar/Time
    # view only; hide the whole overlay in Team mode. Runs on initial load too, so
    # a persisted Team mode hides it from the first render.
    return map_controls_style(visible=not team_mode)


@callback(
    Output("live-strip-overlay", "style"),
    Input("mode-toggle", "checked"),
)
def toggle_live_strip(team_mode):
    # The live match strip belongs to the calendar/Time view only; hide it in
    # Team mode. Runs on initial load too, so a persisted Team mode hides it.
    return overlay_style(visible=not team_mode)


@callback(
    Output("filter-drawer", "opened", allow_duplicate=True),
    Input("mode-toggle", "checked"),
    prevent_initial_call=True,
)
def close_filter_drawer_in_team_mode(team_mode):
    # Entering Team mode closes the (right-side) filter drawer; leaving it alone otherwise.
    return False if team_mode else no_update


@callback(
    Output("tournament-drawer", "opened", allow_duplicate=True),
    Input("mode-toggle", "checked"),
    prevent_initial_call=True,
)
def close_tournament_drawer_in_team_mode(team_mode):
    # Team mode hides the tournament pin, so also close its (right-side) drawer.
    return False if team_mode else no_update


@callback(
    Output("knockout-drawer", "opened", allow_duplicate=True),
    Input("mode-toggle", "checked"),
    prevent_initial_call=True,
)
def close_knockout_drawer_in_team_mode(team_mode):
    # Team mode hides the map controls, so also close the knockout drawer.
    return False if team_mode else no_update


@callback(
    Output("carousel-index", "data"),
    Input("carousel-prev", "n_clicks"),
    Input("carousel-next", "n_clicks"),
    Input("carousel-logo-prev", "n_clicks"),
    Input("carousel-logo-next", "n_clicks"),
    Input("carousel-logo-prev2", "n_clicks"),
    Input("carousel-logo-next2", "n_clicks"),
    State("carousel-index", "data"),
    prevent_initial_call=True,
)
def move_carousel(_p, _n, _lp, _ln, _lp2, _ln2, index):
    # Arrows and inner logos step ±1; the outer logos jump ±2 (bring a far team in).
    deltas = {
        "carousel-prev": -1,
        "carousel-logo-prev": -1,
        "carousel-logo-prev2": -2,
        "carousel-next": 1,
        "carousel-logo-next": 1,
        "carousel-logo-next2": 2,
    }
    delta = deltas.get(ctx.triggered_id, 1)
    return advance(index or 0, delta, len(TEAM_NAMES))


@callback(
    Output("carousel-img-prev2", "src"),
    Output("carousel-img-prev", "src"),
    Output("carousel-img-center", "src"),
    Output("carousel-img-next", "src"),
    Output("carousel-img-next2", "src"),
    Output("carousel-name", "children"),
    Input("carousel-index", "data"),
)
def render_carousel(index):
    view = carousel_view(TEAM_NAMES, index or 0, app.get_asset_url)
    return (
        view["prev2_src"],
        view["prev1_src"],
        view["center_src"],
        view["next1_src"],
        view["next2_src"],
        view["center_name"],
    )


@callback(
    Output("group-grid", "rowData"),
    Output("group-table-title", "children"),
    Input("carousel-index", "data"),
    Input("live-store", "data"),
)
def update_group_panel(index, live):
    name, rows = group_panel_payload(index, (live or {}).get("standings"))
    return rows, name


@callback(
    Output("squad-grid", "rowData"),
    Output("squad-table-title", "children"),
    Input("carousel-index", "data"),
)
def update_squad_panel(index):
    name, rows = squad_panel_payload(index)
    return rows, name


@callback(
    Output("leaders-grid", "rowData"),
    Output("leaders-grid", "columnDefs"),
    Output("leaders-table-title", "children"),
    Input("leaders-tabs", "value"),
    Input("carousel-index", "data"),
    Input("live-store", "data"),
)
def update_leaders_panel(stat, index, live):
    rows, cols, team = leaders_payload(stat, index)
    return rows, cols, team


@callback(
    Output("tourn-tabs", "data"),
    Output("tourn-tabs", "value"),
    Input("tourn-scope", "value"),
)
def set_tournament_tabs(scope):
    opts = tab_options(scope)
    return opts, opts[0]


@callback(
    Output("tourn-grid", "rowData"),
    Output("tourn-grid", "columnDefs"),
    Input("tourn-scope", "value"),
    Input("tourn-tabs", "value"),
    Input("tourn-stage", "checked"),
    Input("live-store", "data"),
)
def update_tournament_grid(scope, tab, group_stage_on, live):
    return tournament_grid_payload(scope, tab, live, bool(group_stage_on))


@callback(
    Output("formation-img", "src"),
    Output("formation-title", "children"),
    Input("carousel-index", "data"),
    Input("color-scheme-toggle", "checked"),
)
def update_formation_panel(index, dark):
    # Single owner of the pitch image src: re-renders on team change (carousel)
    # and on theme change (dark/light), so the two never race for the src.
    title, _team, src = formation_panel_payload(index, dark)
    return src, title


@callback(
    Output("kpi-strip", "children"),
    Input("carousel-index", "data"),
    Input("live-store", "data"),
)
def update_kpi_strip(index, _live):
    # _live is the trigger only: form is read from the per-date caches so the
    # strip refreshes as results finalise; the snapshot itself carries no history.
    return kpi_cards(team_stats_payload(index), team_form_payload(index))


@callback(
    Output("goal-mouth-graph", "figure"),
    Input("carousel-index", "data"),
    Input("goal-mouth-mode", "value"),
    Input("color-scheme-toggle", "checked"),
    Input("live-store", "data"),
)
def update_goal_mouth(index, mode, dark, live):
    return goal_mouth_figure_payload(index, live, dark, mode)


@callback(
    Output("goal-mouth-zone", "data"),
    Output("goal-mouth-drawer", "opened"),
    Output("goal-mouth-drawer", "title"),
    Output("goal-mouth-drawer", "children"),
    Input("goal-mouth-graph", "clickData"),
    Input("carousel-index", "data"),
    State("goal-mouth-zone", "data"),
    State("live-store", "data"),
    prevent_initial_call=True,
)
def open_goal_mouth_zone(click, index, current_zone, live):
    # Team change closes any open zone drawer.
    if ctx.triggered_id == "carousel-index":
        return None, False, no_update, no_update
    if not click or not click.get("points"):
        return no_update, no_update, no_update, no_update
    zid = click["points"][0].get("customdata")
    if isinstance(zid, list):           # customdata may arrive as a list
        zid = zid[0]
    if zid is None:                     # stray fill-edge click with no zone -> ignore
        return no_update, no_update, no_update, no_update
    if zid == current_zone:             # re-click same zone -> close
        return None, False, no_update, no_update
    title, children = goal_mouth_drawer_payload(zid, index, live)
    return zid, True, title, children


@callback(
    Output("goal-mouth-zone", "data", allow_duplicate=True),
    Input("goal-mouth-drawer", "opened"),
    prevent_initial_call=True,
)
def clear_goal_mouth_zone(opened):
    # Closing via the X / overlay clears the stored zone so a re-click reopens.
    return None if not opened else no_update


# Toggling the switch flips both the Mantine color scheme and the base map
# tiles in one clientside callback (checked => dark). The tile URLs contain
# Leaflet's {s}/{z}/{x}/{y} placeholders, so inject them via json.dumps rather
# than an f-string.
_THEME_JS = """
(checked) => {
    document.documentElement.setAttribute(
        'data-mantine-color-scheme', checked ? 'dark' : 'light'
    );
    return checked ? __DARK__ : __LIGHT__;
}
""".replace("__DARK__", json.dumps(DARK_TILE)).replace("__LIGHT__", json.dumps(LIGHT_TILE))

clientside_callback(
    _THEME_JS,
    Output("base-tiles", "url"),
    Input("color-scheme-toggle", "checked"),
)

# Read the browser's IANA timezone once at load (e.g. "Europe/Berlin"); null on failure.
_TZ_JS = """
function(_) {
    try { return Intl.DateTimeFormat().resolvedOptions().timeZone || null; }
    catch (e) { return null; }
}
"""

clientside_callback(
    _TZ_JS,
    Output("user-tz", "data"),
    Input("tz-probe", "n_intervals"),
)

# Switch the main area into the Team-mode bento grid by adding `--team`; Time
# mode (no modifier) collapses the grid so the map card fills the screen. The
# grid layout snaps instantly (no CSS transition), so re-tile the map as soon as
# the new layout is applied: fire a window resize on the next animation frames
# (Leaflet's invalidateSize) plus a short fallback. A long delay would leave the
# map mis-tiled (e.g. a grey band when it expands) until the resize fired.
_PANEL_JS = """
(checked) => {
    const fire = () => window.dispatchEvent(new Event('resize'));
    requestAnimationFrame(() => requestAnimationFrame(fire));
    setTimeout(fire, 120);
    return checked ? 'main-split main-split--team' : 'main-split';
}
"""

clientside_callback(
    _PANEL_JS,
    Output("main-split", "className"),
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

_SQUAD_GRID_THEME_JS = """
(checked) => (checked ? 'ag-theme-quartz-dark squad-grid'
                      : 'ag-theme-quartz squad-grid')
"""

clientside_callback(
    _SQUAD_GRID_THEME_JS,
    Output("squad-grid", "className"),
    Input("color-scheme-toggle", "checked"),
)

_JOURNEY_GRID_THEME_JS = """
(checked) => (checked ? 'ag-theme-quartz-dark journey-grid'
                      : 'ag-theme-quartz journey-grid')
"""

clientside_callback(
    _JOURNEY_GRID_THEME_JS,
    Output("journey-grid", "className"),
    Input("color-scheme-toggle", "checked"),
)

_TOURN_GRID_THEME_JS = """
(checked) => (checked ? 'ag-theme-quartz-dark tourn-grid'
                      : 'ag-theme-quartz tourn-grid')
"""

clientside_callback(
    _TOURN_GRID_THEME_JS,
    Output("tourn-grid", "className"),
    Input("color-scheme-toggle", "checked"),
)

_LEADERS_GRID_THEME_JS = """
(checked) => (checked ? 'ag-theme-quartz-dark leaders-grid'
                      : 'ag-theme-quartz leaders-grid')
"""

clientside_callback(
    _LEADERS_GRID_THEME_JS,
    Output("leaders-grid", "className"),
    Input("color-scheme-toggle", "checked"),
)

_TP_GRID_THEME_JS = """
(checked) => (checked ? 'ag-theme-quartz-dark tp-grid'
                      : 'ag-theme-quartz tp-grid')
"""

clientside_callback(
    _TP_GRID_THEME_JS,
    Output("third-place-grid", "className"),
    Input("color-scheme-toggle", "checked"),
)

# Switch the journey grid's Distance unit (km <-> mi). The formatDistance value
# formatter reads window.__journeyUnit; we set it and refresh just that column so
# the current sort and page are preserved (no rowData/columnDefs churn).
_UNIT_JS = """
async function(toMiles) {
    window.__journeyUnit = toMiles ? 'mi' : 'km';
    try {
        const api = await dash_ag_grid.getApiAsync('journey-grid');
        if (api) api.refreshCells({force: true, columns: ['distance_km']});
    } catch (e) {}
    return toMiles ? 'mi' : 'km';
}
"""

clientside_callback(
    _UNIT_JS,
    Output("unit-store", "data"),
    Input("unit-toggle", "checked"),
)

# Selected teams are tinted in their own flow colour via the grid's getRowStyle,
# which only re-runs on a redraw — so redraw the rows whenever the selection
# changes. (The selection also drives the map flows via update_flow_layer.)
_JOURNEY_REDRAW_JS = """
async function(selectedRows) {
    try {
        const api = await dash_ag_grid.getApiAsync('journey-grid');
        if (api) api.redrawRows();
    } catch (e) {}
    return window.dash_clientside.no_update;
}
"""

clientside_callback(
    _JOURNEY_REDRAW_JS,
    Output("journey-redraw", "data"),
    Input("journey-grid", "selectedRows"),
)

def _backfill_live_stats():
    """Refresh both per-match caches from past scheduled dates, once per process
    start. Cheaply idempotent: updaters skip finished matches already on disk."""
    today = date.today()
    now = time.monotonic()
    for d in sorted({m.date for m in MATCHES if m.date <= today}):
        day = LIVE.matches_on(d.isoformat(), now)
        LIVE.update_player_stats(day, now)
        LIVE.update_team_stats(day, now)
        LIVE.update_shot_stats(day, now)
    # Warm the matches_on cache for upcoming knockout dates too, so the
    # knockout bracket renders (and its cards become clickable) without each
    # render paying for ~17 future-date fetches.
    for d in sorted({m.date for m in KO_MATCHES if m.date > today}):
        LIVE.matches_on(d.isoformat(), now)


# Always register the persistent WS callback so the client can always resolve it
# (a conditional registration leaves a connecting client with a callback the
# server doesn't know, which raises "Callback function not found"). When there's
# no API key the callback simply returns and the app stays on static data.
@callback(persistent=True)
async def live_feed():
    ws = ctx.websocket
    if ws is None or LIVE is None:
        return
    await asyncio.to_thread(_backfill_live_stats)
    while not ws.is_shutdown:
        now = asyncio.get_running_loop().time()
        snap = await asyncio.to_thread(LIVE.snapshot, date.today().isoformat(), now)
        set_props("live-store", {"data": snap})
        await asyncio.to_thread(LIVE.update_player_stats, snap["matches"], now)
        await asyncio.to_thread(LIVE.update_team_stats, snap["matches"], now)
        await asyncio.to_thread(LIVE.update_shot_stats, snap["matches"], now)
        await asyncio.sleep(next_delay(snap))


@callback(
    Output("analysis-view-index", "data"),
    Input("analysis-prev", "n_clicks"),
    Input("analysis-next", "n_clicks"),
    Input("analysis-modal-prev", "n_clicks"),
    Input("analysis-modal-next", "n_clicks"),
    State("analysis-view-index", "data"),
    prevent_initial_call=True,
)
def move_analysis_view(_prev, _next, _mprev, _mnext, index):
    delta = -1 if ctx.triggered_id in ("analysis-prev", "analysis-modal-prev") else 1
    return advance(index or 0, delta, len(analysis_views.VIEWS))


@callback(
    Output("analysis-graph", "figure"),
    Output("analysis-title", "children"),
    Output("analysis-caption", "children"),
    Output("analysis-caveat", "children"),
    Output("analysis-dots", "children"),
    Output("analysis-race-controls", "style"),
    Output("analysis-modal-graph", "figure"),
    Output("analysis-modal", "title"),
    Output("analysis-modal-dots", "children"),
    Input("analysis-view-index", "data"),
    Input("analysis-race-metric", "value"),
    Input("analysis-race-frame", "data"),
    Input("carousel-index", "data"),
    Input("live-store", "data"),
    Input("color-scheme-toggle", "checked"),
)
def render_analysis(view_index, race_metric, frame, carousel_index, _live, dark):
    fig, title, caption, caveat, dots_children, race_style = analysis_render(
        view_index, race_metric, carousel_index,
        dark if dark is not None else True, frame)
    # The expanded modal mirrors the current chart (same figure), title, and
    # position dots so the in-modal carousel stays in sync with the tile.
    return (fig, title, caption, caveat, dots_children, race_style,
            fig, title, dots_children)


@callback(
    Output("analysis-modal", "opened"),
    Input("analysis-expand", "n_clicks"),
    State("analysis-modal", "opened"),
    prevent_initial_call=True,
)
def toggle_analysis_modal(_n, opened):
    return not opened


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


if __name__ == "__main__":
    app.run(debug=False)
