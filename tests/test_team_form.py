from src.data.team_form import DRAW, LOSS, WIN, match_result, recent_form


def _norm(name):
    # simplistic normalizer for tests: lowercase + alias one live spelling
    n = " ".join((name or "").strip().lower().split())
    return {"korea republic": "south korea"}.get(n, n)


def _m(home, away, hs, away_s, state="finished", kickoff=None):
    return {"home": home, "away": away, "home_score": hs, "away_score": away_s,
            "state": state, "kickoff": kickoff}


def test_match_result_win_loss_draw_from_team_perspective():
    # team is home and wins
    assert match_result("Mexico", _m("Mexico", "Poland", 2, 0), _norm) == WIN
    # team is away and wins
    assert match_result("Mexico", _m("Poland", "Mexico", 0, 1), _norm) == WIN
    # team is home and loses
    assert match_result("Mexico", _m("Mexico", "Poland", 0, 3), _norm) == LOSS
    # team is away and loses
    assert match_result("Mexico", _m("Poland", "Mexico", 3, 0), _norm) == LOSS
    # draw
    assert match_result("Mexico", _m("Mexico", "Poland", 1, 1), _norm) == DRAW


def test_match_result_none_when_not_finished_or_no_score_or_not_involved():
    assert match_result("Mexico", _m("Mexico", "Poland", None, None,
                                     state="scheduled"), _norm) is None
    assert match_result("Mexico", _m("Mexico", "Poland", None, None,
                                     state="live"), _norm) is None
    # finished but no score parsed
    assert match_result("Mexico", _m("Mexico", "Poland", None, None), _norm) is None
    # team not in this match
    assert match_result("Brazil", _m("Mexico", "Poland", 2, 0), _norm) is None


def test_match_result_uses_normalizer_for_name_matching():
    # live feed spells it "Korea Republic"; normalizer maps it to "South Korea"
    assert match_result("South Korea",
                        _m("Korea Republic", "Ghana", 2, 1), _norm) == WIN


def test_recent_form_is_chronological_by_kickoff():
    matches = [
        _m("Mexico", "C", 0, 1, kickoff="2026-06-20T18:00:00+00:00"),  # L (3rd)
        _m("A", "Mexico", 0, 0, kickoff="2026-06-11T18:00:00+00:00"),  # D (1st)
        _m("Mexico", "B", 3, 0, kickoff="2026-06-15T18:00:00+00:00"),  # W (2nd)
    ]
    assert recent_form("Mexico", matches, _norm) == [DRAW, WIN, LOSS]


def test_recent_form_ignores_unfinished_and_unrelated_matches():
    matches = [
        _m("Mexico", "B", 3, 0, kickoff="2026-06-15T18:00:00+00:00"),   # W
        _m("Mexico", "C", 1, 1, state="live",
           kickoff="2026-06-20T18:00:00+00:00"),                        # ignored
        _m("A", "B", 2, 2, kickoff="2026-06-12T18:00:00+00:00"),        # not Mexico
    ]
    assert recent_form("Mexico", matches, _norm) == [WIN]


def test_recent_form_caps_at_limit_keeping_most_recent():
    matches = [
        _m("Mexico", f"T{i}", 1, 0, kickoff=f"2026-06-{10+i:02d}T18:00:00+00:00")
        for i in range(7)  # 7 wins, dates ascending
    ]
    form = recent_form("Mexico", matches, _norm, limit=5)
    assert form == [WIN] * 5   # last 5 of 7 (all wins here)
    assert len(form) == 5


def test_recent_form_empty_when_no_finished_matches():
    assert recent_form("Mexico", [], _norm) == []
