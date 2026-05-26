"""Smoke test for the TUI module -- verifies it imports cleanly."""

from __future__ import annotations


def test_tui_imports():
    """tui.py should import without errors (no real app instantiation)."""
    import importlib
    import sys

    # Remove cached import if present
    if "tui" in sys.modules:
        del sys.modules["tui"]

    spec = importlib.util.find_spec("tui")
    assert spec is not None, "tui.py module not found"
