"""IMAX mode and IMAX audio settings.

The AVR-X3600H advertises both functions in Deviceinfo.xml with their option
lists (IMAX: Off/On/Auto; IMAX Audio Settings: Auto/Manual). The wire tokens are
'PSIMAX <value>' and 'PSIMAXAUD <value>'.
"""

from __future__ import annotations

import pytest

from avr.models import AvrState, Discovery
from avr.parser import TelnetParser, parse_device_info
from avr.profile import load_profile


@pytest.fixture
def parser() -> TelnetParser:
    return TelnetParser(load_profile(), Discovery())


def _feed(parser: TelnetParser, *lines: str) -> AvrState:
    state = AvrState()
    for line in lines:
        parser.feed(line, state)
    return state


def test_imax_mode_and_audio_settings_do_not_collide(parser: TelnetParser) -> None:
    state = _feed(parser, "PSIMAX AUTO", "PSIMAXAUD MANUAL")
    assert state.values["imax"] == "AUTO"
    assert state.values["imax_audio_settings"] == "MANUAL"


def test_controls_are_gated_on_the_advertised_functions() -> None:
    profile = load_profile()
    assert profile.control("imax").feature == "IMAX"
    assert profile.control("imax_audio_settings").feature == "IMAXAudioSettings"


def test_option_labels_line_up_with_the_wire_values(x3600h_deviceinfo: str) -> None:
    profile = load_profile()
    discovery = parse_device_info(
        x3600h_deviceinfo,
        {"IMAX", "IMAXAudioSettings"},
        {"IMAX", "IMAXAudioSettings"},
    )
    for control_id, labels in (("imax", ["Off", "On", "Auto"]), ("imax_audio_settings", ["Auto", "Manual"])):
        spec = profile.control(control_id)
        assert discovery.option_labels[spec.feature] == labels
        assert [value.lower() for value in spec.values] == [label.lower() for label in labels]
