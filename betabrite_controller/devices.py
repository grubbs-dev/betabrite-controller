"""Cross-platform serial-device discovery for BetaBrite Controller."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path

from serial.tools import list_ports

from .settings import (
    AppSettings,
    DevicePreference,
    forget_device as forget_saved_device,
    load_settings,
    remember_device,
)


AUTO_PORT = "auto"

# DSD TECH SH-RJ12C / Prolific PL2303GT used by the physically tested setup.
PREFERRED_USB_IDS = {
    (0x067B, 0x23A3),
}


class DeviceDiscoveryError(RuntimeError):
    """Base class for serial-device discovery failures."""


class DeviceNotFoundError(DeviceDiscoveryError):
    """Raised when no usable USB serial adapter can be found."""


class DeviceSelectionError(DeviceDiscoveryError):
    """Raised when automatic selection would be ambiguous."""


@dataclass(frozen=True, slots=True)
class SerialDevice:
    device: str
    description: str | None = None
    hwid: str | None = None
    vid: int | None = None
    pid: int | None = None
    serial_number: str | None = None
    manufacturer: str | None = None
    product: str | None = None

    @property
    def is_usb(self) -> bool:
        return self.vid is not None and self.pid is not None

    @property
    def preferred(self) -> bool:
        return (self.vid, self.pid) in PREFERRED_USB_IDS

    @property
    def usb_id(self) -> str | None:
        if not self.is_usb:
            return None
        return f"{self.vid:04x}:{self.pid:04x}"

    @property
    def display_name(self) -> str:
        value = self.product or self.description or self.manufacturer
        if not value or value.casefold() == "n/a":
            return "Serial device"
        return value


@dataclass(frozen=True, slots=True)
class DeviceSelection:
    port: str
    source: str
    device: SerialDevice | None = None


@dataclass(frozen=True, slots=True)
class DeviceDiagnostic:
    state: str
    message: str
    port: str | None = None
    source: str | None = None
    device: SerialDevice | None = None

    @property
    def ready(self) -> bool:
        """Backward-compatible success flag for passive device selection."""
        return self.state in {"selected", "ready"}


def _from_port_info(info) -> SerialDevice:
    return SerialDevice(
        device=str(info.device),
        description=getattr(info, "description", None),
        hwid=getattr(info, "hwid", None),
        vid=getattr(info, "vid", None),
        pid=getattr(info, "pid", None),
        serial_number=getattr(info, "serial_number", None),
        manufacturer=getattr(info, "manufacturer", None),
        product=getattr(info, "product", None),
    )


def list_serial_devices() -> list[SerialDevice]:
    """Return every enumerated serial port, with useful USB ports first."""
    devices = [_from_port_info(info) for info in list_ports.comports()]
    return sorted(
        devices,
        key=lambda item: (
            not item.preferred,
            not item.is_usb,
            item.device.casefold(),
        ),
    )


def list_candidate_devices() -> list[SerialDevice]:
    """Return likely customer-facing serial adapters, excluding legacy ports."""
    return [device for device in list_serial_devices() if device.is_usb]


def _same_port(left: str, right: str) -> bool:
    if os.name == "nt":
        return left.casefold() == right.casefold()
    return left == right


def _device_for_port(
    port: str,
    devices: list[SerialDevice],
) -> SerialDevice | None:
    return next(
        (device for device in devices if _same_port(device.device, port)),
        None,
    )


def device_matches_preference(
    device: SerialDevice,
    preference: DevicePreference,
) -> bool:
    """Match a remembered adapter by stable USB identity when possible."""
    if preference.vid is not None and preference.pid is not None:
        if (device.vid, device.pid) != (preference.vid, preference.pid):
            return False

        if preference.serial_number:
            return device.serial_number == preference.serial_number

        return True

    if preference.device:
        return _same_port(device.device, preference.device)

    return False


def port_is_available(port: str) -> bool:
    """Check a manually selected or automatically resolved serial port."""
    if not port or port == AUTO_PORT:
        return False

    for device in list_serial_devices():
        if _same_port(device.device, port):
            return True

    # Some POSIX serial devices can exist without useful USB metadata.
    if os.name != "nt":
        return Path(port).exists()

    return False


def resolve_device(
    port: str | None = AUTO_PORT,
    *,
    settings: AppSettings | None = None,
    devices: list[SerialDevice] | None = None,
) -> DeviceSelection:
    """Resolve a requested port to a serial device and explain the selection."""
    requested = (port or AUTO_PORT).strip()
    available = list_serial_devices() if devices is None else list(devices)

    if requested.casefold() != AUTO_PORT:
        return DeviceSelection(
            port=requested,
            source="explicit",
            device=_device_for_port(requested, available),
        )

    current_settings = load_settings() if settings is None else settings
    preference = current_settings.preferred_device

    if preference is not None:
        matches = [
            device
            for device in available
            if device_matches_preference(device, preference)
        ]

        if len(matches) == 1:
            return DeviceSelection(
                port=matches[0].device,
                source="remembered",
                device=matches[0],
            )

        if len(matches) > 1:
            if preference.device:
                previous_port = _device_for_port(preference.device, matches)
                if previous_port is not None:
                    return DeviceSelection(
                        port=previous_port.device,
                        source="remembered-port",
                        device=previous_port,
                    )

            ports = ", ".join(device.device for device in matches)
            raise DeviceSelectionError(
                "The remembered USB adapter matches multiple ports "
                f"({ports}). Select the correct adapter and remember it again."
            )

    preferred = [device for device in available if device.preferred]
    if len(preferred) == 1:
        return DeviceSelection(
            port=preferred[0].device,
            source="tested-adapter",
            device=preferred[0],
        )
    if len(preferred) > 1:
        ports = ", ".join(device.device for device in preferred)
        raise DeviceSelectionError(
            "Multiple tested BetaBrite USB adapters were found "
            f"({ports}). Select one and remember it."
        )

    usb_devices = [device for device in available if device.is_usb]
    if len(usb_devices) == 1:
        return DeviceSelection(
            port=usb_devices[0].device,
            source="single-usb-adapter",
            device=usb_devices[0],
        )
    if len(usb_devices) > 1:
        ports = ", ".join(device.device for device in usb_devices)
        raise DeviceSelectionError(
            "Multiple USB serial adapters were found "
            f"({ports}). Select the BetaBrite adapter and remember it."
        )

    raise DeviceNotFoundError(
        "No USB serial adapter was detected. Plug in the BetaBrite adapter "
        "and try again, or provide a serial port explicitly."
    )


def resolve_port(
    port: str | None = AUTO_PORT,
    *,
    settings: AppSettings | None = None,
    devices: list[SerialDevice] | None = None,
) -> str:
    return resolve_device(
        port,
        settings=settings,
        devices=devices,
    ).port


def remember_port(
    port: str | None = AUTO_PORT,
    *,
    settings_path=None,
) -> DeviceSelection:
    """Remember an adapter so future auto-selection follows its USB identity."""
    devices = list_serial_devices()
    selection = resolve_device(
        port,
        settings=AppSettings(),
        devices=devices,
    )
    device = selection.device

    if device is None:
        if not port_is_available(selection.port):
            raise DeviceNotFoundError(
                f"Serial port {selection.port!r} is not currently available."
            )
        device = SerialDevice(device=selection.port)

    remember_device(device, settings_path)
    return DeviceSelection(
        port=selection.port,
        source="remembered",
        device=device,
    )


def forget_port(*, settings_path=None) -> None:
    forget_saved_device(settings_path)


def diagnose_device(
    port: str | None = AUTO_PORT,
    *,
    settings: AppSettings | None = None,
    devices: list[SerialDevice] | None = None,
) -> DeviceDiagnostic:
    """Return side-effect-free device-selection diagnostics for a UI or CLI."""
    try:
        selection = resolve_device(
            port,
            settings=settings,
            devices=devices,
        )
    except DeviceNotFoundError as exc:
        return DeviceDiagnostic(state="not-found", message=str(exc))
    except DeviceSelectionError as exc:
        return DeviceDiagnostic(state="selection-required", message=str(exc))

    device = selection.device
    if device is None:
        message = f"Serial port {selection.port} is selected."
    else:
        message = f"{device.display_name} on {selection.port} is selected."

    return DeviceDiagnostic(
        state="selected",
        message=message,
        port=selection.port,
        source=selection.source,
        device=device,
    )
