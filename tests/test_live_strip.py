from __future__ import annotations

from src.components.live_strip import abbr, overlay_style, strip_items


def test_overlay_style_hidden_off_calendar_view():
    assert overlay_style(visible=True).get("display") != "none"
    assert overlay_style(visible=False)["display"] == "none"
    assert overlay_style(visible=True)["position"] == "fixed"   # base style kept


def test_abbr_maps_names_aliases_and_falls_back():
    assert abbr("Argentina") == "ARG"
    assert abbr("USA") == "USA"
    assert abbr("South Korea") == "KOR"   # live-API alias -> canonical -> code
    assert abbr("Côte d'Ivoire") == "CIV"
    assert abbr("Atlantis FC") == "Atlantis FC"   # unknown -> original


def _ids(items):
    return [it.to_plotly_json()["props"]["id"]["index"] for it in items]


def test_strip_items_one_per_match_with_match_id():
    live = {"matches": [
        {"match_id": 1, "home": "Brazil", "away": "Mexico", "home_score": 2,
         "away_score": 1, "state": "live", "is_live": True},
        {"match_id": 2, "home": "USA", "away": "Canada", "home_score": None,
         "away_score": None, "state": "scheduled", "is_live": False},
    ]}
    items = strip_items(live)
    assert len(items) == 2
    assert _ids(items) == [1, 2]
    blob = str([it.to_plotly_json() for it in items])
    assert "BRA" in blob and "MEX" in blob       # abbreviations, not full names
    assert "Brazil" not in blob and "Mexico" not in blob
    assert "2" in blob and "1" in blob          # live score shown
    assert "LIVE" in blob.upper()                # live badge for match 1


def test_strip_items_empty_when_no_matches():
    assert strip_items({"matches": []}) == []
    assert strip_items(None) == []
