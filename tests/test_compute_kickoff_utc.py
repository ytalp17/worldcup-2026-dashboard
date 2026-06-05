from scripts.compute_kickoff_utc import to_utc


def test_to_utc_resolves_mexico_city_no_dst():
    # America/Mexico_City is UTC-6 year-round (no DST since 2022): 13:00 -> 19:00Z.
    assert to_utc("2026-06-11", "13:00", "America/Mexico_City") == "2026-06-11T19:00:00+00:00"


def test_to_utc_resolves_us_pacific_dst():
    # America/Los_Angeles in June is PDT = UTC-7: 18:00 -> 01:00Z next day.
    assert to_utc("2026-06-12", "18:00", "America/Los_Angeles") == "2026-06-13T01:00:00+00:00"
