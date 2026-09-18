"""Application branding paths shared by the portable desktop entry points."""

from __future__ import annotations

from pathlib import Path


def application_icon_path() -> Path:
    """Return the packaged PNG used by Qt at runtime."""
    return Path(__file__).resolve().parent / "assets" / "betabrite-controller.png"
