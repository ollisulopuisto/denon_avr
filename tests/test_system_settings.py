"""System settings shared by every Denon/Marantz network receiver."""

from __future__ import annotations

from avr.models import AvrState, Discovery
from avr.parser import TelnetParser
from avr.profile import load_profile


def test_auto_standby() -> None:
    parser = TelnetParser(load_profile(), Discovery())
    state = AvrState()
    parser.feed("STBY30M", state)
    assert state.values["auto_standby"] == "30M"


def test_zone_auto_standby_is_not_read_as_main() -> None:
    parser = TelnetParser(load_profile(), Discovery())
    state = AvrState()
    parser.feed("Z2STBY2H", state)
    assert "auto_standby" not in state.values
