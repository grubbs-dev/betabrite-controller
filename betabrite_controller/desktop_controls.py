"""Toolkit-independent message-composer state for desktop interfaces."""

from __future__ import annotations

from dataclasses import dataclass

from .controller import COLORS, MODES, SPECIALS


PRESETS = {
    "BRIEF": "BRIEF IN PROGRESS",
    "AVAILABLE": "AVAILABLE",
    "WARNING": "WARNING",
    "ONLINE": "SYSTEM ONLINE",
}


def display_name(value: str) -> str:
    """Convert backend keys into customer-facing labels."""
    return value.replace("-", " ").title()


@dataclass(frozen=True, slots=True)
class MessageDraft:
    """Portable representation of one BetaBrite transmission request."""

    message: str = "BRIEF IN PROGRESS"
    color_name: str = "auto"
    mode_name: str = "rotate"
    special_name: str | None = None
    speed_level: int = 3
    flash: bool = False
    wide: bool = False

    @property
    def normalized_message(self) -> str:
        return self.message.strip()

    @property
    def has_payload(self) -> bool:
        return bool(self.normalized_message or self.special_name)

    def validate(self) -> "MessageDraft":
        if self.color_name not in COLORS:
            raise ValueError(f"Unknown color: {self.color_name}")

        if self.mode_name not in MODES:
            raise ValueError(f"Unknown display mode: {self.mode_name}")

        if self.special_name is not None and self.special_name not in SPECIALS:
            raise ValueError(f"Unknown special effect: {self.special_name}")

        if self.speed_level not in range(1, 6):
            raise ValueError("Speed must be between 1 and 5")

        if not self.has_payload:
            raise ValueError("A message or special effect is required")

        return self

    def send_kwargs(self) -> dict:
        """Return validated keyword arguments for BetaBriteController.send()."""
        self.validate()
        return {
            "message": self.normalized_message,
            "color_name": self.color_name,
            "mode_name": self.mode_name,
            "special_name": self.special_name,
            "speed_level": self.speed_level,
            "flash": self.flash,
            "wide": self.wide,
        }


def can_transmit(connection_ready: bool, draft: MessageDraft) -> bool:
    """Return whether a draft is both valid and actively connection-ready."""
    if not connection_ready:
        return False

    try:
        draft.validate()
    except ValueError:
        return False

    return True
