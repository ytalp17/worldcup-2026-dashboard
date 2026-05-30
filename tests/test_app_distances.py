import app


def test_app_flows_carry_distance():
    assert app.TEAM_FLOWS["Brazil"].distance_km > 0
    assert hasattr(app, "DISTANCES")
    assert len(app.DISTANCES) == 48
