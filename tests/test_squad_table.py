import dash_ag_grid as dag
import dash_mantine_components as dmc

from src.components.squad_table import (
    COL_DEFS, build_squad_panel, position_code, squad_rows,
)
from src.data.squads import Player, Squad


def _walk(node):
    yield node
    children = getattr(node, "children", None)
    if isinstance(children, (list, tuple)):
        for c in children:
            yield from _walk(c)
    elif children is not None:
        yield from _walk(children)


def _squad():
    return Squad("Canada", (
        Player(number=19, name="Alphonso Davies", position="Left-Back",
               dob="02/11/2000", age="25", club="Bayern Munich", height_m="1.83",
               foot="left", caps="58", goals="15", debut="14/06/2017",
               market_value="€40.00m"),
        Player(number=18, name="Owen Goodman", position="Goalkeeper",
               dob="27/11/2003", age="22", club="Barnsley FC", height_m="1.93",
               foot="left", caps="", goals="0", debut="01/04/2026",
               market_value="€550k"),
    ))


def test_position_code_maps_known_positions():
    assert position_code("Goalkeeper") == "GK"
    assert position_code("Centre-Back") == "CB"
    assert position_code("Defensive Midfield") == "DM"
    assert position_code("Second Striker") == "SS"


def test_position_code_unknown_falls_back():
    assert position_code("Sweeper") != ""


def test_squad_rows_shape_and_formatting():
    rows = squad_rows(_squad())
    assert len(rows) == 2
    davies = rows[0]
    assert davies["number"] == 19
    assert davies["name"] == "Alphonso Davies"
    assert davies["pos"] == "LB"
    assert davies["age"] == "25"
    assert davies["club"] == "Bayern Munich"
    assert davies["height"] == "1.83 m"
    assert davies["foot"] == "Left"
    assert davies["caps"] == "58"
    assert davies["value"] == "€40.00m"


def test_squad_rows_blank_caps_and_blank_height():
    rows = squad_rows(Squad("X", (
        Player(number=1, name="Z", position="Goalkeeper", dob="", age="",
               club="", height_m="", foot="", caps="", goals="0", debut="",
               market_value=""),
    )))
    assert rows[0]["caps"] == ""
    assert rows[0]["height"] == ""
    assert rows[0]["foot"] == ""


def test_col_defs_exclude_country_and_team_id():
    fields = {c.get("field") for c in COL_DEFS}
    assert "country" not in fields
    assert "team_id" not in fields
    assert {"number", "name", "pos", "value"} <= fields


def test_col_defs_pin_number_and_player_left():
    by_field = {c["field"]: c for c in COL_DEFS}
    assert by_field["number"].get("pinned") == "left"
    assert by_field["name"].get("pinned") == "left"


def test_build_squad_panel_has_grid_and_title():
    panel = build_squad_panel(_squad())
    grids = [n for n in _walk(panel) if isinstance(n, dag.AgGrid)]
    assert len(grids) == 1
    assert grids[0].id == "squad-grid"
    assert len(grids[0].rowData) == 2
    titles = [n for n in _walk(panel)
              if isinstance(n, dmc.Text) and getattr(n, "id", None) == "squad-table-title"]
    assert titles and titles[0].children == "Canada"


def test_build_squad_panel_none_is_empty():
    panel = build_squad_panel(None)
    grids = [n for n in _walk(panel) if isinstance(n, dag.AgGrid)]
    assert grids[0].rowData == []
