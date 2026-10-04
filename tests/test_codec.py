"""Tests for the pure wire value codecs."""

from __future__ import annotations

import pytest

from avr.codec import decode_half_step, encode_half_step


@pytest.mark.parametrize(
    ("token", "expected"),
    [("50", 50.0), ("455", 45.5), ("450", 45.0), ("00", 0.0), ("OFF", None), ("NON", None)],
)
def test_decode_half_step(token: str, expected: float | None) -> None:
    assert decode_half_step(token) == expected


@pytest.mark.parametrize(("value", "expected"), [(50.0, "50"), (45.5, "455"), (5.0, "05"), (-3.0, "00")])
def test_encode_half_step(value: float, expected: str) -> None:
    assert encode_half_step(value) == expected


@pytest.mark.parametrize("value", [0.0, 0.5, 12.0, 45.5, 98.0])
def test_half_step_round_trip(value: float) -> None:
    assert decode_half_step(encode_half_step(value)) == value
