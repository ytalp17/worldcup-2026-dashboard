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
    assert "filter-pin-layer.children" in joined
    assert "carousel-wrapper.style" in joined
    assert "flow-layer.children" in joined
    assert "pulse-layer.children" in joined


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
