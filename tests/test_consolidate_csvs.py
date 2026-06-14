from pathlib import Path

import pandas as pd

DATA = Path(__file__).parent.parent / "assets" / "data"


def test_venues_csv_shape_and_join():
    df = pd.read_csv(DATA / "venues.csv")
    assert len(df) == 16
    expected = {
        "city", "country", "official_name", "stadium_name", "location",
        "capacity", "opened", "info", "image_filename", "image_url",
        "latitude", "longitude", "altitude_m", "altitude_ft", "altitude_tier",
        "region_cluster", "airport_code", "timezone", "tz_label",
    }
    assert set(df.columns) == expected
    dallas = df[df["city"] == "Dallas"].iloc[0]
    assert dallas["stadium_name"] == "Dallas Stadium"
    assert dallas["official_name"] == "AT&T Stadium"
    assert int(dallas["capacity"]) == 94000
    assert dallas["timezone"] == "America/Chicago"
    assert dallas["tz_label"] == "Central Time"
    assert int(dallas["altitude_m"]) == 183
    assert dallas["airport_code"] == "DAL"
    assert "San Francisco" in set(df["city"])
    assert df["airport_code"].notna().all()


def test_teams_csv_shape_and_codes():
    df = pd.read_csv(DATA / "teams.csv")
    assert len(df) == 48
    assert set(df.columns) == {
        "team", "continent", "distance_km", "code", "confederation",
        "coach", "coach_nationality", "coach_since",
    }
    assert df["code"].notna().all() and (df["code"].str.len() == 3).all()
    by_team = df.set_index("team")
    assert by_team.loc["Korea Republic", "code"] == "KOR"
    assert by_team.loc["USA", "code"] == "USA"
    assert by_team.loc["Côte d'Ivoire", "code"] == "CIV"
    assert by_team.loc["Türkiye", "code"] == "TUR"
    assert by_team.loc["Scotland", "code"] == "SCO"
    assert by_team.loc["Mexico", "confederation"] == "CONCACAF"
    assert by_team.loc["Brazil", "coach"] == "Carlo Ancelotti"


def test_matches_and_squads_carried_over():
    matches = pd.read_csv(DATA / "matches.csv")
    assert len(matches) == 104
    assert list(matches.columns)[:3] == ["match_number", "home_team", "away_team"]
    squads = pd.read_csv(DATA / "squads.csv")
    assert len(squads) == 1247
    assert "country" in squads.columns and "name" in squads.columns
