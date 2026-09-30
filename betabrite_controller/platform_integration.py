"""Optional Linux application-menu integration for downloaded AppImages."""
import os
from pathlib import Path
import shutil

from .branding import application_icon_path


def install_appimage():
    source = Path(os.environ.get("APPIMAGE", ""))
    if not source.is_file() or source.suffix != ".AppImage":
        raise ValueError("Open the downloaded AppImage to install its application-menu shortcut.")
    base = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")
    destination = base / "betabrite-controller" / "BetaBrite-Controller.AppImage"
    destination.parent.mkdir(parents=True, exist_ok=True)
    if source.resolve() != destination.resolve():
        shutil.copy2(source, destination)
    destination.chmod(0o755)
    icon = base / "icons" / "hicolor" / "256x256" / "apps" / "dev.grubbs.BetaBriteController.png"
    icon.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(application_icon_path(), icon)
    desktop = base / "applications" / "dev.grubbs.BetaBriteController.desktop"
    desktop.parent.mkdir(parents=True, exist_ok=True)
    # Desktop Entry Exec quoting has its own escaping rules; this is not a shell command.
    executable = destination.as_posix().replace("\\", "\\\\\\\\").replace('"', '\\\\"').replace('`', '\\\\`').replace('$', '\\\\$').replace('%', '%%')
    if "\n" in executable or "\r" in executable:
        raise ValueError("Application folder contains unsupported newline characters")
    desktop.write_text(
        "[Desktop Entry]\nType=Application\nName=BetaBrite Controller\n"
        f'Exec="{executable}"\nIcon=dev.grubbs.BetaBriteController\n'
        "Categories=Utility;\nTerminal=false\n", encoding="utf-8")
    return destination
