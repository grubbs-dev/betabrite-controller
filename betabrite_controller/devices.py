"""Cross-platform serial-device discovery for BetaBrite Controller."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path

from serial.tools import list_ports


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
        return (
            self.product
            or self.description
            or self.manufacturer
            or "Serial device"
        )


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
    """Return serial ports with the tested BetaBrite adapter sorted first."""
    devices = [_from_port_info(info) for info in list_ports.comports()]
    return sorted(
        devices,
        key=lambda item: (
            not item.preferred,
            not item.is_usb,
            item.device.casefold(),
        ),
    )


def _same_port(left: str, right: str) -> bool:
    if os.name == "nt":
        return left.casefold() == right.casefold()
    return left == right


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


def resolve_port(port: str | None = AUTO_PORT) -> str:
    """Resolve ``auto`` to the best USB serial port for the sign.

    Selection order:
      1. Exactly one physically tested PL2303GT adapter.
      2. Exactly one USB serial adapter of any model.
      3. Otherwise require explicit selection.

    Passing an explicit port (for example COM4 or /dev/ttyUSB0) always wins.
    """
    requested = (port or AUTO_PORT).strip()

    if requested.casefold() != AUTO_PORT:
        return requested

    devices = list_serial_devices()

    preferred = [device for device in devices if device.preferred]
    if len(preferred) == 1:
        return preferred[0].device
    if len(preferred) > 1:
        ports = ", ".join(device.device for device in preferred)
        raise DeviceSelectionError(
            "Multiple tested BetaBrite USB adapters were found "
            f"({ports}). Select one explicitly with --port."
        )

    usb_devices = [device for device in devices if device.is_usb]
    if len(usb_devices) == 1:
        return usb_devices[0].device
    if len(usb_devices) > 1:
        ports = ", ".join(device.device for device in usb_devices)
        raise DeviceSelectionError(
            "Multiple USB serial adapters were found "
            f"({ports}). Select the BetaBrite adapter with --port."
        )

    raise DeviceNotFoundError(
        "No USB serial adapter was detected. Plug in the BetaBrite adapter "
        "and try again, or provide a serial port explicitly with --port."
    )
