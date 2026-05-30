from __future__ import annotations

CONTINENT_ORDER = [
    "North America",
    "South America",
    "Europe",
    "Africa",
    "Asia",
    "Oceania",
]

TEAM_CONTINENT: dict[str, str] = {
    # North America
    "Canada": "North America", "Curaçao": "North America", "Haiti": "North America",
    "Mexico": "North America", "Panama": "North America", "USA": "North America",
    # South America
    "Argentina": "South America", "Brazil": "South America", "Colombia": "South America",
    "Ecuador": "South America", "Paraguay": "South America", "Uruguay": "South America",
    # Europe
    "Austria": "Europe", "Belgium": "Europe", "Bosnia and Herzegovina": "Europe",
    "Croatia": "Europe", "Czechia": "Europe", "England": "Europe", "France": "Europe",
    "Germany": "Europe", "Netherlands": "Europe", "Norway": "Europe", "Portugal": "Europe",
    "Scotland": "Europe", "Spain": "Europe", "Sweden": "Europe", "Switzerland": "Europe",
    "Türkiye": "Europe",
    # Africa
    "Algeria": "Africa", "Cabo Verde": "Africa", "Congo DR": "Africa",
    "Côte d'Ivoire": "Africa", "Egypt": "Africa", "Ghana": "Africa", "Morocco": "Africa",
    "Senegal": "Africa", "South Africa": "Africa", "Tunisia": "Africa",
    # Asia
    "IR Iran": "Asia", "Iraq": "Asia", "Japan": "Asia", "Jordan": "Asia",
    "Korea Republic": "Asia", "Qatar": "Asia", "Saudi Arabia": "Asia", "Uzbekistan": "Asia",
    # Oceania
    "Australia": "Oceania", "New Zealand": "Oceania",
}


def continent_for(team: str) -> str:
    try:
        return TEAM_CONTINENT[team]
    except KeyError as exc:
        raise ValueError(f"No continent mapped for team {team!r}") from exc


def grouped_team_options(teams: list[str]) -> list[dict]:
    """DMC MultiSelect grouped data, continents in CONTINENT_ORDER, teams sorted."""
    options: list[dict] = []
    for continent in CONTINENT_ORDER:
        items = sorted(t for t in teams if TEAM_CONTINENT.get(t) == continent)
        if items:
            options.append(
                {"group": continent, "items": [{"value": t, "label": t} for t in items]}
            )
    return options
