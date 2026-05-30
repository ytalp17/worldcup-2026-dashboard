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
