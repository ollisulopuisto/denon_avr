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


def test_imax_filters_and_subwoofer(parser: TelnetParser) -> None:
    state = _feed(parser, "PSIMAXHPF 080", "PSIMAXLPF 120", "PSIMAXSWM ON", "PSIMAXSWO L+M")
    assert state.values["imax_high_pass_filter"] == "080"
    assert state.values["imax_low_pass_filter"] == "120"
    assert state.values["imax_subwoofer"] == "ON"
    assert state.values["imax_subwoofer_output"] == "L+M"
    # The longer filter prefixes never leak into the IMAX mode select.
    assert "imax" not in state.values


def test_imax_filter_values_match_what_the_receiver_publishes(x3600h_deviceinfo: str) -> None:
    import xml.etree.ElementTree as ET

    profile = load_profile()
    root = ET.fromstring(x3600h_deviceinfo)
    for control_id, block in (("imax_high_pass_filter", "HighPassFilter"), ("imax_low_pass_filter", "LowPassFilter")):
        published = [int(v.text) for v in root.find(f".//{block}").findall("Value")]
        assert [int(v) for v in profile.control(control_id).values] == published
        assert profile.control(control_id).feature == block


def test_select_options_on_an_x3600h(x3600h_deviceinfo: str, integration_helpers) -> None:
    profile = load_profile()
    enum_features = {s.feature for s in profile.controls.values() if s.kind == "enum" and s.feature}
    discovery = parse_device_info(x3600h_deviceinfo, enum_features, enum_features)
    expected = {
        "imax": ["Off", "On", "Auto"],
        "imax_subwoofer": ["Off", "On"],
        "imax_subwoofer_output": ["LFE+Main", "LFE"],
        "imax_high_pass_filter": ["40 Hz", "60 Hz", "70 Hz", "80 Hz", "90 Hz", "100 Hz", "110 Hz", "120 Hz", "150 Hz", "180 Hz", "200 Hz", "250 Hz"],
    }
    for control_id, options in expected.items():
        assert integration_helpers.enum_options(discovery, profile.control(control_id))[0] == options
