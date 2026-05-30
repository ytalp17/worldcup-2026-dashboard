def test_app_builds_with_layout():
    import app

    assert app.app is not None
    # Layout is a MantineProvider instance built from the loaded cities.
    assert app.app.layout.id == "mantine-provider"


def test_app_loads_sixteen_cities():
    import app

    assert len(app.CITIES) == 16
