"""Build the knockout bracket from the fixture schedule, resolving each slot as
far as the available data allows.

The schedule (matches.csv) carries the bracket *skeleton*: the six knockout
rounds, their dates/times, and the connectivity encoded in placeholder labels —
``"Group A winners"``, ``"Group B runners-up"``, ``"Group A/B/.. third place"``
and ``"Winner Match 73"`` / ``"Runner-up Match 101"``. This module turns that
skeleton into resolved ``BracketMatch`` objects:

- ``results`` (real teams + scores, matched from the live feed by kickoff) take
  precedence and, when finished, record the winner so it propagates into the
  ``"Winner Match N"`` slot of the next round.
- group winner / runner-up labels resolve from ``standings`` only once that
  group's stage is complete (so we never show a premature table leader);
- third-place slots stay unresolved (shown as TBD) — their FIFA allocation is
  not derivable from standings alone.

Pure and offline: everything is computed from plain inputs, so it is fully
unit-testable without the API.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime

KO_STAGES = ["Round of 32", "Round of 16", "Quarter-Final", "Semi-Final",
             "Bronze Final", "Final"]

# Carousel pages: two stages shown at a time.
STAGE_PAGES = [
    ("Round of 32", "Round of 16"),
    ("Quarter-Final", "Semi-Final"),
    ("Final", "Bronze Final"),
]

_WINNER_RE = re.compile(r"Winner Match (\d+)", re.I)
_RUNNER_RE = re.compile(r"Runner-up Match (\d+)", re.I)
_WINNERS_RE = re.compile(r"Group ([A-L]) winners", re.I)
_RUNNERS_RE = re.compile(r"Group ([A-L]) runners-up", re.I)


@dataclass(frozen=True)
class Slot:
    """One side of a bracket match. ``team`` is the resolved official name (or
    None when undecided → rendered as TBD); ``winner`` marks the side that won."""
    team: str | None
    score: int | None
    winner: bool


@dataclass(frozen=True)
class BracketMatch:
    number: int
    stage: str
    date: date
    kickoff_utc: datetime
    home: Slot
    away: Slot
    finished: bool
    feeder_numbers: tuple[int, ...]  # earlier matches feeding this one
    venue: str = ""                  # where the match is played


def _feeders(home_label: str, away_label: str) -> tuple[int, ...]:
    """Match numbers feeding a match, parsed from Winner/Runner-up Match labels."""
    nums = []
    for label in (home_label, away_label):
        m = _WINNER_RE.search(label) or _RUNNER_RE.search(label)
        if m:
            nums.append(int(m.group(1)))
    return tuple(nums)


def _resolve_label(label: str, standings: dict, complete_groups: set,
                   winners: dict, losers: dict) -> str | None:
    """Resolve a placeholder label to an official team name, or None if undecided."""
    if (m := _WINNER_RE.search(label)):
        return winners.get(int(m.group(1)))
    if (m := _RUNNER_RE.search(label)):
        return losers.get(int(m.group(1)))
    if (m := _WINNERS_RE.search(label)):
        group = f"Group {m.group(1).upper()}"
        table = standings.get(group)
        if group in complete_groups and table:
            return table[0]
        return None
    if (m := _RUNNERS_RE.search(label)):
        group = f"Group {m.group(1).upper()}"
        table = standings.get(group)
        if group in complete_groups and table and len(table) > 1:
            return table[1]
        return None
    return None  # third-place slots and anything else: TBD


def build_bracket(ko_matches, standings: dict | None = None,
                  complete_groups: set | None = None,
                  results: dict | None = None,
                  venues: dict | None = None) -> dict[str, list[BracketMatch]]:
    """Resolve the knockout schedule into ``{stage: [BracketMatch]}``.

    ``standings``: ``{group_name: [team, ...]}`` ordered best-first.
    ``complete_groups``: group names whose stage is finished (gate for winner /
    runner-up resolution). ``results``: ``{match_number: (home, away,
    home_score, away_score)}`` from the live feed. Matches are processed in
    number order so a finished match's winner propagates into later rounds.
    """
    standings = standings or {}
    complete_groups = complete_groups or set()
    results = results or {}
    venues = venues or {}

    winners: dict[int, str] = {}
    losers: dict[int, str] = {}
    out: dict[str, list[BracketMatch]] = {stage: [] for stage in KO_STAGES}

    for m in sorted(ko_matches, key=lambda x: x.number):
        res = results.get(m.number)
        if res:
            home_team, away_team, home_score, away_score = res
        else:
            home_team = _resolve_label(m.home, standings, complete_groups,
                                       winners, losers)
            away_team = _resolve_label(m.away, standings, complete_groups,
                                       winners, losers)
            home_score = away_score = None

        finished = home_score is not None and away_score is not None
        home_won = away_won = False
        if finished and home_team and away_team:
            if home_score > away_score:
                home_won = True
                winners[m.number], losers[m.number] = home_team, away_team
            elif away_score > home_score:
                away_won = True
                winners[m.number], losers[m.number] = away_team, home_team

        out[m.stage].append(BracketMatch(
            number=m.number, stage=m.stage, date=m.date,
            kickoff_utc=m.kickoff_utc,
            home=Slot(home_team, home_score, home_won),
            away=Slot(away_team, away_score, away_won),
            finished=finished,
            feeder_numbers=_feeders(m.home, m.away),
            venue=venues.get(m.stadium, m.stadium),
        ))
    return out


def stage_ties(bracket: dict[str, list[BracketMatch]], left_stage: str,
               right_stage: str) -> list[tuple[BracketMatch, list[BracketMatch]]]:
    """For a stage pair, pair each right-stage match with its feeder matches in
    the left stage (via ``feeder_numbers``)."""
    left_by_num = {bm.number: bm for bm in bracket.get(left_stage, [])}
    ties = []
    for rm in bracket.get(right_stage, []):
        feeders = [left_by_num[n] for n in rm.feeder_numbers if n in left_by_num]
        ties.append((rm, feeders))
    return ties
