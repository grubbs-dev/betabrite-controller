#!/usr/bin/env bash
set -euo pipefail

if [[ $EUID -eq 0 ]]; then
    SUDO=""
else
    SUDO="sudo"
fi

echo "==> Removing BetaBrite Controller"

$SUDO rm -rf /opt/betabrite-controller
$SUDO rm -f /usr/local/bin/betabrite
$SUDO rm -f /usr/local/bin/betabrite-gui
$SUDO rm -f /usr/local/share/applications/betabrite-controller.desktop
$SUDO rm -f /etc/udev/rules.d/99-betabrite.rules

$SUDO udevadm control --reload-rules
$SUDO udevadm trigger

echo "BetaBrite Controller removed."
