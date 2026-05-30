from __future__ import annotations

import json
from pathlib import Path

from dash import ALL, Dash, Input, Output, callback, clientside_callback, ctx, no_update

from src.components.detail_panel import stadium_detail
from src.components.filter_panel import legend
from src.components.flow_layer import flows_for
from src.components.layout import build_layout
from src.components.map_view import DARK_TILE, LIGHT_TILE, MARKER_TYPE
from src.data.altitudes import AltitudeRepository
from src.data.distances import DistanceRepository
from src.data.flows import build_team_flows
from src.data.host_cities import HostCityRepository
from src.data.matches import MatchRepository, matches_by_stadium
from src.data.stadiums import StadiumRepository
from src.data.team_continents import grouped_team_options
from src.data.venues import build_venues

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


def flow_children(selected):
    return flows_for(selected, TEAM_FLOWS)

app = Dash(__name__)
app.title = "FIFA World Cup 2026"
app.layout = build_layout(VENUES, TEAM_OPTIONS, TEAM_FLOWS)

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


def drawer_for_city(city: str | None):
    """Compute the (opened, title, children) drawer state for a clicked city.

    Returns a closed, empty drawer for unknown/None cities.
    """
    venue = VENUES_BY_CITY.get(city) if city else None
    if venue is None:
        return False, no_update, no_update
    matches = MATCHES_BY_STADIUM.get(venue.stadium_name, [])
    return True, venue.official_name, stadium_detail(venue, matches)


@callback(
    Output("stadium-drawer", "opened"),
    Output("stadium-drawer", "title"),
    Output("stadium-drawer", "children"),
    Output("filter-drawer", "opened", allow_duplicate=True),
    Input({"type": MARKER_TYPE, "index": ALL}, "n_clicks"),
    prevent_initial_call=True,
)
def open_stadium_drawer(n_clicks):
    # Ignore the callback firing when markers mount with n_clicks=None.
    if not any(n_clicks):
        return no_update, no_update, no_update, no_update
    triggered = ctx.triggered_id
    city = triggered.get("index") if isinstance(triggered, dict) else None
    opened, title, children = drawer_for_city(city)
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
    Output("filter-legend", "children"),
    Input("team-filter", "value"),
)
def update_flows(selected):
    return flow_children(selected), legend(selected, TEAM_FLOWS)


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

if __name__ == "__main__":
    app.run(debug=True)
