#!/usr/bin/env bash
set -euo pipefail

DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
APP_DIR="$DATA_HOME/betabrite-controller"
DESKTOP_DIR="$DATA_HOME/applications"
ICON_DIR="$DATA_HOME/icons/hicolor/256x256/apps"

rm -f "$APP_DIR/BetaBriteController.bin"
rmdir "$APP_DIR" 2>/dev/null || true
rm -f "$DESKTOP_DIR/dev.grubbs.BetaBriteController.desktop"
rm -f "$ICON_DIR/dev.grubbs.BetaBriteController.png"

if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$DESKTOP_DIR" >/dev/null 2>&1 || true
fi

printf 'Removed BetaBrite Controller application files.\n'
printf 'User settings were preserved.\n'
