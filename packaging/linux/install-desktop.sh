#!/usr/bin/env bash
set -euo pipefail

SOURCE_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
APP_DIR="$DATA_HOME/betabrite-controller"
DESKTOP_DIR="$DATA_HOME/applications"
ICON_DIR="$DATA_HOME/icons/hicolor/256x256/apps"
DESKTOP_FILE="$DESKTOP_DIR/dev.grubbs.BetaBriteController.desktop"

mkdir -p "$APP_DIR" "$DESKTOP_DIR" "$ICON_DIR"
install -m 755 "$SOURCE_DIR/BetaBriteController.bin" "$APP_DIR/BetaBriteController.bin"
install -m 644 \
    "$SOURCE_DIR/dev.grubbs.BetaBriteController.png" \
    "$ICON_DIR/dev.grubbs.BetaBriteController.png"

executable="$APP_DIR/BetaBriteController.bin"
escaped="${executable//\\/\\\\}"
escaped="${escaped//&/\\&}"
escaped="${escaped//|/\\|}"
sed "s|@EXECUTABLE@|$escaped|" \
    "$SOURCE_DIR/betabrite-controller.desktop.in" \
    > "$DESKTOP_FILE"
chmod 644 "$DESKTOP_FILE"

if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$DESKTOP_DIR" >/dev/null 2>&1 || true
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -f -t "$DATA_HOME/icons/hicolor" >/dev/null 2>&1 || true
fi

printf 'Installed BetaBrite Controller for %s.\n' "$USER"
printf 'User settings remain in the platform configuration directory.\n'
