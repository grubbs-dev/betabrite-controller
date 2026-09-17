#!/usr/bin/env bash
set -euo pipefail

APP_NAME="betabrite-controller"
APP_TITLE="BetaBrite Controller"
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
INSTALL_USER="${SUDO_USER:-$USER}"

banner() {
cat <<'EOF'

  ╔══════════════════════════════════════════════════════════╗
  ║                                                          ║
  ║              B E T A B R I T E                           ║
  ║              C O N T R O L L E R                         ║
  ║                                                          ║
  ║              LEGACY SIGN // MODERN CONTROL               ║
  ║                                                          ║
  ╚══════════════════════════════════════════════════════════╝

EOF
}

step() {
    printf '\n  [>] %s\n' "$1"
}

good() {
    printf '  [✓] %s\n' "$1"
}

warn() {
    printf '  [!] %s\n' "$1"
}

fail() {
    printf '\n  [X] %s\n\n' "$1" >&2
    exit 1
}

banner

echo "  This installer configures the current Fedora desktop application"
echo "  and the cross-platform BetaBrite controller package."
echo
echo "  Install location: $INSTALL_DIR"
echo "  User:             $INSTALL_USER"
echo

if ! command -v dnf >/dev/null 2>&1; then
    fail "Automatic desktop installation currently supports Fedora Linux."
fi

step "Checking Fedora dependencies"

PACKAGES=(
    python3
    python3-pip
    python3-gobject
    gtk4
)

MISSING=()

for package in "${PACKAGES[@]}"; do
    if ! rpm -q "$package" >/dev/null 2>&1; then
        MISSING+=("$package")
    fi
done

if ((${#MISSING[@]})); then
    echo "      Installing: ${MISSING[*]}"
    $SUDO dnf install -y "${MISSING[@]}"
else
    good "System dependencies already installed"
fi

command -v python3 >/dev/null 2>&1 ||
    fail "Python 3 installation failed."

step "Installing desktop application files"

$SUDO rm -rf "$INSTALL_DIR"
$SUDO mkdir -p "$INSTALL_DIR"

$SUDO install -Dm755 \
    "$SCRIPT_DIR/betabrite-gui" \
    "$INSTALL_DIR/betabrite-gui"

$SUDO install -Dm644 \
    "$SCRIPT_DIR/README.md" \
    "$INSTALL_DIR/README.md"

$SUDO install -Dm644 \
    "$SCRIPT_DIR/CHANGELOG.md" \
    "$INSTALL_DIR/CHANGELOG.md"

good "Desktop application files installed"

step "Building isolated controller runtime"

$SUDO python3 -m venv \
    --system-site-packages \
    "$VENV_DIR"

$SUDO "$VENV_DIR/bin/python" -m pip install \
    --disable-pip-version-check \
    --quiet \
    --upgrade pip setuptools wheel

$SUDO "$VENV_DIR/bin/python" -m pip install \
    --disable-pip-version-check \
    --quiet \
    "$SCRIPT_DIR"

if ! "$VENV_DIR/bin/python" - <<'PYTEST'
import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # noqa: F401

import alphasign
import serial
from importlib.metadata import version

print(f"      package version: {version('betabrite-controller')}")
print("      GTK4 bindings: OK")
print("      serial runtime: OK")
PYTEST
then
    fail "Installed Python runtime health check failed."
fi

good "Packaged controller runtime ready"

step "Installing command launchers"

$SUDO rm -f \
    /usr/local/sbin/betabrite \
    /usr/local/sbin/betabrite-gui \
    "$BIN_DIR/betabrite" \
    "$BIN_DIR/betabrite-gui"

$SUDO tee "$BIN_DIR/betabrite" >/dev/null <<EOF
#!/usr/bin/env bash
exec "$VENV_DIR/bin/betabrite" "\$@"
EOF

$SUDO tee "$BIN_DIR/betabrite-gui" >/dev/null <<EOF
#!/usr/bin/env bash
exec "$VENV_DIR/bin/python" "$INSTALL_DIR/betabrite-gui" "\$@"
EOF

$SUDO chmod 755 \
    "$BIN_DIR/betabrite" \
    "$BIN_DIR/betabrite-gui"

good "CLI installed: $BIN_DIR/betabrite"
good "GUI installed: $BIN_DIR/betabrite-gui"

step "Adding desktop application"

$SUDO install -Dm644 \
    "$SCRIPT_DIR/packaging/betabrite-controller.desktop" \
    "$DESKTOP_DIR/betabrite-controller.desktop"

if command -v update-desktop-database >/dev/null 2>&1; then
    $SUDO update-desktop-database "$DESKTOP_DIR" >/dev/null 2>&1 || true
fi

good "BetaBrite Controller added to application menu"

step "Configuring tested BetaBrite USB hardware"

$SUDO install -Dm644 \
    "$SCRIPT_DIR/packaging/99-betabrite.rules" \
    "$UDEV_DIR/99-betabrite.rules"

$SUDO udevadm control --reload-rules
$SUDO udevadm trigger

if ! getent group dialout >/dev/null 2>&1; then
    $SUDO groupadd --system dialout
fi

GROUP_CHANGED=0

if ! id -nG "$INSTALL_USER" | tr ' ' '\n' | /usr/bin/grep -qx dialout; then
    $SUDO usermod -aG dialout "$INSTALL_USER"
    GROUP_CHANGED=1
fi

good "Serial hardware permissions configured"

step "Running installation health check"

[[ -x "$BIN_DIR/betabrite" ]] ||
    fail "CLI launcher was not installed."

[[ -x "$BIN_DIR/betabrite-gui" ]] ||
    fail "GUI launcher was not installed."

[[ -f "$DESKTOP_DIR/betabrite-controller.desktop" ]] ||
    fail "Desktop application was not installed."

[[ -f "$UDEV_DIR/99-betabrite.rules" ]] ||
    fail "USB hardware rule was not installed."

"$VENV_DIR/bin/betabrite" --version ||
    fail "Installed CLI could not start."

"$VENV_DIR/bin/betabrite" --list-ports >/dev/null ||
    fail "Installed CLI device discovery failed."

good "Controller package and CLI operational"

DETECTED="$("$VENV_DIR/bin/python" - <<'PY'
from betabrite_controller.devices import list_candidate_devices
print(", ".join(device.device for device in list_candidate_devices()))
PY
)"

echo
echo "  ╔══════════════════════════════════════════════════════════╗"
echo "  ║                 INSTALLATION COMPLETE                    ║"
echo "  ╚══════════════════════════════════════════════════════════╝"
echo

if [[ -n "$DETECTED" ]]; then
    good "USB serial adapter detected: $DETECTED"
else
    warn "No USB serial adapter detected yet."
    echo "      Plug in the BetaBrite USB-to-RJ12 adapter when ready."
fi

if [[ "$GROUP_CHANGED" -eq 1 ]]; then
    echo
    warn "ONE LOGOUT IS REQUIRED"
    echo
    echo "      Serial access was just enabled for $INSTALL_USER."
    echo "      Log out of Fedora and back in once."
fi

echo
echo "  START THE APP"
echo
echo "      Open the Fedora application menu and search:"
echo
echo "          BetaBrite Controller"
echo
echo "      Or run:"
echo
echo "          betabrite-gui"
echo
echo "  TERMINAL CONTROL"
echo
echo '      betabrite "HELLO WORLD"'
echo "      betabrite --check-connection"
echo
echo "  User settings are stored separately and survive application upgrades."
echo
echo "  Ready."
echo
