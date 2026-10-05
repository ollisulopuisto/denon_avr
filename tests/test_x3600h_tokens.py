"""AVR-X3600H wire tokens that differ from the names the receiver reports.

Measured on an AVR-X3600H over telnet: it reports 'DOLBY AUDIO-DSUR' and
'DTS NEURAL:X' but silently ignores them as commands, and accepts 'DOLBY DIGITAL'
and 'DTS SURROUND' instead (it then reports the expected mode). On the Multi In
input, 'Multi In + DSur' goes out as 'M CH IN+DSUR'. The surround speaker size
also accepts 'NON' (no surround speakers), which lets Dolby Surround upmix to a
3-channel front layout.
"""

from __future__ import annotations

import pytest

from avr.device import DenonAvrDevice
from avr.profile import load_profile


@pytest.mark.parametrize(
    ("name", "wire"),
    [
        ("Dolby Audio - Dolby Surround", "DOLBY DIGITAL"),
        ("DTS Neural:X", "DTS SURROUND"),
        ("Multi In + DSur", "M CH IN+DSUR"),
        ("Multi Ch Stereo", "MCH STEREO"),
        ("Stereo", "STEREO"),
    ],
)
def test_sound_mode_wire_tokens(name: str, wire: str) -> None:
    device = DenonAvrDevice(session=None, host="192.0.2.1")
    assert device._resolve_sound_mode_wire(name) == wire


def test_surround_speaker_size_offers_none(integration_helpers) -> None:
    profile = load_profile()
    assert integration_helpers.speaker_size_options(profile, "SUA") == {"LAR": "Large", "SMA": "Small", "NON": "None"}
    assert integration_helpers.speaker_size_options(profile, "FRO") == {"LAR": "Large", "SMA": "Small"}
