"""Shared fixtures for the protocol library tests.

The tests import the dependency light `avr` package directly (not through the
Home Assistant integration package), so Home Assistant is not needed to run them.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "custom_components" / "denon_avr"))

FIXTURES = ROOT / "tests" / "fixtures"


@pytest.fixture
def x3600h_deviceinfo() -> str:
    """Deviceinfo.xml read from a real AVR-X3600H (MAC address anonymised)."""

    return (FIXTURES / "deviceinfo_avr_x3600h.xml").read_text(encoding="utf-8")


@pytest.fixture
def integration_helpers():
    """The integration's helpers module, loaded without Home Assistant.

    helpers.py only imports from the avr package, so it is loaded under a stand-in
    package name that does not run the integration's __init__ (which needs HA).
    """

    import importlib
    import types

    name = "denon_avr_standin"
    if name not in sys.modules:
        package = types.ModuleType(name)
        package.__path__ = [str(ROOT / "custom_components" / "denon_avr")]
        sys.modules[name] = package
    return importlib.import_module(f"{name}.helpers")
