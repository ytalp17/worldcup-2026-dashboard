from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import dash
from dash import ALL, Dash, Input, Output, State, callback, clientside_callback, ctx, no_update

from src.components.detail_panel import stadium_detail
from src.components.filter_panel import legend
from src.components.flow_layer import flows_for
from src.components.group_table import build_group_panel, group_rows
from src.components.header_calendar import build_match_calendar
from src.components.layout import build_layout
from src.components.map_view import DARK_TILE, LIGHT_TILE, MARKER_TYPE, filter_pin, pulse_markers
from src.data.altitudes import AltitudeRepository
from src.data.distances import DistanceRepository
from src.data.flows import build_team_flows, team_cities
from src.data.groups import build_groups, group_for_team
from src.data.host_cities import HostCityRepository
from src.data.match_calendar import MatchCalendar
from src.data.matches import MatchRepository, matches_by_stadium
from src.data.stadiums import StadiumRepository
from src.components.team_carousel import advance, build_team_carousel, carousel_view, center_team, team_order
from src.data.team_continents import grouped_team_options
from src.data.venues import build_venues

# dash-mantine-components 2.x is built on Mantine 8 / React 18 (e.g. useId).
# The runtime (conda base) pairs it with Dash 2.18, which still defaults to
# React 16, so we must opt into React 18 or the UI fails with
# "(0 , r.useId) is not a function".
dash._dash_renderer._set_react_version("18.2.0")

DATA_DIR = Path(__file__).parent / "assets" / "data"
IMAGE_DIR = Path(__file__).parent / "assets" / "stadiums"

CITIES = HostCityRepository(DATA_DIR / "fifa_2026_host_cities.csv").load()
STADIUMS = StadiumRepository(DATA_DIR / "fifa_wc2026_stadiums.csv").load()
ALTITUDES = AltitudeRepository(DATA_DIR / "wc2026_stadium_altitude.csv").load()
DISTANCES = DistanceRepository(DATA_DIR / "team_distances.csv").load()
VENUES = build_venues(CITIES, STADIUMS, IMAGE_DIR, ALTITUDES)
VENUES_BY_CITY = {v.city: v for v in VENUES}

MATCHES = MatchRepository(DATA_DIR / "wc2026_matches.csv").load()
MATCHES_BY_STADIUM = matches_by_stadium(MATCHES)

TEAM_FLOWS = build_team_flows(MATCHES, VENUES, distances=DISTANCES)
TEAM_OPTIONS = grouped_team_options(sorted(TEAM_FLOWS))
TEAM_NAMES = team_order(TEAM_FLOWS)
GROUPS = build_groups(MATCHES)

STADIUM_TO_CITY = {v.stadium_name: v.city for v in VENUES}
MATCH_CALENDAR = MatchCalendar(MATCHES, STADIUM_TO_CITY, today=date.today())


def flow_children(selected):
    return flows_for(selected, TEAM_FLOWS)

app = Dash(__name__)
app.title = "FIFA World Cup 2026"
TEAM_CAROUSEL = build_team_carousel(TEAM_NAMES, app.get_asset_url, index=0)


def group_panel_payload(index):
    """(group_name, rowData) for the centred team at `index`. Used by the
    content callback and the initial panel render."""
    team = center_team(TEAM_NAMES, index or 0)
    group = group_for_team(GROUPS, team)
    name = group.name if group else "—"
    rows = group_rows(group, app.get_asset_url) if group else []
    return name, rows


app.layout = build_layout(
    VENUES,
    TEAM_OPTIONS,
    TEAM_FLOWS,
    match_calendar=build_match_calendar(MATCH_CALENDAR),
    team_carousel=TEAM_CAROUSEL,
    group_panel=build_group_panel(group_for_team(GROUPS, center_team(TEAM_NAMES, 0)), app.get_asset_url),
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


def drawer_for_city(city: str | None, user_tz: str | None = None):
    """Compute the (opened, title, children) drawer state for a clicked city."""
    venue = VENUES_BY_CITY.get(city) if city else None
    if venue is None:
        return False, no_update, no_update
    matches = MATCHES_BY_STADIUM.get(venue.stadium_name, [])
    return True, venue.official_name, stadium_detail(venue, matches, user_tz)


@callback(
    Output("stadium-drawer", "opened"),
    Output("stadium-drawer", "title"),
    Output("stadium-drawer", "children"),
    Output("filter-drawer", "opened", allow_duplicate=True),
    Input({"type": MARKER_TYPE, "index": ALL}, "n_clicks"),
    State("user-tz", "data"),
    prevent_initial_call=True,
)
def open_stadium_drawer(n_clicks, user_tz):
    # user_tz is a State snapshot: if the tz probe hasn't resolved yet, the drawer falls back to venue-local time (window is brief, acceptable per design).
    # Ignore the callback firing when markers mount with n_clicks=None.
    if not any(n_clicks):
        return no_update, no_update, no_update, no_update
    triggered = ctx.triggered_id
    city = triggered.get("index") if isinstance(triggered, dict) else None
    opened, title, children = drawer_for_city(city, user_tz)
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
    Input("team-filter", "value"),
    Input("carousel-index", "data"),
)
def update_flow_layer(team_mode, filter_value, index):
    return flow_children_for_mode(team_mode, filter_value, index)


@callback(
    Output("filter-legend", "children"),
    Input("team-filter", "value"),
)
def update_filter_legend(selected):
    return legend(selected, TEAM_FLOWS)


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
)
def update_group_panel(index):
    name, rows = group_panel_payload(index)
    return rows, name


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
# mode (no modifier) collapses the grid so the map card fills the screen. After
# the layout change, dispatch a window resize so Leaflet runs invalidateSize()
# and re-tiles the resized map card.
_PANEL_JS = """
(checked) => {
    setTimeout(() => window.dispatchEvent(new Event('resize')), 350);
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

if __name__ == "__main__":
    app.run(debug=True)
