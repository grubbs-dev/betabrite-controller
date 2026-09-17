"""Qt-independent presentation model for the portable desktop application."""

from __future__ import annotations

from dataclasses import dataclass

from .devices import (
    SerialDevice,
    device_matches_preference,
    list_candidate_devices,
)
from .settings import AppSettings, load_settings


@dataclass(frozen=True, slots=True)
class AdapterOption:
    """Customer-facing serial adapter option for desktop interfaces."""

    port: str
    label: str
    preferred: bool
    remembered: bool


def adapter_options(
    *,
    devices: list[SerialDevice] | None = None,
    settings: AppSettings | None = None,
) -> list[AdapterOption]:
    """Return display-ready USB adapter options without importing a GUI toolkit."""
    available = list_candidate_devices() if devices is None else list(devices)
    current_settings = load_settings() if settings is None else settings
    preference = current_settings.preferred_device

    options: list[AdapterOption] = []
    for device in available:
        remembered = bool(
            preference is not None
            and device_matches_preference(device, preference)
        )

        parts = [device.device, device.display_name]
        if device.usb_id:
            parts.append(f"[{device.usb_id}]")
        if device.preferred:
            parts.append("TESTED")
        if remembered:
            parts.append("SAVED")

        options.append(
            AdapterOption(
                port=device.device,
                label="  //  ".join(parts),
                preferred=device.preferred,
                remembered=remembered,
            )
        )

    return options


def default_adapter_index(options: list[AdapterOption]) -> int:
    """Prefer the remembered adapter, then the tested adapter, then the first."""
    for index, option in enumerate(options):
        if option.remembered:
            return index

    for index, option in enumerate(options):
        if option.preferred:
            return index

    return 0 if options else -1
