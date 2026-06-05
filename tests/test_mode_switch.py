import dash_mantine_components as dmc

from src.components.mode_switch import MODE_SWITCH_ID, mode_switch


def test_mode_switch_is_a_switch_with_expected_id_and_default():
    assert isinstance(mode_switch, dmc.Switch)
    assert mode_switch.id == MODE_SWITCH_ID == "mode-toggle"
    # Default unchecked == Time mode (preserves current default behavior).
    assert mode_switch.checked is False
    assert mode_switch.persistence is True
