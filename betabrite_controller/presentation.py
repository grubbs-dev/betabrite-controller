"""Presentation helpers shared by BetaBrite user interfaces."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ConnectionView:
    state: str
    headline: str
    detail: str
    tone: str
    can_send: bool
    port: str | None = None


_HEADLINES = {
    "ready": "● READY",
    "selected": "● ADAPTER DETECTED",
    "no-adapter": "● NO ADAPTER",
    "not-found": "● NO ADAPTER",
    "selection-required": "● SELECT ADAPTER",
    "permission-denied": "● PERMISSION NEEDED",
    "port-busy": "● PORT BUSY",
    "port-not-found": "● PORT MISSING",
    "open-failed": "● CONNECTION ERROR",
}

_TONES = {
    "ready": "online",
    "selected": "selected",
    "selection-required": "selected",
    "port-busy": "selected",
}


def connection_view(diagnostic) -> ConnectionView:
    """Convert a backend diagnostic into stable customer-facing UI state."""
    state = getattr(diagnostic, "state", "unknown")
    headline = _HEADLINES.get(state, "● CHECK CONNECTION")
    detail = getattr(diagnostic, "message", "") or "Connection status unavailable."
    port = getattr(diagnostic, "port", None)

    return ConnectionView(
        state=state,
        headline=headline,
        detail=detail,
        tone=_TONES.get(state, "offline"),
        # A passive SELECTED state only proves the adapter is present. Sending
        # is enabled after an active READY probe succeeds.
        can_send=state == "ready",
        port=port,
    )
