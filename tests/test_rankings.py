from pathlib import Path

import pandas as pd

ROOT = Path(__file__).parent.parent
TEAMS_CSV = ROOT / "assets" / "data" / "teams.csv"
FLAGS_DIR = ROOT / "assets" / "flags"


def test_teams_csv_has_fifa_rank():
    df = pd.read_csv(TEAMS_CSV)
    assert "fifa_rank" in df.columns
    assert len(df) == 48
    assert df["fifa_rank"].notna().all()
    assert (df["fifa_rank"] > 0).all()
    by_team = df.set_index("team")
    assert by_team.loc["Argentina", "fifa_rank"] == 1
    assert by_team.loc["Spain", "fifa_rank"] == 2
    assert by_team.loc["USA", "fifa_rank"] == 15


def test_a_flag_png_exists_for_every_team():
    df = pd.read_csv(TEAMS_CSV)
    missing = [t for t in df["team"] if not (FLAGS_DIR / f"{t}.png").exists()]
    assert missing == [], f"missing flags for: {missing}"
