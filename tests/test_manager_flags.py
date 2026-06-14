from pathlib import Path

ROOT = Path(__file__).parent.parent
FLAGS = ROOT / "assets" / "manager_flags"


def test_a_flag_exists_for_every_manager_nationality():
    from src.data.team_continents import (
        TEAM_MANAGER_NATIONALITY,
        manager_nationality_for,
    )
    nats = {manager_nationality_for(t) for t in TEAM_MANAGER_NATIONALITY} - {None}
    missing = [n for n in nats if not (FLAGS / f"{n}.png").exists()]
    assert missing == [], f"missing manager flags: {missing}"


def test_specific_manager_flags_present():
    assert (FLAGS / "Italy.png").exists()
    assert (FLAGS / "Spain.png").exists()
    assert (FLAGS / "Bosnia and Herzegovina.png").exists()
