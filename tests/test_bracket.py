from datetime import date, datetime, time

from src.data.bracket import (
    KO_STAGES,
    STAGE_PAGES,
    BracketMatch,
    build_bracket,
    stage_ties,
)
from src.data.matches import Match


def _m(number, home, away, stage, d="2026-06-28"):
    dt = date.fromisoformat(d)
    return Match(number=number, home=home, away=away, group="", stage=stage,
                 stadium="X", date=dt, local_time=time(19, 0),
                 kickoff_utc=datetime.fromisoformat(f"{d}T19:00:00+00:00"))


def _mini_ko():
    """Two R32 feeding one R16."""
    return [
        _m(73, "Group A winners", "Group B runners-up", "Round of 32"),
        _m(74, "Group C winners", "Group D runners-up", "Round of 32"),
        _m(89, "Winner Match 73", "Winner Match 74", "Round of 16"),
    ]


def test_stage_constants_cover_all_six_rounds():
    assert KO_STAGES == ["Round of 32", "Round of 16", "Quarter-Final",
                         "Semi-Final", "Bronze Final", "Final"]
    assert STAGE_PAGES == [("Round of 32", "Round of 16"),
                           ("Quarter-Final", "Semi-Final"),
                           ("Final", "Bronze Final")]


def test_build_bracket_groups_by_stage_with_tbd_when_unresolved():
    br = build_bracket(_mini_ko())
    assert [m.number for m in br["Round of 32"]] == [73, 74]
    assert [m.number for m in br["Round of 16"]] == [89]
    r16 = br["Round of 16"][0]
    # nothing resolved yet -> both slots are TBD (team is None)
    assert r16.home.team is None and r16.away.team is None
    assert isinstance(r16, BracketMatch)


def test_feeder_numbers_parsed_from_winner_match_labels():
    br = build_bracket(_mini_ko())
    r16 = br["Round of 16"][0]
    assert r16.feeder_numbers == (73, 74)
    # R32 matches are fed by group slots, not matches
    assert br["Round of 32"][0].feeder_numbers == ()


def test_group_slots_resolve_only_when_group_complete():
    standings = {"Group A": ["Mexico", "Poland"], "Group B": ["Brazil", "Serbia"]}
    # Group A complete, Group B not -> only the A winner resolves
    br = build_bracket(_mini_ko(), standings=standings,
                       complete_groups={"Group A"})
    r32 = br["Round of 32"][0]
    assert r32.home.team == "Mexico"        # Group A winners
    assert r32.away.team is None            # Group B runners-up (group incomplete)


def test_results_set_scores_and_mark_winner_and_propagate():
    # Match 73 finished 2-1 (home wins), 74 finished 0-3 (away wins);
    # winners propagate into R16 match 89's two slots.
    results = {
        73: ("Mexico", "Serbia", 2, 1),
        74: ("Brazil", "Poland", 0, 3),
    }
    br = build_bracket(_mini_ko(), results=results)
    m73 = br["Round of 32"][0]
    assert m73.finished and m73.home.winner and not m73.away.winner
    assert (m73.home.team, m73.home.score) == ("Mexico", 2)
    r16 = br["Round of 16"][0]
    assert r16.home.team == "Mexico"   # winner of 73
    assert r16.away.team == "Poland"   # winner of 74 (away won)


def test_stage_ties_link_winner_to_its_two_feeders():
    br = build_bracket(_mini_ko())
    ties = stage_ties(br, "Round of 32", "Round of 16")
    assert len(ties) == 1
    winner_match, feeders = ties[0]
    assert winner_match.number == 89
    assert [f.number for f in feeders] == [73, 74]
