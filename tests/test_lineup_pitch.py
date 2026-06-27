"""Head-to-head lineup pitch: pure layout + DMC node building."""
from __future__ import annotations

import dash_mantine_components as dmc

from src.components.lineup_pitch import (
    build_lineup_pitch,
    pitch_nodes,
    surname,
)

# Two small synthetic lineups shaped like the real parse_lineups output.
HOME = {
    "rows": [
        [{"name": "Matthew Freese", "number": 24, "position": "Goalkeeper"}],
        [
            {"name": "Antonee Robinson", "number": 5, "position": "Defender"},
            {"name": "Tim Ream", "number": 13, "position": "Defender"},
            {"name": "Chris Richards", "number": 3, "position": "Defender"},
            {"name": "Nathan Freeman", "number": 16, "position": "Defender"},
        ],
        [
            {"name": "Tyler Adams", "number": 4, "position": "Midfielder"},
            {"name": "Malik Tillman", "number": 17, "position": "Midfielder"},
        ],
        [
            {"name": "Christian Pulišić", "number": 10, "position": "Midfielder"},
            {"name": "Weston McKennie", "number": 8, "position": "Midfielder"},
            {"name": "Sergiño Dest", "number": 2, "position": "Midfielder"},
        ],
        [{"name": "Folarin Balogun", "number": 20, "position": "Forward"}],
    ]
}
AWAY = {
    "rows": [
        [{"name": "Roberto Gill", "number": 12, "position": "Goalkeeper"}],
        [
            {"name": "Junior Alonso", "number": 6, "position": "Defender"},
            {"name": "Omar Alderete", "number": 3, "position": "Defender"},
            {"name": "Gustavo Gómez", "number": 15, "position": "Defender"},
            {"name": "Juan Cáceres", "number": 4, "position": "Defender"},
        ],
        [
            {"name": "Miguel Almirón", "number": 10, "position": "Midfielder"},
            {"name": "Damián Bobadilla", "number": 16, "position": "Midfielder"},
            {"name": "Andrés Cubas", "number": 14, "position": "Midfielder"},
            {"name": "Diego Gómez", "number": 8, "position": "Midfielder"},
        ],
        [
            {"name": "Julio Enciso", "number": 19, "position": "Forward"},
            {"name": "Antonio Sanabria", "number": 9, "position": "Forward"},
        ],
    ]
}
LINEUPS = {"home": HOME, "away": AWAY}


def _walk(node):
    yield node
    children = getattr(node, "children", None)
    if isinstance(children, (list, tuple)):
        for c in children:
            yield from _walk(c)
    elif children is not None:
        yield from _walk(children)


class TestSurname:
    def test_last_token(self):
        assert surname("Christian Pulišić") == "Pulišić"
        assert surname("Balogun") == "Balogun"

    def test_blank(self):
        assert surname("") == ""
        assert surname(None) == ""


class TestPitchNodes:
    def test_places_every_player_once(self):
        nodes = pitch_nodes(HOME["rows"], "home")
        assert len(nodes) == 11
        numbers = {p["number"] for p, _x, _y in nodes}
        assert len(numbers) == 11

    def test_home_keeper_is_left_forward_is_central(self):
        nodes = pitch_nodes(HOME["rows"], "home")
        by_num = {p["number"]: (x, y) for p, x, y in nodes}
        gk_x = by_num[24][0]
        fwd_x = by_num[20][0]
        assert gk_x < 15            # keeper hugs the left edge
        assert gk_x < fwd_x         # forward is further right (toward centre)
        assert 40 <= fwd_x < 50     # forward meets near the centre line

    def test_away_is_mirrored(self):
        nodes = pitch_nodes(AWAY["rows"], "away")
        by_num = {p["number"]: (x, y) for p, x, y in nodes}
        gk_x = by_num[12][0]
        assert gk_x > 85            # away keeper hugs the right edge
        # away forwards meet near the centre from the right
        fwd_x = by_num[19][0]
        assert 50 < fwd_x <= 60

    def test_single_player_line_centred_vertically(self):
        nodes = pitch_nodes(HOME["rows"], "home")
        by_num = {p["number"]: (x, y) for p, x, y in nodes}
        assert by_num[24][1] == 50  # lone keeper
        assert by_num[20][1] == 50  # lone striker

    def test_multi_player_line_spreads_vertically(self):
        nodes = pitch_nodes(HOME["rows"], "home")
        back_four_y = sorted(
            y for p, _x, y in nodes if p["number"] in (5, 13, 3, 16)
        )
        assert len(set(back_four_y)) == 4          # all distinct
        assert back_four_y[0] < 50 < back_four_y[-1]  # spread across the pitch


class TestBuildLineupPitch:
    def test_returns_box_with_all_22_players(self):
        pitch = build_lineup_pitch(LINEUPS)
        assert isinstance(pitch, dmc.Box)
        texts = [
            n.children for n in _walk(pitch)
            if isinstance(n, dmc.Text) and isinstance(n.children, str)
        ]
        # Every surname appears on the pitch.
        assert "Pulišić" in texts
        assert "Balogun" in texts
        assert "Sanabria" in texts
        badges = [n for n in _walk(pitch)
                  if "lu-node__badge" in getattr(n, "className", "")]
        assert len(badges) == 22

    def test_team_and_keeper_colors(self):
        pitch = build_lineup_pitch(LINEUPS)
        badges = [n for n in _walk(pitch)
                  if "lu-node__badge" in getattr(n, "className", "")]
        gk = [b for b in badges if "lu-node__badge--gk" in b.className]
        home = [b for b in badges if "lu-node__badge--home" in b.className]
        away = [b for b in badges if "lu-node__badge--away" in b.className]
        assert len(gk) == 2       # one keeper per team, distinct colour
        assert len(home) == 10    # home outfielders
        assert len(away) == 10    # away outfielders

    def test_empty_lineups_returns_none(self):
        assert build_lineup_pitch({"home": {"rows": []}, "away": {"rows": []}}) is None
        assert build_lineup_pitch({}) is None
