"""Tests for Deviceinfo.xml discovery against a real AVR-X3600H document."""

from __future__ import annotations

from avr.parser import parse_device_info
from avr.profile import load_profile


def _discover(xml_text: str):
    profile = load_profile()
    return parse_device_info(xml_text, receiver_type=profile.receiver_type)


def test_model_zones_and_type(x3600h_deviceinfo: str) -> None:
    discovery = _discover(x3600h_deviceinfo)
    assert discovery.device.model_name == "AVR-X3600H"
    assert discovery.device.zone_count == 2
    assert [zone.id for zone in discovery.zones] == ["main", "zone2"]
    assert discovery.device.hardware_type == "avr-x-2016"


def test_advertised_features(x3600h_deviceinfo: str) -> None:
    features = _discover(x3600h_deviceinfo).features
    for present in ("IMAX", "IMAXAudioSettings", "TUNER", "SourceRename", "ZoneRename", "MultEq", "DTSNeuralX"):
        assert present in features
    assert not any("Auro" in name for name in features)
    assert "SpeakerPreset" not in features


def test_unparseable_document_yields_empty_discovery() -> None:
    discovery = parse_device_info("<not xml")
    assert discovery.device.model_name is None
    assert discovery.features == set()
