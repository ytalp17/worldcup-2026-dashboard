def test_app_builds_with_layout():
    import app

    assert app.app is not None
    # Layout is a MantineProvider built from the joined venues.
    assert app.app.layout.id == "mantine-provider"


def test_app_builds_sixteen_venues():
    import app

    assert len(app.VENUES) == 16


def test_drawer_for_city_returns_detail():
    import app

    opened, title, children = app.drawer_for_city("Dallas")
    assert opened is True
    assert title == "AT&T Stadium"  # official name from host-cities source
    assert children is not None


def test_drawer_for_unknown_city_stays_closed():
    import app

    opened, title, children = app.drawer_for_city("Atlantis")
    assert opened is False


def test_favicon_uses_white_fifa_logo():
    import app

    index = app.app.index_string
    assert 'rel="icon"' in index
    assert "fifa_logo_white.cc.svg" in index


def test_app_builds_team_flows_and_options():
    import app

    assert len(app.TEAM_FLOWS) == 48
    groups = [g["group"] for g in app.TEAM_OPTIONS]
    assert "South America" in groups


def test_app_flow_layer_children_for_selection():
    import dash_leaflet as dl

    import app

    children = app.flow_children(["Brazil"])
    assert any(isinstance(c, dl.Polyline) for c in children)
    assert app.flow_children([]) == []


def test_app_team_names_alphabetical_48():
    import app

    assert len(app.TEAM_NAMES) == 48
    assert app.TEAM_NAMES == sorted(app.TEAM_NAMES, key=str.casefold)


def test_team_stats_payload_for_centered_team():
    import app
    from src.data.team_stats import TeamStats

    stats = app.team_stats_payload(0)
    assert isinstance(stats, TeamStats)
    assert stats.squad_size > 0
    assert stats.value_display.startswith("€")
    # KPI strip rebuilds to 8 cards (incl. Form) for any team index.
    cards = app.kpi_cards(app.team_stats_payload(5), app.team_form_payload(5))
    assert len(cards) == 8


def test_team_form_payload_returns_wdl_tuple():
    import app

    form = app.team_form_payload(0)
    assert isinstance(form, tuple)
    # Without a live service (no API key in tests) there is no form yet, but the
    # shape is stable and every entry, when present, is a W/D/L token.
    assert all(r in ("W", "D", "L") for r in form)


def test_formation_panel_payload_is_theme_aware():
    import app

    disp, team, src_dark = app.formation_panel_payload(0, True)
    src_light = app.formation_panel_payload(0, False)[2]
    # The centred team at index 0 (alphabetical) has a hyphenated formation
    # and a theme-correct pitch image src.
    assert "-" in disp
    assert team == app.center_team(app.TEAM_NAMES, 0)
    # src carries a ?v=<mtime> cache-buster, so compare the path portion.
    assert src_dark.split("?")[0].endswith("-dark.png")
    assert src_light.split("?")[0].endswith("-light.png")


def test_flow_children_for_mode_team_uses_centered_team():
    import dash_leaflet as dl

    import app

    idx = app.TEAM_NAMES.index("Brazil")
    # Team mode: filter value is ignored; centered team's flow is drawn.
    children = app.flow_children_for_mode(True, ["Argentina"], idx)
    assert any(isinstance(c, dl.Polyline) for c in children)


def test_flow_children_for_mode_time_uses_filter():
    import dash_leaflet as dl

    import app

    children = app.flow_children_for_mode(False, ["Brazil"], 0)
    assert any(isinstance(c, dl.Polyline) for c in children)
    assert app.flow_children_for_mode(False, [], 0) == []


def test_pulse_children_for_mode_team_pulses_centered_team_cities():
    import app

    idx = app.TEAM_NAMES.index("Brazil")
    rings = app.pulse_children_for_mode(True, None, idx)
    # Brazil plays three group-stage matches → up to three distinct host cities.
    assert 1 <= len(rings) <= 3


def test_pulse_children_for_mode_time_uses_date_logic():
    import app

    # An out-of-tournament / None date yields no pulses in Time mode.
    assert app.pulse_children_for_mode(False, None, 0) == []


def test_app_layout_contains_carousel_and_mode_switch():
    import app

    def walk(node):
        yield node
        ch = getattr(node, "children", None)
        if isinstance(ch, (list, tuple)):
            for c in ch:
                yield from walk(c)
        elif ch is not None:
            yield from walk(ch)

    ids = {
        nid for n in walk(app.app.layout)
        if isinstance((nid := getattr(n, "id", None)), str)
    }
    assert "team-carousel" in ids
    assert "mode-toggle" in ids
    assert "carousel-index" in ids


def test_app_registers_mode_callbacks():
    import app
    import dash._callback

    outputs = set()
    # Dash 2.x registers module-level @callback decorators into GLOBAL_CALLBACK_MAP,
    # not app.callback_map (which stays empty until a request triggers compilation).
    cb_map = dash._callback.GLOBAL_CALLBACK_MAP
    for cb in cb_map.values():
        outs = cb["output"] if isinstance(cb["output"], list) else [cb["output"]]
        for o in outs:
            outputs.add(str(o))
    joined = " ".join(outputs)
    assert "carousel-index.data" in joined
    assert "map-controls-overlay.style" in joined
    assert "carousel-wrapper.style" in joined
    assert "flow-layer.children" in joined
    assert "pulse-layer.children" in joined
    # Every ag-grid follows the color scheme; the leaders grid's theme swap was
    # missing, leaving it dark-themed (unreadable) in light mode.
    assert "leaders-grid.className" in joined


def test_active_cities_decider_threads_user_tz():
    import app

    # In Time mode, an unknown/None tz keeps the venue-date pulse behavior.
    assert app.pulse_children_for_mode(False, "2026-06-11", 0) is not None


def test_drawer_for_city_accepts_user_tz():
    import app

    opened, title, children = app.drawer_for_city("Dallas", "Asia/Tokyo")
    assert opened is True
    assert children is not None


def test_group_panel_payload_for_group_a_team():
    import app

    idx = app.TEAM_NAMES.index("Mexico")
    name, rows = app.group_panel_payload(idx)
    assert name == "Group A"
    assert [r["rank"] for r in rows] == [1, 2, 3, 4]
    assert rows[0]["team"] == "Mexico"
    # Korea Republic is in Group A and shows under its display name.
    assert any(r["team"] == "South Korea" for r in rows)


def test_group_panel_payload_handles_none_index():
    import app

    name, rows = app.group_panel_payload(None)
    # index 0 resolves to the first team alphabetically; it has a real group.
    assert name != "—"
    assert len(rows) == 4


def test_squad_panel_payload_returns_name_and_rows():
    import app

    name, rows = app.squad_panel_payload(0)
    assert isinstance(name, str) and name != ""
    assert isinstance(rows, list) and len(rows) > 0
    assert "name" in rows[0] and "pos" in rows[0]


def test_squad_panel_payload_matches_centered_team():
    import app
    from src.components.team_carousel import center_team

    name, rows = app.squad_panel_payload(0)
    expected = center_team(app.TEAM_NAMES, 0)
    assert name == expected


def test_leaders_payload_columns_and_team():
    import app
    rows, cols, team = app.leaders_payload("Goals", 0)
    assert team == app.center_team(app.TEAM_NAMES, 0)
    assert [c["headerName"] for c in cols] == ["#", "Player", "Goals", "Apps"]
    assert isinstance(rows, list)   # empty in no-key test env, but well-formed


def test_leaders_payload_cards_tab_splits_yellow_red():
    import app
    _rows, cols, _team = app.leaders_payload("Cards", 3)
    assert [c["headerName"] for c in cols] == ["#", "Player", "🟨", "🟥", "Apps"]


def test_tournament_grid_payload_team_attack():
    import app
    # Standings was removed from the Team scope; Attack & xG is the first team tab.
    rows, cols = app.tournament_grid_payload("Team", "Attack & xG", {"standings": {}})
    assert [c["headerName"] for c in cols][:2] == ["Team", "Goals"]
    assert isinstance(rows, list)


def test_tournament_grid_payload_players_goals():
    import app
    rows, cols = app.tournament_grid_payload("Players", "Goals", {})
    assert [c["headerName"] for c in cols] == ["#", "Player", "Team", "Goals", "Ap"]
    assert isinstance(rows, list)


def test_official_team_maps_live_names_to_logo_filenames():
    import app
    # Live-feed spellings must resolve to the official country_logos filenames.
    assert app.official_team("Czech Republic") == "Czechia"
    assert app.official_team("South Korea") == "Korea Republic"
    assert app.official_team("Bosnia & Herzegovina") == "Bosnia and Herzegovina"
    assert app.official_team("Brazil") == "Brazil"          # already official
    assert app.official_team("Nowhere FC") == "Nowhere FC"  # unknown: passthrough


def test_attach_team_flags_adds_flag_url_and_display_name():
    import app
    rows = app.attach_team_flags([
        {"team": "Korea Republic", "goals": 2},
        {"team": "Bosnia and Herzegovina", "goals": 1},
    ])
    # Flag filename uses the canonical name (matches country_logos/<canonical>.svg);
    # the displayed team uses the friendly display name.
    assert rows[0]["flag"].endswith("country_logos/Korea Republic.svg")
    assert rows[0]["team"] == "South Korea"
    assert rows[0]["goals"] == 2                       # other fields preserved
    assert rows[1]["flag"].endswith("country_logos/Bosnia and Herzegovina.svg")
    assert rows[1]["team"] == "Bosnia & Herzegovina"


def test_app_layout_has_tournament_drawer():
    import app
    from dash_mantine_components import Drawer

    def walk(n):
        yield n
        ch = getattr(n, "children", None)
        if isinstance(ch, (list, tuple)):
            for c in ch:
                yield from walk(c)
        elif ch is not None:
            yield from walk(ch)

    ids = {n.id for n in walk(app.app.layout) if isinstance(n, Drawer)}
    assert "tournament-drawer" in ids


# ---------------------------------------------------------------------------
# _modal_match_id — only open the live-match modal on a REAL click, never when
# the venue/stadium drawer dynamically mounts new match cards (regression).
# ---------------------------------------------------------------------------

def test_modal_match_id_opens_on_real_click():
    import app
    trig = {"type": "open-live-modal", "index": 42}
    assert app._modal_match_id(trig, 1) == 42


def test_modal_match_id_ignores_card_mount_with_no_click():
    import app
    # Opening a drawer mounts new cards → their n_clicks value is None/0.
    trig = {"type": "open-live-modal", "index": 42}
    assert app._modal_match_id(trig, None) is None
    assert app._modal_match_id(trig, 0) is None


def test_modal_match_id_ignores_non_pattern_trigger():
    import app
    assert app._modal_match_id("scheme-toggle", 1) is None
    assert app._modal_match_id(None, 1) is None


# ---------------------------------------------------------------------------
# Two-phase modal open: target store + id extraction
# ---------------------------------------------------------------------------

def test_layout_has_live_modal_target_store():
    import app
    from dash import dcc

    def walk(n):
        yield n
        ch = getattr(n, "children", None)
        if isinstance(ch, (list, tuple)):
            for c in ch:
                yield from walk(c)
        elif ch is not None:
            yield from walk(ch)

    store_ids = {n.id for n in walk(app.app.layout) if isinstance(n, dcc.Store)}
    assert "live-modal-target" in store_ids


def test_modal_target_id_extracts_match_id():
    import app
    assert app._modal_target_id({"id": 7, "t": 1.0}) == 7
    assert app._modal_target_id(None) is None
    assert app._modal_target_id({}) is None


# ---------------------------------------------------------------------------
# Task 7: stage filter wiring — group_only reaches both leader calls
# ---------------------------------------------------------------------------

class _FakeLive:
    def __init__(self):
        self.calls = []

    def tournament_team_leaders(self, standings=None, group_only=False):
        self.calls.append(("team", group_only))
        return {}

    def tournament_player_leaders(self, group_only=False):
        self.calls.append(("player", group_only))
        return {}


def test_tournament_grid_payload_passes_group_only(monkeypatch):
    import app
    fake = _FakeLive()
    monkeypatch.setattr(app, "LIVE", fake)
    app.tournament_grid_payload("Team", "Attack & xG", {"standings": {}},
                                group_only=True)
    assert ("team", True) in fake.calls
    assert ("player", True) in fake.calls


def test_tournament_grid_payload_defaults_group_only_false(monkeypatch):
    import app
    fake = _FakeLive()
    monkeypatch.setattr(app, "LIVE", fake)
    app.tournament_grid_payload("Team", "Attack & xG", {"standings": {}})
    assert ("team", False) in fake.calls


def test_update_tournament_grid_callback_wires_switch_to_grid(monkeypatch):
    # The stage Switch's `checked` state must drive the grid: on -> group_only,
    # off -> all. Calls the real callback and asserts the flag reaches LIVE.
    import app
    fake = _FakeLive()
    monkeypatch.setattr(app, "LIVE", fake)

    rows, cols = app.update_tournament_grid("Team", "Attack & xG", True,
                                            {"standings": {}})
    assert ("team", True) in fake.calls and ("player", True) in fake.calls
    assert cols  # columnDefs returned for the grid

    fake.calls.clear()
    app.update_tournament_grid("Team", "Attack & xG", False, {"standings": {}})
    assert ("team", False) in fake.calls and ("player", False) in fake.calls


# ---------------------------------------------------------------------------
# Task 9: goal-mouth payload helpers
# ---------------------------------------------------------------------------
import plotly.graph_objects as go


class _FakeGMLive:
    """Stand-in LIVE exposing team_goal_mouth with a fixed aggregate."""
    def __init__(self):
        from src.data.live.shots import ShotRecord
        from src.data.live.goal_mouth import aggregate_goal_mouth
        self._agg = aggregate_goal_mouth([
            ShotRecord(1, "England", "A", "10'", "Goal", "Low Centre"),
            ShotRecord(1, "England", "B", "20'", "Saved", "Low Centre")])
        self.calls = []

    def team_goal_mouth(self, team, group_only=False):
        self.calls.append((team, group_only))
        return self._agg


def test_goal_mouth_figure_payload_builds_figure(monkeypatch):
    import app
    monkeypatch.setattr(app, "LIVE", _FakeGMLive())
    fig = app.goal_mouth_figure_payload(0, {"ok": True}, dark=True)
    assert isinstance(fig, go.Figure)
    assert app.LIVE.calls and isinstance(app.LIVE.calls[0][0], str)


def test_goal_mouth_figure_payload_no_live_is_empty(monkeypatch):
    import app
    monkeypatch.setattr(app, "LIVE", None)
    fig = app.goal_mouth_figure_payload(0, None, dark=True)
    assert isinstance(fig, go.Figure)          # empty-but-valid frame




def test_goal_mouth_drawer_payload_lists_zone(monkeypatch):
    import app
    monkeypatch.setattr(app, "LIVE", _FakeGMLive())
    title, children = app.goal_mouth_drawer_payload(
        "low_centre", 0, {"ok": True}, dark=True)
    assert "Low Centre" in title
    assert isinstance(children, list) and children
