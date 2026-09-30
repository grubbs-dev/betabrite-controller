"""Persistent, cross-platform settings for BetaBrite Controller."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
import json
import os
from pathlib import Path, PurePosixPath
import sys
import tempfile
import logging


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
            device=_optional_text(value.get("device")),
            vid=_optional_int(value.get("vid")),
            pid=_optional_int(value.get("pid")),
            serial_number=_optional_text(value.get("serial_number")),
            manufacturer=_optional_text(value.get("manufacturer")),
            product=_optional_text(value.get("product")),
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
    signs: dict[str, DevicePreference] = field(default_factory=dict)
    draft: dict = field(default_factory=dict)
    saved_messages: dict[str, dict] = field(default_factory=dict)
    recent_messages: list[dict] = field(default_factory=list)

    @classmethod
    def from_mapping(cls, value) -> "AppSettings":
        if not isinstance(value, dict):
            return cls()
        return cls(
            preferred_device=DevicePreference.from_mapping(
                value.get("preferred_device")
            ),
            signs={name: device for name, item in _mapping(value.get("signs")).items()
                   if (device := DevicePreference.from_mapping(item)) is not None},
            draft=_draft(value.get("draft")),
            saved_messages={name: draft for name, item in _mapping(value.get("saved_messages")).items()
                            if (draft := _draft(item))},
            recent_messages=[draft for item in (value.get("recent_messages") or [])[:20]
                             if (draft := _draft(item))]
            if isinstance(value.get("recent_messages"), list) else [],
        )

    def to_mapping(self) -> dict:
        return {
            "schema_version": SETTINGS_SCHEMA_VERSION,
            "signs": {name: device.to_mapping() for name, device in self.signs.items()},
            "draft": self.draft,
            "saved_messages": self.saved_messages,
            "recent_messages": self.recent_messages,
            "preferred_device": (
                self.preferred_device.to_mapping()
                if self.preferred_device is not None
                else None
            ),
        }


def _optional_text(value) -> str | None:
    return value if isinstance(value, str) and value else None


def _mapping(value) -> dict:
    return value if isinstance(value, dict) else {}


def _draft(value) -> dict:
    # Import lazily: the controller also uses settings during discovery.
    from .desktop_controls import MessageDraft
    if not isinstance(value, dict):
        return {}
    try:
        MessageDraft(**value).validate()
    except (ValueError, TypeError, AttributeError):
        return {}
    return value


def _optional_int(value) -> int | None:
    if value is None:
        return None
    try:
        number = int(value)
        return number if 0 <= number <= 65535 else None
    except (TypeError, ValueError, OverflowError):
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
    base = Path(xdg) if xdg and PurePosixPath(xdg).is_absolute() else home / ".config"
    return base / APP_DIR_NAME


def settings_path(**kwargs) -> Path:
    return config_dir(**kwargs) / "settings.json"


def load_settings(path: Path | str | None = None) -> AppSettings:
    target = Path(path) if path is not None else settings_path()
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError, ValueError, RecursionError):
        if target.exists():
            logging.getLogger(__name__).warning("Could not read settings; using defaults")
        return AppSettings()
    return AppSettings.from_mapping(data)


def save_settings(
    settings: AppSettings,
    path: Path | str | None = None,
) -> Path:
    target = Path(path) if path is not None else settings_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(settings.to_mapping(), indent=2, sort_keys=True) + "\n"
    # Unique, private temporary files avoid symlinks and concurrent-writer collisions.
    descriptor, name = tempfile.mkstemp(dir=target.parent, prefix=".settings-")
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)
    return target


def remember_device(device, path: Path | str | None = None) -> Path:
    return save_settings(
        replace(load_settings(path), preferred_device=DevicePreference.from_device(device)),
        path,
    )


def forget_device(path: Path | str | None = None) -> Path:
    return save_settings(replace(load_settings(path), preferred_device=None), path)
