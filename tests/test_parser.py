"""Tests for parser helpers in custom_components/denon_avr/avr/parser.py."""

from __future__ import annotations

from avr.parser import parse_upnp_description


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
