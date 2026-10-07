"""Volume level scale: raw / 100, like the Home Assistant core Denon integration.

The core integration reported (dB + 80) / 100, which is raw / 100 (raw 80 is 0 dB). An amp at raw 36 (-44 dB) was
0.36, and the amp's own Absolute display reads 36.0. Dividing by the receiver's volume limit instead made the same
loudness read 0.60 and broke every dashboard and automation that knew the old numbers. The limit (MVMAX) still caps
what can be set: it only decides the maximum, not the scale.
"""

from __future__ import annotations

import asyncio

from avr.device import DenonAvrDevice


def _device(limit_raw: float | None) -> tuple[DenonAvrDevice, list[str]]:
    device = DenonAvrDevice(session=None, host="192.0.2.1")
    device._state.zone("main").volume_max_raw = limit_raw
    sent: list[str] = []

    async def capture(command: str) -> None:
        sent.append(command)

    device._send = capture  # type: ignore[method-assign]
    return device, sent


def test_raw_to_level_is_raw_over_100_whatever_the_limit() -> None:
    for limit in (60, 98, None):
        device, _ = _device(limit)
        assert device.volume_raw_to_level(36) == 0.36
        assert device.volume_raw_to_level(60) == 0.60
        assert device.volume_raw_to_level(0) == 0.0


def test_level_to_raw_is_level_times_100() -> None:
    device, _ = _device(60)
    assert device._level_to_raw("main", 0.36) == 36
    assert device._level_to_raw("main", 0.365) == 36.5
    assert device._level_to_raw("main", 0.0) == 0


def test_set_volume_sends_the_old_scale_and_respects_the_limit() -> None:
    device, sent = _device(60)
    asyncio.run(device.async_set_volume_level("main", 0.36))
    asyncio.run(device.async_set_volume_level("main", 0.9))
    assert sent == ["MV36", "MV60"]


def test_set_then_read_round_trips() -> None:
    device, _ = _device(60)
    for level in (0.1, 0.36, 0.5):
        raw = device._level_to_raw("main", level)
        assert abs(device.volume_raw_to_level(raw) - level) < 0.005
