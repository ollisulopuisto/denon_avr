"""Tuner (TF/TM/TP) parsing and command encoding.

Wire formats follow the Denon AVR control protocol: the frequency is six digits
in hundredths ('TFAN010570' = 105.70 MHz on FM, 'TFAN052200' = 522.00 kHz on AM),
the band and the tuning mode share the 'TMAN' prefix, presets are two digits
('TPAN05'), and the RDS station name arrives as 'TFANNAME<text>'.
"""

from __future__ import annotations

import pytest

from avr.models import AvrState, Discovery
from avr.parser import TelnetParser
from avr.profile import load_profile


@pytest.fixture
def parser() -> TelnetParser:
    return TelnetParser(load_profile(), Discovery())


def _feed(parser: TelnetParser, *lines: str) -> AvrState:
    state = AvrState()
    for line in lines:
        parser.feed(line, state)
    return state


@pytest.mark.parametrize(("line", "expected"), [("TFAN010570", "105.70"), ("TFAN008750", "87.50"), ("TFAN052200", "522.00")])
def test_frequency(parser: TelnetParser, line: str, expected: str) -> None:
    assert _feed(parser, line).readonly["tuner_frequency"] == expected


def test_station_name_is_not_read_as_a_frequency(parser: TelnetParser) -> None:
    state = _feed(parser, "TFAN010570", "TFANNAMEYLE RADIO 1  ")
    assert state.readonly["tuner_station_name"] == "YLE RADIO 1"
    assert state.readonly["tuner_frequency"] == "105.70"


def test_band_and_mode_share_a_prefix(parser: TelnetParser) -> None:
    state = _feed(parser, "TMANFM", "TMANAUTO")
    assert state.values["tuner_band"] == "FM"
    assert state.values["tuner_mode"] == "AUTO"


def test_preset(parser: TelnetParser) -> None:
    assert _feed(parser, "TPAN05").values["tuner_preset"] == 5


def test_tuner_controls_are_gated_on_the_tuner_function() -> None:
    profile = load_profile()
    for control_id in ("tuner_band", "tuner_mode", "tuner_preset"):
        assert profile.control(control_id).feature == "TUNER"
    for readonly_id in ("tuner_frequency", "tuner_station_name"):
        assert profile.readonly[readonly_id]["feature"] == "TUNER"


def test_preset_is_sent_as_two_digits() -> None:
    from avr.device import DenonAvrDevice

    spec = load_profile().control("tuner_preset")
    assert spec.prefix + DenonAvrDevice._encode_control_value(None, spec, 5) == "TPAN05"


def _resync_queries(features: set[str]) -> list[str]:
    from avr.device import DenonAvrDevice

    device = DenonAvrDevice(session=None, host="192.0.2.1")
    device._discovery.features = features
    return device._resync_queries()


def test_tuner_queried_only_when_advertised() -> None:
    tuner_queries = {"TFAN?", "TFANNAME?", "TMAN?", "TPAN?"}
    assert tuner_queries <= set(_resync_queries({"TUNER"}))
    assert not tuner_queries & set(_resync_queries(set()))


def test_x3600h_document_does_not_relabel_the_tuner_controls(x3600h_deviceinfo: str) -> None:
    from avr.parser import parse_device_info

    discovery = parse_device_info(x3600h_deviceinfo, {"TUNER"}, {"TUNER"})
    assert "TUNER" in discovery.features
    assert "TUNER" not in discovery.option_labels
    assert "TUNER" not in discovery.numeric_meta
