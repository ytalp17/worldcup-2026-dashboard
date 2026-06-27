"""Position-aware assignment of starting-XI players to formation slots.

The slot coordinates used here are captured verbatim from
``mplsoccer.Pitch(pitch_type="opta").get_formation(...)`` so these tests need
neither mplsoccer nor scipy-via-mplsoccer wiring — just the pure module.
"""
from __future__ import annotations

from src.data.formation_assign import (
    NATURAL_POSITIONS,
    assign_xi_to_slots,
    natural_xy,
)

# mplsoccer opta slots for 4-3-3, in get_formation() order (GK first).
# (name kept only as a comment for the reader; the function takes (x, y).)
SLOTS_433 = [
    (12, 50),  # GK
    (27, 12),  # RB
    (27, 38),  # RCB
    (27, 62),  # LCB
    (27, 88),  # LB
    (42, 50),  # CDM
    (58, 30),  # RCM
    (58, 70),  # LCM
    (73, 10),  # RW
    (73, 90),  # LW
    (88, 50),  # ST
]

# Argentina's real estimated XI (surname, shirt number) and the real positions
# from squads.csv keyed by shirt number.
ARG_XI = [
    ("Martínez", 23),
    ("Martínez", 6),
    ("Molina", 26),
    ("Otamendi", 19),
    ("Tagliafico", 3),
    ("De Paul", 7),
    ("Fernández", 24),
    ("González", 15),
    ("Mac Allister", 20),
    ("Álvarez", 9),
    ("Messi", 10),
]
ARG_POSITIONS = {
    23: "Goalkeeper",
    6: "Centre-Back",
    26: "Right-Back",
    19: "Centre-Back",
    3: "Left-Back",
    7: "Central Midfield",
    24: "Central Midfield",
    15: "Left Winger",
    20: "Central Midfield",
    9: "Centre-Forward",
    10: "Right Winger",
}


class TestNaturalXY:
    def test_known_positions_map_to_expected_zones(self):
        # Defenders sit deep (low x), forwards high (high x).
        assert natural_xy("Goalkeeper")[0] < 20
        assert natural_xy("Centre-Back")[0] < 35
        assert natural_xy("Central Midfield")[0] == NATURAL_POSITIONS["Central Midfield"][0]
        assert natural_xy("Centre-Forward")[0] > 80

    def test_lateral_orientation_matches_mplsoccer(self):
        # opta width: low y = right side, high y = left side.
        assert natural_xy("Right-Back")[1] < 50
        assert natural_xy("Left-Back")[1] > 50
        assert natural_xy("Right Winger")[1] < 50
        assert natural_xy("Left Winger")[1] > 50

    def test_unknown_position_falls_back_to_centre(self):
        assert natural_xy("Sweeper") == (58, 50)
        assert natural_xy("") == (58, 50)


class TestAssignXIToSlots:
    def test_returns_one_player_per_slot(self):
        assigned = assign_xi_to_slots(SLOTS_433, ARG_XI, ARG_POSITIONS)
        assert len(assigned) == len(SLOTS_433)

    def test_is_a_bijection(self):
        assigned = assign_xi_to_slots(SLOTS_433, ARG_XI, ARG_POSITIONS)
        # Every player placed exactly once, none dropped or duplicated.
        assert set(assigned) == set(ARG_XI)
        assert len(assigned) == len(set(assigned))

    def test_goalkeeper_pinned_to_gk_slot(self):
        assigned = assign_xi_to_slots(SLOTS_433, ARG_XI, ARG_POSITIONS)
        # slots[0] is the GK slot; the goalkeeper (#23) must land there.
        assert assigned[0] == ("Martínez", 23)

    def test_central_midfielder_not_on_the_wing(self):
        # The regression: Mac Allister (#20, Central Midfield) must NOT be
        # placed on the RW slot (index 8, coord (73, 10)).
        assigned = assign_xi_to_slots(SLOTS_433, ARG_XI, ARG_POSITIONS)
        slot_of = {num: SLOTS_433[i] for i, (_, num) in enumerate(assigned)}
        macca_x, _ = slot_of[20]
        # A midfielder belongs in the CDM/CM band (x <= 58), never the wings.
        assert macca_x <= 58

    def test_wingers_take_the_wide_attacking_slots(self):
        assigned = assign_xi_to_slots(SLOTS_433, ARG_XI, ARG_POSITIONS)
        slot_of = {num: SLOTS_433[i] for i, (_, num) in enumerate(assigned)}
        # Messi (#10, Right Winger) -> RW (73, 10); González (#15, Left Winger) -> LW (73, 90).
        assert slot_of[10] == (73, 10)
        assert slot_of[15] == (73, 90)
        # Álvarez (#9, Centre-Forward) -> ST (88, 50).
        assert slot_of[9] == (88, 50)

    def test_all_three_midfielders_in_midfield_band(self):
        assigned = assign_xi_to_slots(SLOTS_433, ARG_XI, ARG_POSITIONS)
        slot_of = {num: SLOTS_433[i] for i, (_, num) in enumerate(assigned)}
        for num in (7, 24, 20):  # De Paul, Fernández, Mac Allister
            x, _ = slot_of[num]
            assert 40 <= x <= 58

    def test_overflow_player_goes_to_nearest_free_slot(self):
        # Four central-ish players but only three central slots in 4-3-3.
        # Swap González (winger) for an extra Central Midfield -> the extra
        # central player must still be placed (bijection holds) and one of the
        # four ends up in an attacking slot rather than being dropped.
        positions = dict(ARG_POSITIONS)
        positions[15] = "Central Midfield"  # now 4 central mids
        assigned = assign_xi_to_slots(SLOTS_433, ARG_XI, positions)
        assert set(assigned) == set(ARG_XI)
        slot_of = {num: SLOTS_433[i] for i, (_, num) in enumerate(assigned)}
        central = [num for num in (7, 24, 20, 15) if slot_of[num][0] <= 58]
        # Three of the four central players occupy the three central slots;
        # the fourth overflows forward.
        assert len(central) == 3

    def test_falls_back_when_no_unique_goalkeeper(self):
        # Defensive: missing GK position should not crash; still a bijection.
        positions = dict(ARG_POSITIONS)
        del positions[23]
        assigned = assign_xi_to_slots(SLOTS_433, ARG_XI, positions)
        assert set(assigned) == set(ARG_XI)
