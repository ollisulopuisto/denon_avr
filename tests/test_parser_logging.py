"""Lines the parser does not recognise are logged at debug level for diagnosis."""

from __future__ import annotations

import logging

from avr.models import AvrState, Discovery
from avr.parser import TelnetParser
from avr.profile import load_profile


def test_unhandled_line_is_logged(caplog) -> None:
    parser = TelnetParser(load_profile(), Discovery())
    with caplog.at_level(logging.DEBUG):
        assert parser.feed("QQUNKNOWN 123", AvrState()) is False
    assert "QQUNKNOWN 123" in caplog.text


def test_applied_line_is_not_logged(caplog) -> None:
    parser = TelnetParser(load_profile(), Discovery())
    with caplog.at_level(logging.DEBUG):
        parser.feed("PSDYNVOL LIT", AvrState())
    assert "not applied" not in caplog.text
