#!/usr/bin/env bash
set -euo pipefail

APP_NAME="betabrite-controller"
INSTALL_DIR="/opt/$APP_NAME"
VENV_DIR="$INSTALL_DIR/venv"
BIN_DIR="/usr/local/bin"
DESKTOP_DIR="/usr/local/share/applications"
UDEV_DIR="/etc/udev/rules.d"

if [[ $EUID -eq 0 ]]; then
    SUDO=""
else
    SUDO="sudo"
fi

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

echo "==> BetaBrite Controller installer"

if ! command -v python3 >/dev/null 2>&1; then
    echo "ERROR: python3 is required."
    exit 1
fi

if ! python3 -c 'import gi; gi.require_version("Gtk", "4.0"); from gi.repository import Gtk' >/dev/null 2>&1; then
    echo "ERROR: GTK4 Python bindings are required."
    echo "On Fedora:"
    echo "  sudo dnf install python3-gobject gtk4"
    exit 1
fi

echo "==> Installing application to $INSTALL_DIR"

$SUDO rm -rf "$INSTALL_DIR"
$SUDO mkdir -p "$INSTALL_DIR"

$SUDO cp -r \
    "$SCRIPT_DIR/betabrite_controller" \
    "$INSTALL_DIR/"

$SUDO cp \
    "$SCRIPT_DIR/betabrite" \
    "$SCRIPT_DIR/betabrite-gui" \
    "$INSTALL_DIR/"

echo "==> Creating Python environment"

$SUDO python3 -m venv \
    --system-site-packages \
    "$VENV_DIR"

$SUDO "$VENV_DIR/bin/python" -m pip install \
    --upgrade pip

$SUDO "$VENV_DIR/bin/python" -m pip install \
    -r "$SCRIPT_DIR/requirements.txt"

echo "==> Installing CLI launcher"

$SUDO tee "$BIN_DIR/betabrite" >/dev/null <<EOF
#!/usr/bin/env bash
exec "$VENV_DIR/bin/python" "$INSTALL_DIR/betabrite" "\$@"
EOF

$SUDO chmod 755 "$BIN_DIR/betabrite"

echo "==> Installing GUI launcher"

$SUDO tee "$BIN_DIR/betabrite-gui" >/dev/null <<EOF
#!/usr/bin/env bash
exec "$VENV_DIR/bin/python" "$INSTALL_DIR/betabrite-gui" "\$@"
EOF

$SUDO chmod 755 "$BIN_DIR/betabrite-gui"

echo "==> Installing desktop entry"

$SUDO install -Dm644 \
    "$SCRIPT_DIR/packaging/betabrite-controller.desktop" \
    "$DESKTOP_DIR/betabrite-controller.desktop"

echo "==> Installing udev rule"

$SUDO install -Dm644 \
    "$SCRIPT_DIR/packaging/99-betabrite.rules" \
    "$UDEV_DIR/99-betabrite.rules"

$SUDO udevadm control --reload-rules
$SUDO udevadm trigger

# Grant the invoking desktop user access to serial devices.
INSTALL_USER="${SUDO_USER:-$USER}"

if ! getent group dialout >/dev/null 2>&1; then
    echo "==> Creating dialout group"
    $SUDO groupadd --system dialout
fi

if ! id -nG "$INSTALL_USER" | tr ' ' '\n' | grep -qx dialout; then
    echo "==> Adding $INSTALL_USER to dialout"
    $SUDO usermod -aG dialout "$INSTALL_USER"
    GROUP_CHANGED=1
else
    GROUP_CHANGED=0
fi

echo
echo "Installation complete."

if [[ "$GROUP_CHANGED" -eq 1 ]]; then
    echo
    echo "IMPORTANT:"
    echo "  Serial-device permission was granted to $INSTALL_USER."
    echo "  Log out and back in before using the controller."
fi
echo
echo "CLI:"
echo '  betabrite "HELLO WORLD"'
echo
echo "GUI:"
echo "  betabrite-gui"
echo
echo "If the USB adapter was already connected, unplug and reconnect it"
echo "if /dev/betabrite does not appear immediately."
