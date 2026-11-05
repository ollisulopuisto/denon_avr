"""Tests for parser helpers in custom_components/denon_avr/avr/parser.py."""

from __future__ import annotations

from avr.models import AvrState, Discovery
from avr.parser import TelnetParser, parse_upnp_description
from avr.profile import load_profile


def test_parse_upnp_description_complete() -> None:
    xml_data = """<?xml version="1.0"?>
    <root xmlns="urn:schemas-upnp-org:device-1-0" xmlns:dm="urn:schemas-denon-com:device-1-0">
      <device>
        <deviceType>urn:schemas-upnp-org:device:MediaRenderer:1</deviceType>
        <friendlyName>Denon AVR-X3600H</friendlyName>
        <manufacturer>Denon</manufacturer>
        <modelNumber>A100</modelNumber>
        <serialNumber>123456789012</serialNumber>
        <dm:firmware_version>3.1.0</dm:firmware_version>
        <dm:firmwareRevision>1234-5678</dm:firmwareRevision>
        <serviceList>
          <service><serviceType>test</serviceType></service>
          <service><serviceType>test2</serviceType></service>
        </serviceList>
      </device>
    </root>
    """
    res = parse_upnp_description(xml_data)
    assert res == {
        "manufacturer": "Denon",
        "network_module_version": "A100",
        "serial_number": "123456789012",
        "firmware_version": "3.1.0",
        "firmware_revision": "1234-5678",
    }


def test_parse_upnp_description_partial() -> None:
    xml_data = """<root>
      <manufacturer>Denon</manufacturer>
      <serialNumber>123456789012</serialNumber>
    </root>"""
    res = parse_upnp_description(xml_data)
    assert res == {
        "manufacturer": "Denon",
        "serial_number": "123456789012",
    }


def test_parse_upnp_description_empty_and_invalid() -> None:
    assert parse_upnp_description("<invalid xml") == {}
    assert parse_upnp_description("<root></root>") == {}
    assert parse_upnp_description("") == {}


def test_parse_upnp_description_empty_text_ignored() -> None:
    xml_data = """<root>
      <manufacturer>   </manufacturer>
      <serialNumber>123456789012</serialNumber>
    </root>"""
    res = parse_upnp_description(xml_data)
    assert res == {
        "serial_number": "123456789012",
    }


def test_telnet_parser_speaker_config_and_recompute_channels() -> None:
    profile = load_profile()
    discovery = Discovery()
    state = AvrState()
    parser = TelnetParser(profile, discovery)

    # Initially no configured channels
    assert discovery.configured_channels == set()

    # Feed speaker config for Front speakers (LAR) - group code is FRO
    assert parser.feed("SSSPCFRO LAR", state)
    assert "FL" in discovery.configured_channels
    assert "FR" in discovery.configured_channels
    assert state.speaker_sizes["FRO"] == "LAR"

    # Subwoofer double (2SP) - count group SWF
    assert parser.feed("SSSPCSWF 2SP", state)
    assert "SW" in discovery.configured_channels
    assert "SW2" in discovery.configured_channels

    # Surround Back single (1SP) - count group SBK
    assert parser.feed("SSSPCSBK 1SP", state)
    assert "SB" in discovery.configured_channels
    assert "SBL" not in discovery.configured_channels

    # Center speaker (CEN)
    assert parser.feed("SSSPCCEN SMA", state)
    assert "C" in discovery.configured_channels

    # Non-configured / absent speaker
    assert parser.feed("SSSPCFRH NON", state)
    assert "FHL" not in discovery.configured_channels
    assert "FHR" not in discovery.configured_channels
