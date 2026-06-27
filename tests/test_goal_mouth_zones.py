from src.data.live.goal_mouth_zones import (
    ON_TARGET, MARGINS, ZONE_MAP, classify_target, parse_shot_minute,
)


def test_all_six_grid_cells_map():
    assert classify_target("High Left") == "high_left"
    assert classify_target("High Centre") == "high_centre"
    assert classify_target("High Right") == "high_right"
    assert classify_target("Low Left") == "low_left"
    assert classify_target("Low Centre") == "low_centre"
    assert classify_target("Low Right") == "low_right"
    assert set(ON_TARGET) == {
        "high_left", "high_centre", "high_right",
        "low_left", "low_centre", "low_right",
    }


def test_near_miss_margins_including_quirks():
    assert classify_target("Close High") == "close_high"
    assert classify_target("CloseLeft") == "close_left"        # no space
    assert classify_target("Close Right") == "close_right"
    assert classify_target("Close Right And High") == "close_right_high"  # compound
    assert set(MARGINS) == {"close_high", "close_left",
                            "close_right", "close_right_high"}


def test_null_is_off_target():
    assert classify_target(None) == "off_target"


def test_unknown_is_other_never_dropped():
    assert classify_target("Top Bins") == "other"
    assert classify_target("") == "other"


def test_zone_map_has_no_string_split_dependency():
    # The compound value is a single key, not two tokens.
    assert ZONE_MAP["Close Right And High"] == "close_right_high"


def test_parse_shot_minute_orders_stoppage():
    assert parse_shot_minute("15'") == (15, 0)
    assert parse_shot_minute("45+1") == (45, 1)
    assert parse_shot_minute("90+3'") == (90, 3)
    assert parse_shot_minute(None) == (0, 0)
    assert parse_shot_minute("45'") < parse_shot_minute("45+1")
    assert parse_shot_minute("45+1") < parse_shot_minute("46'")
