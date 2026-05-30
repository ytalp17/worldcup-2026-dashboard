from __future__ import annotations

from pathlib import Path

from dash import Dash, Input, Output, clientside_callback

from src.components.layout import build_layout
from src.data.host_cities import HostCityRepository

CSV_PATH = Path(__file__).parent / "assets" / "data" / "fifa_2026_host_cities.csv"

CITIES = HostCityRepository(CSV_PATH).load()

app = Dash(__name__)
app.title = "FIFA World Cup 2026"
app.layout = build_layout(CITIES)

# Flip the document color scheme when the switch toggles (checked => dark).
clientside_callback(
    """
    (checked) => {
        document.documentElement.setAttribute(
            'data-mantine-color-scheme', checked ? 'dark' : 'light'
        );
        return window.dash_clientside.no_update;
    }
    """,
    Output("color-scheme-toggle", "id"),
    Input("color-scheme-toggle", "checked"),
)

if __name__ == "__main__":
    app.run(debug=True)
