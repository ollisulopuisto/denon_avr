"""Sound mode selection through the receiver's HTTP command API.

The MS telnet tokens often differ from the names the receiver reports, and some
modes have no working MS token at all (DTS Virtual:X on an AVR-X3600H is reported
as 'MSVIRTUAL:X' but no MS command selects it). The HTTP command API
(AppCommand0300.xml, advertised under SoundMode/Commands in Deviceinfo.xml) lists
the modes of the current genre with an entry number and selects one by that
number, so a mode can be chosen by its display name without knowing its token.

These helpers only build and parse the XML; they have no I/O.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

_ENVELOPE = (
    '<?xml version="1.0" encoding="utf-8" ?>'
    '<tx><cmd id="3"><name>{name}</name><list>{params}</list></cmd></tx>'
)


def get_request() -> str:
    """Request body for the current genre's sound mode list."""

    return _ENVELOPE.format(name="GetSoundModeList", params='<param name="genrelist"></param>')


def set_request(genre: str, listno: int) -> str:
    """Request body selecting entry `listno` of genre list `genre`."""

    params = f'<param name="genrelist">{genre}</param><param name="listno">{listno}</param>'
    return _ENVELOPE.format(name="SetSoundModeList", params=params)


def parse_list(xml_text: str | None) -> tuple[str | None, list[tuple[int, str, bool]]]:
    """Parse a GetSoundModeList reply into (genre, [(listno, name, selected)])."""

    if not xml_text:
        return None, []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return None, []
    genre = None
    for param in root.iter("param"):
        if param.get("name") == "genrelist" and (param.text or "").strip():
            genre = param.text.strip()
            break
    entries: list[tuple[int, str, bool]] = []
    for value in root.iter("value"):
        number = (value.findtext("listno") or "").strip()
        name = (value.findtext("dispname") or "").strip()
        if number.isdigit() and name:
            entries.append((int(number), name, (value.findtext("selected") or "").strip() == "1"))
    return genre, entries


def is_ok(xml_text: str | None) -> bool:
    """True when a Set reply acknowledges the command."""

    if not xml_text:
        return False
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return False
    return any((cmd.text or "").strip() == "OK" for cmd in root.iter("cmd"))
