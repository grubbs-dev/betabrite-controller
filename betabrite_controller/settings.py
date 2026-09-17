"""Persistent, cross-platform settings for BetaBrite Controller."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import sys


SETTINGS_SCHEMA_VERSION = 1
APP_DIR_NAME = "betabrite-controller"
WINDOWS_APP_DIR_NAME = "BetaBrite Controller"


@dataclass(frozen=True, slots=True)
class DevicePreference:
    """Stable identity for the USB serial adapter selected by the user."""

    device: str | None = None
    vid: int | None = None
    pid: int | None = None
    serial_number: str | None = None
    manufacturer: str | None = None
    product: str | None = None

    @classmethod
    def from_device(cls, device) -> "DevicePreference":
        return cls(
            device=getattr(device, "device", None),
            vid=getattr(device, "vid", None),
            pid=getattr(device, "pid", None),
            serial_number=getattr(device, "serial_number", None),
            manufacturer=getattr(device, "manufacturer", None),
            product=getattr(device, "product", None),
        )

    @classmethod
    def from_mapping(cls, value) -> "DevicePreference | None":
        if not isinstance(value, dict):
            return None
        return cls(
            device=value.get("device"),
            vid=_optional_int(value.get("vid")),
            pid=_optional_int(value.get("pid")),
            serial_number=value.get("serial_number"),
            manufacturer=value.get("manufacturer"),
            product=value.get("product"),
        )

    def to_mapping(self) -> dict:
        return {
            "device": self.device,
            "vid": self.vid,
            "pid": self.pid,
            "serial_number": self.serial_number,
            "manufacturer": self.manufacturer,
            "product": self.product,
        }

    @property
    def usb_id(self) -> str | None:
        if self.vid is None or self.pid is None:
            return None
        return f"{self.vid:04x}:{self.pid:04x}"

    @property
    def label(self) -> str:
        return self.product or self.manufacturer or self.device or "Serial adapter"


@dataclass(frozen=True, slots=True)
class AppSettings:
    preferred_device: DevicePreference | None = None

    @classmethod
    def from_mapping(cls, value) -> "AppSettings":
        if not isinstance(value, dict):
            return cls()
        return cls(
            preferred_device=DevicePreference.from_mapping(
                value.get("preferred_device")
            )
        )

    def to_mapping(self) -> dict:
        return {
            "schema_version": SETTINGS_SCHEMA_VERSION,
            "preferred_device": (
                self.preferred_device.to_mapping()
                if self.preferred_device is not None
                else None
            ),
        }


def _optional_int(value) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def config_dir(
    *,
    platform_name: str | None = None,
    environ: dict[str, str] | None = None,
    home: Path | None = None,
) -> Path:
    """Return the per-user application configuration directory."""
    env = os.environ if environ is None else environ
    override = env.get("BETABRITE_CONFIG_DIR")
    if override:
        return Path(override).expanduser()

    platform_name = sys.platform if platform_name is None else platform_name
    home = Path.home() if home is None else Path(home)

    if platform_name.startswith("win"):
        appdata = env.get("APPDATA")
        base = Path(appdata) if appdata else home / "AppData" / "Roaming"
        return base / WINDOWS_APP_DIR_NAME

    if platform_name == "darwin":
        return home / "Library" / "Application Support" / WINDOWS_APP_DIR_NAME

    xdg = env.get("XDG_CONFIG_HOME")
    base = Path(xdg) if xdg else home / ".config"
    return base / APP_DIR_NAME


def settings_path(**kwargs) -> Path:
    return config_dir(**kwargs) / "settings.json"


def load_settings(path: Path | str | None = None) -> AppSettings:
    target = Path(path) if path is not None else settings_path()
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return AppSettings()
    return AppSettings.from_mapping(data)


def save_settings(
    settings: AppSettings,
    path: Path | str | None = None,
) -> Path:
    target = Path(path) if path is not None else settings_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f".{target.name}.tmp")
    payload = json.dumps(settings.to_mapping(), indent=2, sort_keys=True) + "\n"
    temporary.write_text(payload, encoding="utf-8")
    os.replace(temporary, target)
    return target


def remember_device(device, path: Path | str | None = None) -> Path:
    return save_settings(
        AppSettings(preferred_device=DevicePreference.from_device(device)),
        path,
    )


def forget_device(path: Path | str | None = None) -> Path:
    return save_settings(AppSettings(), path)
