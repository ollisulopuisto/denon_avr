"""Selecting a sound mode by its list entry over the HTTP command API.

The receiver's MS telnet tokens differ from the names it reports, and some modes
(DTS Virtual:X on an AVR-X3600H) have no working MS token at all. Its HTTP command
API (AppCommand0300.xml: GetSoundModeList / SetSoundModeList) selects a mode by
the entry number in the current genre list, looked up by display name. The
fixture is a real reply from an AVR-X3600H on a 2-channel network source.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from avr import sound_mode_list
from avr.device import DenonAvrDevice

FIXTURE = (Path(__file__).parent / "fixtures" / "soundmodelist_avr_x3600h.xml").read_text()


def test_parse_list() -> None:
    genre, entries = sound_mode_list.parse_list(FIXTURE)
    assert genre == "2"
    assert entries[0] == (1, "Stereo", True)
    assert entries[3] == (4, "DTS Virtual:X", False)
    assert len(entries) == 9


def test_requests() -> None:
    assert '<name>GetSoundModeList</name>' in sound_mode_list.get_request()
    assert '<param name="genrelist"></param>' in sound_mode_list.get_request()
    body = sound_mode_list.set_request("2", 4)
    assert '<name>SetSoundModeList</name>' in body
    assert '<param name="genrelist">2</param><param name="listno">4</param>' in body


def test_ok_reply() -> None:
    assert sound_mode_list.is_ok('<?xml version="1.0" encoding="utf-8" ?><rx><cmd>OK</cmd></rx>')
    assert not sound_mode_list.is_ok('<?xml version="1.0" encoding="utf-8" ?><rx></rx>')
    assert not sound_mode_list.is_ok(None)


class _FakeGoform:
    def __init__(self, list_reply: str | None, set_reply: str | None) -> None:
        self.list_reply, self.set_reply, self.bodies = list_reply, set_reply, []

    async def async_app_command(self, body: str) -> str | None:
        self.bodies.append(body)
        return self.list_reply if "GetSoundModeList" in body else self.set_reply


def _device(goform: _FakeGoform) -> tuple[DenonAvrDevice, list[str]]:
    device = DenonAvrDevice(session=None, host="192.0.2.1")
    device._goform = goform
    sent: list[str] = []

    async def capture(command: str) -> None:
        sent.append(command)

    async def no_refresh() -> None:
        return None

    device._send = capture  # type: ignore[method-assign]
    device._refresh_current_sound_modes = no_refresh  # type: ignore[method-assign]
    return device, sent


def test_select_uses_the_list_entry() -> None:
    goform = _FakeGoform(FIXTURE, '<rx><cmd>OK</cmd></rx>')
    device, sent = _device(goform)
    asyncio.run(device.async_select_sound_mode("DTS Virtual:X"))
    assert '<param name="genrelist">2</param><param name="listno">4</param>' in goform.bodies[-1]
    assert sent == []


def test_falls_back_to_the_ms_token_when_http_fails() -> None:
    device, sent = _device(_FakeGoform(None, None))
    asyncio.run(device.async_select_sound_mode("Stereo"))
    assert sent == ["MSSTEREO"]


def test_falls_back_when_the_mode_is_not_in_the_current_list() -> None:
    goform = _FakeGoform(FIXTURE, '<rx><cmd>OK</cmd></rx>')
    device, sent = _device(goform)
    asyncio.run(device.async_select_sound_mode("Pure Direct"))
    assert sent == ["MSPURE DIRECT"]
    assert not any("SetSoundModeList" in body for body in goform.bodies)


def test_falls_back_when_the_set_is_not_acknowledged() -> None:
    device, sent = _device(_FakeGoform(FIXTURE, '<rx></rx>'))
    asyncio.run(device.async_select_sound_mode("Stereo"))
    assert sent == ["MSSTEREO"]
