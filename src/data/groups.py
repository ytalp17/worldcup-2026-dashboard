from __future__ import annotations

from dataclasses import dataclass

from src.data.matches import Match


@dataclass(frozen=True)
class GroupStanding:
    team: str
    played: int = 0
    won: int = 0
    drawn: int = 0
    lost: int = 0
    goal_diff: int = 0
    points: int = 0


@dataclass(frozen=True)
class Group:
    name: str                              # e.g. "Group A"
    standings: tuple[GroupStanding, ...]   # official (seeding) order


def build_groups(matches: list[Match]) -> dict[str, Group]:
    """Map group name -> Group. Teams are ordered by first appearance across the
    group's Group-Stage matches in match_number order; all stats start at zero."""
    order: dict[str, list[str]] = {}
    for m in sorted(matches, key=lambda match: match.number):
        if m.stage != "Group Stage" or not m.group:
            continue
        teams = order.setdefault(m.group, [])
        for team in (m.home, m.away):
            if team not in teams:
                teams.append(team)
    return {
        name: Group(name, tuple(GroupStanding(team=t) for t in teams))
        for name, teams in order.items()
    }


def group_for_team(groups: dict[str, Group], team: str) -> Group | None:
    """The Group a team belongs to, or None if the team is unknown."""
    for group in groups.values():
        if any(s.team == team for s in group.standings):
            return group
    return None
