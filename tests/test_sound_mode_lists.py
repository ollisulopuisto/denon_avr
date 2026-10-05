"""The current-context mode list (OPSML) the sound mode select offers.

Besides answering 'OPSML ?' with a list ended by 'OPSML END', the receiver pushes
single OPSML lines when the mode changes. Those must not pile up as duplicates
in the next list (seen live: 'Stereo' five times in the select's options).
"""

from __future__ import annotations

from avr.models import AvrState, Discovery
from avr.parser import TelnetParser
from avr.profile import load_profile


def test_pushed_lines_do_not_duplicate_modes() -> None:
    discovery = Discovery()
    parser = TelnetParser(load_profile(), discovery)
    state = AvrState()
    for line in ["OPSML 011Stereo", "OPSML 011Stereo", "OPSML 011Stereo",
                 "OPSML 011Stereo", "OPSML 020Multi Ch Stereo", "OPSML 030Rock Arena", "OPSML END"]:
        parser.feed(line, state)
    assert discovery.current_sound_modes == ["Stereo", "Multi Ch Stereo", "Rock Arena"]
    assert state.values["sound_mode_display"] == "Stereo"
