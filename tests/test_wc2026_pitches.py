import matplotlib

matplotlib.use("Agg")  # headless, before any pyplot import

from wc2026_pitches import THEMES, render_team

SAMPLE = {
    "name": "Argentina",
    "formation": "433",
    "coach": "",
    "xi": [
        ["Martínez", 23], ["Molina", 26], ["Otamendi", 19], ["Martínez", 6],
        ["Tagliafico", 3], ["De Paul", 7], ["Fernández", 24],
        ["Mac Allister", 20], ["González", 15], ["Messi", 10], ["Álvarez", 9],
    ],
}


def test_themes_define_dark_and_light():
    assert set(THEMES) == {"dark", "light"}
    for palette in THEMES.values():
        for key in ("pitch_color", "line_color", "node_color", "gk_color",
                    "text_color", "fig_color", "number_color"):
            assert key in palette


def test_render_team_writes_png_per_theme(tmp_path):
    for theme in ("dark", "light"):
        out = render_team("argentina", SAMPLE, THEMES[theme], theme, tmp_path)
        assert out.exists()
        assert out.suffix == ".png"
        assert out.name == f"argentina-{theme}.png"
        assert out.stat().st_size > 0
