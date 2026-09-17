#!/usr/bin/env bash
set -euo pipefail

PURGE_SETTINGS=0

if [[ "${1:-}" == "--purge-settings" ]]; then
    PURGE_SETTINGS=1
elif [[ $# -gt 0 ]]; then
    echo "Usage: $0 [--purge-settings]" >&2
    exit 2
fi

if [[ $EUID -eq 0 ]]; then
    SUDO=""
else
    SUDO="sudo"
fi

TARGET_USER="${SUDO_USER:-$USER}"
TARGET_HOME="$(getent passwd "$TARGET_USER" | cut -d: -f6)"
TARGET_HOME="${TARGET_HOME:-$HOME}"
SETTINGS_DIR="${XDG_CONFIG_HOME:-$TARGET_HOME/.config}/betabrite-controller"

echo "==> Removing BetaBrite Controller"

$SUDO rm -rf /opt/betabrite-controller
$SUDO rm -f /usr/local/bin/betabrite
$SUDO rm -f /usr/local/bin/betabrite-gui
$SUDO rm -f /usr/local/sbin/betabrite
$SUDO rm -f /usr/local/sbin/betabrite-gui
$SUDO rm -f /usr/local/share/applications/betabrite-controller.desktop
$SUDO rm -f /etc/udev/rules.d/99-betabrite.rules

$SUDO udevadm control --reload-rules
$SUDO udevadm trigger

if command -v update-desktop-database >/dev/null 2>&1; then
    $SUDO update-desktop-database /usr/local/share/applications >/dev/null 2>&1 || true
fi

if [[ "$PURGE_SETTINGS" -eq 1 ]]; then
    rm -rf "$SETTINGS_DIR"
    echo "User settings removed: $SETTINGS_DIR"
else
    echo "User settings preserved: $SETTINGS_DIR"
    echo "Use '$0 --purge-settings' to remove them too."
fi

echo "BetaBrite Controller removed."
