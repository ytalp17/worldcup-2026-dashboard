from __future__ import annotations

import json
from pathlib import Path

import dash
from dash import ALL, Dash, Input, Output, callback, clientside_callback, ctx, no_update

from src.components.detail_panel import stadium_detail
from src.components.layout import build_layout
from src.components.map_view import DARK_TILE, LIGHT_TILE, MARKER_TYPE
from src.data.host_cities import HostCityRepository
from src.data.matches import MatchRepository, matches_by_stadium
from src.data.stadiums import StadiumRepository
from src.data.venues import build_venues

# dash-mantine-components 0.15.x is built on Mantine 7 / React 18 and uses
# React 18-only APIs (e.g. useId). Dash still defaults to React 16, so we must
# opt into React 18 before the app is created or the UI fails to render with
# "(0 , r.useId) is not a function".
dash._dash_renderer._set_react_version("18.2.0")

DATA_DIR = Path(__file__).parent / "assets" / "data"
IMAGE_DIR = Path(__file__).parent / "assets" / "stadiums"

CITIES = HostCityRepository(DATA_DIR / "fifa_2026_host_cities.csv").load()
STADIUMS = StadiumRepository(DATA_DIR / "fifa_wc2026_stadiums.csv").load()
VENUES = build_venues(CITIES, STADIUMS, IMAGE_DIR)
VENUES_BY_CITY = {v.city: v for v in VENUES}

MATCHES = MatchRepository(DATA_DIR / "wc2026_matches.csv").load()
MATCHES_BY_STADIUM = matches_by_stadium(MATCHES)

app = Dash(__name__)
app.title = "FIFA World Cup 2026"
app.layout = build_layout(VENUES)

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
    Input({"type": MARKER_TYPE, "index": ALL}, "n_clicks"),
    prevent_initial_call=True,
)
def open_stadium_drawer(n_clicks):
    # Ignore the callback firing when markers mount with n_clicks=None.
    if not any(n_clicks):
        return no_update, no_update, no_update
    triggered = ctx.triggered_id
    city = triggered.get("index") if isinstance(triggered, dict) else None
    return drawer_for_city(city)


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
