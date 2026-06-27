"""Pure domain model for the goal-mouth map: the explicit goalTarget→region
lookup and a sortable minute parser. No I/O, no Plotly, no Dash."""
from __future__ import annotations

# On-target grid is 2x3: rows {High, Low} x cols {Left, Centre, Right}.
ON_TARGET = ["high_left", "high_centre", "high_right",
             "low_left", "low_centre", "low_right"]

# Near-miss margins outside the frame (only these four ever occur).
MARGINS = ["close_high", "close_left", "close_right", "close_right_high"]

# The ONLY place goalTarget strings are interpreted. Never string-split — the
# compound "Close Right And High" and the space-less "CloseLeft" are explicit keys.
ZONE_MAP = {
    "High Left": "high_left", "High Centre": "high_centre", "High Right": "high_right",
    "Low Left": "low_left", "Low Centre": "low_centre", "Low Right": "low_right",
    "Close High": "close_high", "CloseLeft": "close_left",
    "Close Right": "close_right", "Close Right And High": "close_right_high",
}


def classify_target(goal_target: str | None) -> str:
    """None -> 'off_target'; a known string -> its region id; anything else ->
    'other' (a visible bucket, never silently dropped)."""
    if goal_target is None:
        return "off_target"
    return ZONE_MAP.get(goal_target, "other")


def parse_shot_minute(time_str: str | None) -> tuple[int, int]:
    """'15'' -> (15, 0); '45+1' -> (45, 1). Returns (base, extra) so stoppage
    time sorts after its base minute. Defensive: bad input -> (0, 0)."""
    if not time_str:
        return (0, 0)
    s = time_str.strip().rstrip("'").strip()
    base, _, extra = s.partition("+")
    try:
        return (int(base or 0), int(extra or 0))
    except ValueError:
        return (0, 0)
