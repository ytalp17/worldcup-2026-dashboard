from __future__ import annotations

from dataclasses import dataclass

from src.data.squads import Squad


def parse_market_value(text: str) -> float:
    """'€1.60m' -> 1_600_000.0, '€700k' -> 700_000.0. Unparseable -> 0.0."""
    s = (text or "").replace("€", "").replace(",", "").strip().lower()
    if not s:
        return 0.0
    mult = 1.0
    if s.endswith("k"):
        mult, s = 1_000.0, s[:-1]
    elif s.endswith("m"):
        mult, s = 1_000_000.0, s[:-1]
    elif s.endswith("bn") or s.endswith("b"):
        mult, s = 1_000_000_000.0, s.rstrip("bn")
    try:
        return float(s) * mult
    except ValueError:
        return 0.0


def format_value(euros: float) -> str:
    """3_000_000 -> '€3M', 700_000 -> '€700K', 1.2e9 -> '€1.2B'."""
    if euros >= 1_000_000_000:
        return f"€{euros / 1_000_000_000:.1f}B"
    if euros >= 1_000_000:
        return f"€{euros / 1_000_000:.0f}M"
    if euros >= 1_000:
        return f"€{euros / 1_000:.0f}K"
    return "€0"


@dataclass(frozen=True)
class TeamStats:
    avg_age: float | None
    avg_height: float | None
    squad_value: float
    value_display: str
    foot_right_pct: int | None
    foot_left_pct: int | None
    squad_size: int
    # No data source yet — rendered as "—".
    fifa_rank: int | None = None
    manager: str | None = None
    manager_nationality: str | None = None
    manager_flag: str | None = None  # asset src for the nationality flag, if any
    manager_age: int | None = None
    abroad: int | None = None


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def compute_team_stats(squad: Squad, fifa_rank: int | None = None,
                       manager: str | None = None,
                       manager_nationality: str | None = None,
                       manager_flag: str | None = None,
                       manager_age: int | None = None) -> TeamStats:
    players = squad.players
    ages = [int(p.age) for p in players if p.age.isdigit()]
    heights = []
    for p in players:
        try:
            heights.append(float(p.height_m))
        except (ValueError, TypeError):
            pass
    value = sum(parse_market_value(p.market_value) for p in players)
    n = len(players)
    right = sum(1 for p in players if p.foot.lower() == "right")
    left = sum(1 for p in players if p.foot.lower() == "left")

    return TeamStats(
        avg_age=_mean([float(a) for a in ages]),
        avg_height=(round(m, 2) if (m := _mean(heights)) is not None else None),
        squad_value=value,
        value_display=format_value(value),
        foot_right_pct=(round(right / n * 100) if n else None),
        foot_left_pct=(round(left / n * 100) if n else None),
        squad_size=n,
        fifa_rank=fifa_rank,
        manager=manager,
        manager_nationality=manager_nationality,
        manager_flag=manager_flag,
        manager_age=manager_age,
    )
