"""Momentary actions (button surface): profile entries, gating and the sent command."""

from __future__ import annotations

import asyncio

from avr.device import DenonAvrDevice
from avr.profile import load_profile

EXPECTED = {
    "tuner_frequency_up": ("TUNER", "TFANUP"),
    "tuner_frequency_down": ("TUNER", "TFANDOWN"),
    "tuner_preset_up": ("TUNER", "TPANUP"),
    "tuner_preset_down": ("TUNER", "TPANDOWN"),
    "quick_select_1_save": ("Quick Select1", "MSQUICK1 MEMORY"),
    "quick_select_4_save": ("Quick Select4", "MSQUICK4 MEMORY"),
}


def _device(features: set[str]) -> tuple[DenonAvrDevice, list[str]]:
    device = DenonAvrDevice(session=None, host="192.0.2.1")
    device._discovery.features = features
    sent: list[str] = []

    async def capture(command: str) -> None:
        sent.append(command)

    device._send = capture  # type: ignore[method-assign]
    return device, sent


def test_profile_actions() -> None:
    actions = load_profile().actions
    for action_id, (feature, command) in EXPECTED.items():
        assert actions[action_id]["feature"] == feature
        assert actions[action_id]["command"] == command


def test_supported_actions_follow_the_advertised_functions() -> None:
    device, _ = _device({"TUNER", "Quick Select1"})
    supported = set(device.supported_actions())
    assert {"tuner_frequency_up", "quick_select_1_save"} <= supported
    assert "quick_select_2_save" not in supported


def test_run_action_sends_its_command() -> None:
    device, sent = _device({"TUNER", "Quick Select1"})
    asyncio.run(device.async_run_action("quick_select_1_save"))
    asyncio.run(device.async_run_action("tuner_preset_up"))
    assert sent == ["MSQUICK1 MEMORY", "TPANUP"]


def test_unsupported_or_unknown_action_sends_nothing() -> None:
    device, sent = _device(set())
    asyncio.run(device.async_run_action("tuner_preset_up"))
    asyncio.run(device.async_run_action("no_such_action"))
    assert sent == []
