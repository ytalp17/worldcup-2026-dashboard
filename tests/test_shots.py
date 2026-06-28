from src.data.live.shots import ShotRecord, parse_shots


def _detail():
    return {
        "homeTeam": {"name": "England", "shots": [
            {"playerName": "K. Bowie", "time": "15'", "outcome": "Blocked",
             "goalTarget": "Low Centre"},
            {"playerName": "M. Olise", "time": "45+1", "outcome": "Missed",
             "goalTarget": None},
        ]},
        "awayTeam": {"name": "Wales", "shots": [
            {"playerName": "D. James", "time": "70'", "outcome": "Saved",
             "goalTarget": "High Right"},
        ]},
    }


def test_parses_both_sides_with_team_names():
    rows = parse_shots(42, _detail())
    assert len(rows) == 3
    eng = [r for r in rows if r.team == "England"]
    assert len(eng) == 2
    assert rows[0] == ShotRecord(42, "England", "K. Bowie", "15'",
                                 "Blocked", "Low Centre", "Wales")
    assert any(r.goal_target is None and r.team == "England" for r in rows)
    # each side's opponent is the other side's name ("vs <team>")
    assert all(r.opponent == "Wales" for r in rows if r.team == "England")
    assert all(r.opponent == "England" for r in rows if r.team == "Wales")


def test_accepts_one_element_list_detail():
    rows = parse_shots(7, [_detail()])
    assert len(rows) == 3


def test_skips_malformed_shots_and_missing_sides():
    detail = {"homeTeam": {"name": "X", "shots": ["junk", None,
              {"playerName": "P", "time": "5'", "outcome": "Goal",
               "goalTarget": "Low Left"}]}}
    rows = parse_shots(1, detail)
    assert len(rows) == 1
    assert rows[0].outcome == "Goal"


def test_empty_or_bad_detail_returns_empty():
    assert parse_shots(1, None) == []
    assert parse_shots(1, []) == []
    assert parse_shots(1, {"homeTeam": {}, "awayTeam": {}}) == []
