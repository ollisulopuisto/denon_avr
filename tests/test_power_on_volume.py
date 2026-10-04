"""Power-on volume: SSVCTZMAPON carries either LAST, MUT or a fixed level.

It is split into two controls on the same prefix: a select for the Last/Mute
modes (exact-enum, so it never claims a number) and a number for a fixed level
on the receiver's absolute 0-98 scale, three digits on the wire like the
volume limit (SSVCTZMALIM 060).
"""

from __future__ import annotations

import pytest

from avr.device import DenonAvrDevice
from avr.models import AvrState, Discovery
from avr.parser import TelnetParser
from avr.profile import load_profile


@pytest.fixture
def parser() -> TelnetParser:
    return TelnetParser(load_profile(), Discovery())


def _feed(parser: TelnetParser, line: str) -> AvrState:
    state = AvrState()
    parser.feed(line, state)
    return state


@pytest.mark.parametrize("token", ["LAST", "MUT"])
def test_mode(parser: TelnetParser, token: str) -> None:
    state = _feed(parser, f"SSVCTZMAPON {token}")
    assert state.values["power_on_volume_mode"] == token
    assert "power_on_volume_level" not in state.values


def test_fixed_level(parser: TelnetParser) -> None:
    state = _feed(parser, "SSVCTZMAPON 040")
    assert state.values["power_on_volume_level"] == 40
    assert "power_on_volume_mode" not in state.values


def test_level_is_sent_as_three_digits() -> None:
    spec = load_profile().control("power_on_volume_level")
    assert spec.prefix + DenonAvrDevice._encode_control_value(None, spec, 40) == "SSVCTZMAPON 040"


def test_does_not_disturb_the_volume_limit(parser: TelnetParser) -> None:
    state = _feed(parser, "SSVCTZMALIM 060")
    assert state.values["volume_limit"] == "060"
