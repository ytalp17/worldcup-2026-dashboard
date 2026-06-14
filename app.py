from __future__ import annotations

import asyncio
import json
import os
import time
from datetime import date
from pathlib import Path

from dash import ALL, Dash, Input, Output, State, callback, clientside_callback, ctx, no_update, set_props

from src.components.detail_panel import stadium_detail
from src.components.flow_layer import flows_for
from src.components.group_table import build_group_panel, group_rows, live_group_rows
from src.components.header_calendar import build_match_calendar
from src.components.layout import build_layout
from src.components.map_view import DARK_TILE, LIGHT_TILE, MARKER_TYPE, filter_pin, live_score_markers, pulse_markers
from src.data.distances import DistanceRepository
from src.data.flows import build_team_flows, team_cities
from src.data.groups import build_groups, group_for_team
from src.data.match_calendar import MatchCalendar
from src.data.matches import MatchRepository, matches_by_stadium
from src.components.formation_pitch import build_formation_panel, formation_title, pitch_src
from src.components.leaders_card import (
    build_leaders_card,
    leaders_columns,
    leaders_row_data,
)
from src.components.squad_table import build_squad_panel, squad_rows
from src.components.live_match_modal import build_modal, modal_body
from src.components.live_strip import overlay_style, strip_items
from src.components.team_kpis import build_kpi_strip, kpi_cards
from src.components.team_carousel import advance, build_team_carousel, carousel_view, center_team, team_order
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
from src.data.live.client import HighlightlyClient
from src.data.live.reconcile import build_stadium_index
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

TEAM_FLOWS = build_team_flows(MATCHES, VENUES, distances=DISTANCES)
TEAM_OPTIONS = grouped_team_options(sorted(TEAM_FLOWS))
TEAM_NAMES = team_order(TEAM_FLOWS)
GROUPS = build_groups(MATCHES)
SQUADS = SquadRepository(DATA_DIR / "squads.csv").load()
LINEUPS = LineupRepository(DATA_DIR / "estimated_starting_eleven.json").load()

STADIUM_TO_CITY = {v.stadium_name: v.city for v in VENUES}
MATCH_CALENDAR = MatchCalendar(MATCHES, STADIUM_TO_CITY, today=date.today())

STADIUM_INDEX = build_stadium_index(MATCHES)
# Load HIGHLIGHTLY_API_KEY (and any other vars) from a local .env so running
# `python app.py` picks up the key without a manual export. An already-exported
# value still wins (setdefault). Without a key, the app runs static-only.
load_env_file(Path(__file__).parent / ".env")
_API_KEY = os.environ.get("HIGHLIGHTLY_API_KEY")
# No-key mode: when the env var is unset the app runs purely on static data,
# so dev and the whole test suite work offline.
# Per-match player-stats cache (gitignored). The live_feed loop maintains it;
# team_leaders reads it for the leaders card.
PLAYER_STORE_PATH = DATA_DIR / "live_player_stats.csv"
LIVE = (
    LiveDataService(HighlightlyClient(api_key=_API_KEY), STADIUM_INDEX,
                    player_store=PLAYER_STORE_PATH)
    if _API_KEY else None
)


def flow_children(selected):
    return flows_for(selected, TEAM_FLOWS)

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
        rows = (live_group_rows(name, live_standings, app.get_asset_url)
                or group_rows(group, app.get_asset_url))
    return name, rows


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
    kpi_strip=build_kpi_strip(team_stats_payload(0)),
    leaders_panel=build_leaders_card(),
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
    Input({"type": MARKER_TYPE, "index": ALL}, "n_clicks"),
    State("user-tz", "data"),
    State("live-store", "data"),
    prevent_initial_call=True,
)
def open_stadium_drawer(n_clicks, user_tz, live):
    # user_tz is a State snapshot: if the tz probe hasn't resolved yet, the drawer falls back to venue-local time (window is brief, acceptable per design).
    # Ignore the callback firing when markers mount with n_clicks=None.
    if not any(n_clicks):
        return no_update, no_update, no_update, no_update
    triggered = ctx.triggered_id
    city = triggered.get("index") if isinstance(triggered, dict) else None
    opened, title, children = drawer_for_city(city, user_tz, live)
    # Opening the stadium drawer closes the filter drawer (both are left-side).
    return opened, title, children, (False if opened else no_update)


@callback(
    Output("filter-drawer", "opened"),
    Output("stadium-drawer", "opened", allow_duplicate=True),
    Input("filter-pin", "n_clicks"),
    prevent_initial_call=True,
)
def open_filter_drawer(n_clicks):
    if not n_clicks:
        return no_update, no_update
    return True, False  # open the filter drawer, close the stadium drawer


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
    Output("live-strip", "children"),
    Input("match-calendar", "value"),
    Input("live-store", "data"),
    State("user-tz", "data"),
)
def render_live_strip(selected_date, live, user_tz):
    fetch = (lambda d: LIVE.matches_on(d, time.monotonic())) if LIVE is not None else None
    matches = strip_day_matches(selected_date, date.today(), live, fetch)
    return strip_items({"matches": matches}, user_tz=user_tz)


@callback(
    Output("live-match-modal", "opened"),
    Output("live-match-modal", "children"),
    Input({"type": "live-strip-item", "index": ALL}, "n_clicks"),
    Input({"type": "open-live-modal", "index": ALL}, "n_clicks"),
    prevent_initial_call=True,
)
def open_live_modal(strip_clicks, drawer_clicks):
    clicks = (strip_clicks or []) + (drawer_clicks or [])
    if not any(c for c in clicks if c):
        return no_update, no_update
    triggered = ctx.triggered_id
    if not isinstance(triggered, dict):
        return no_update, no_update
    match_id = triggered["index"]
    now = time.monotonic()
    if LIVE is not None:
        match = LIVE.match_summary(match_id, now)
        events = LIVE.match_events(match_id, now)
        stats = LIVE.match_statistics(match_id, now)
        lineups = LIVE.match_lineups(match_id, now)
    else:
        match, events, stats, lineups = None, [], {}, {}
    return True, modal_body(match, events, stats, lineups)


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
    Output("filter-pin-layer", "children"),
    Input("mode-toggle", "checked"),
)
def toggle_filter_pin(team_mode):
    # Runs on initial load too, so a persisted Team mode hides the pin from the
    # first render. Re-seeding the pin in Time mode is harmless (Dash diffs the DOM).
    return [] if team_mode else [filter_pin()]


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
)
def update_kpi_strip(index):
    return kpi_cards(team_stats_payload(index))


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

def _backfill_player_stats():
    """One-time refresh of the player-stats cache from past scheduled dates.
    Idempotent: update_player_stats skips finished matches already on disk."""
    today = date.today()
    now = time.monotonic()
    for d in sorted({m.date for m in MATCHES if m.date <= today}):
        LIVE.update_player_stats(LIVE.matches_on(d.isoformat(), now), now)


# Always register the persistent WS callback so the client can always resolve it
# (a conditional registration leaves a connecting client with a callback the
# server doesn't know, which raises "Callback function not found"). When there's
# no API key the callback simply returns and the app stays on static data.
@callback(persistent=True)
async def live_feed():
    ws = ctx.websocket
    if ws is None or LIVE is None:
        return
    await asyncio.to_thread(_backfill_player_stats)
    while not ws.is_shutdown:
        now = asyncio.get_running_loop().time()
        snap = await asyncio.to_thread(LIVE.snapshot, date.today().isoformat(), now)
        set_props("live-store", {"data": snap})
        await asyncio.to_thread(LIVE.update_player_stats, snap["matches"], now)
        await asyncio.sleep(next_delay(snap))


if __name__ == "__main__":
    app.run(debug=True)
