<p align="center">
  <img src="assets/icons/betabrite-controller-128.png" width="96" height="96" alt="BetaBrite Controller icon">
</p>

# BetaBrite Controller

**Legacy sign. Modern control.**

BetaBrite Controller 1.2.0 is a cross-platform desktop and command-line controller for classic Alpha/BetaBrite serial LED signs. The native Windows, macOS, and Linux applications bundle Python, Qt, and their runtime dependencies; normal desktop users do not need Python, pip, Git, or Qt.

[![CI](https://github.com/grubbs-dev/betabrite-controller/actions/workflows/ci.yml/badge.svg)](https://github.com/grubbs-dev/betabrite-controller/actions/workflows/ci.yml)
[![Native Desktop](https://github.com/grubbs-dev/betabrite-controller/actions/workflows/native-desktop.yml/badge.svg)](https://github.com/grubbs-dev/betabrite-controller/actions/workflows/native-desktop.yml)
[![Latest release](https://img.shields.io/github/v/release/grubbs-dev/betabrite-controller?display_name=tag)](https://github.com/grubbs-dev/betabrite-controller/releases/latest)

## Download and install

Download the current files from [GitHub Releases](https://github.com/grubbs-dev/betabrite-controller/releases/latest).

| Platform | Recommended download | Other portable download |
| --- | --- | --- |
| Windows x64 | `betabrite-controller-1.2.0-windows-x86_64-unsigned-setup.exe` | `.zip` or standalone `.exe` |
| macOS Apple silicon | `betabrite-controller-1.2.0-macos-arm64-unsigned.dmg` | `.zip` containing `BetaBrite Controller.app` |
| Linux x64 | `betabrite-controller-1.2.0-linux-x86_64.tar.gz` | standalone `.bin` |

Windows installs per user under the normal local application directory, creates a Start Menu shortcut, offers an optional desktop shortcut, and does not normally request administrator privileges. The macOS DMG provides the application alongside an Applications shortcut. The Linux archive can run directly through `AppRun`; `install-desktop.sh` adds a per-user application-menu entry without root access.

Windows and macOS files with `-unsigned` in their name were built and tested by GitHub Actions but do not carry commercial platform signing identities. Windows SmartScreen and macOS Gatekeeper may therefore warn before first launch. The project has conditional signing and notarization support ready for use when credentials are available; see [Packaging and distribution](docs/packaging.md).

The existing Fedora GTK4 installer remains available as a compatibility/reference path:

```bash
bash install.sh
```

It installs the Fedora-specific GTK application, udev rule, and serial group configuration. It has not been removed or replaced by the portable Qt package.

## What it does

- Discovers serial adapters on Windows, macOS, and Linux
- Prefers the physically tested Prolific PL2303GT adapter automatically
- Remembers a selected USB adapter by stable USB identity
- Reports clear READY, missing, busy, permission, and transport-failure states
- Composes messages with colors, display modes, special effects, speed 1–5, flash, and wide text
- Sends through the shared `BetaBriteController` backend from the Qt GUI, GTK GUI, or CLI
- Provides quick presets and active connection checks
- Operates locally without telemetry or a network requirement

READY means the selected serial transport opened successfully. A successful send means bytes were transmitted without a transport error. Neither state means the physical sign acknowledged the message; this protocol path is effectively one-way.

## Platform status

| Component | Windows | macOS | Linux |
| --- | :---: | :---: | :---: |
| Controller backend and CLI | CI | CI | CI + hardware |
| Portable Qt desktop | CI | CI | CI + hardware |
| Native portable application | CI | CI | CI + local launch |
| Installer/package | Inno Setup | DMG | tar.gz + desktop integration |
| Legacy GTK4 application | — | — | Fedora |

CI validates the compiled application and packaged smoke path independently on each operating system. Physical BetaBrite hardware validation is primarily on Fedora/Linux; a green Windows or macOS build is not a claim of physical sign testing on that platform.

## Tested hardware

The physically tested configuration is:

- **Sign:** Adaptive Micro Systems BetaBrite 213C-1, Series B
- **Adapter:** DSD TECH SH-RJ12C
- **USB chipset:** Prolific PL2303GT (`067b:23a3`)
- **Serial settings:** 9600 baud, 7 data bits, even parity, 1 stop bit

Other compatible Alpha/BetaBrite signs and USB serial adapters may work, but remain unverified until physically tested. Review [Hardware setup](docs/hardware.md) before changing wiring.

## Use the desktop application

1. Connect the USB-to-serial adapter and sign.
2. Open **BetaBrite Controller**.
3. Select the detected adapter and choose **CHECK CONNECTION**.
4. When the application reports READY, compose a message or effect and choose **SEND TO SIGN**.

The application can remember the adapter across launches. It never interprets READY or a completed serial write as an acknowledgment from the display.

Developers running from a Python environment can launch the same interface with:

```bash
betabrite-desktop
```

The headless runtime check is:

```bash
betabrite-desktop --smoke-test
```

## Command line

Install the Python package for automation or advanced CLI use:

```bash
python -m pip install .
```

Inspect devices and status:

```bash
betabrite --version
betabrite --list-ports
betabrite --status
betabrite --check-connection
```

Send messages and effects:

```bash
betabrite "HELLO WORLD"
betabrite "SYSTEM ONLINE" --color green --mode hold
betabrite "WARNING" --color red --flash --speed 5
betabrite --special fireworks
```

Select or remember a port explicitly:

```bash
betabrite "HELLO" --port COM4
betabrite "HELLO" --port /dev/cu.usbserial-XXXX
betabrite "HELLO" --port /dev/ttyUSB0
betabrite --remember-port
betabrite --forget-port
```

Automatic selection uses `auto`, prefers the tested PL2303GT adapter, and safely refuses to guess when several unrecognized USB serial adapters are connected.

## Troubleshooting

Start with:

```bash
betabrite --list-ports
betabrite --check-connection
```

If no adapter appears, confirm that the operating system sees the USB serial device and has the required driver. On Linux, also confirm serial-device permissions. See [Troubleshooting](docs/troubleshooting.md) for Windows Device Manager, macOS `/dev/cu.*`, and Linux/Fedora guidance.

## Development

Create an environment and install the desktop extra:

```bash
python -m venv .venv
python -m pip install -e ".[desktop]"
```

Run the deterministic suite and desktop smoke test:

```bash
python -m unittest discover -s tests -p "test_*.py" -v
betabrite-desktop --smoke-test
```

Build the native artifact for the current operating system:

```bash
python scripts/build-native.py --dry-run
python scripts/build-native.py
```

Fedora native compilation also needs the matching Python development headers:

```bash
sudo dnf install python3-devel
```

Regenerate the original application icon assets with Pillow:

```bash
python -m pip install "Pillow==12.3.0"
python scripts/generate-icons.py
python scripts/generate-icons.py --check
```

See [Portable desktop application](docs/portable-gui.md), [Packaging and distribution](docs/packaging.md), and [Contributing](CONTRIBUTING.md) for architecture and release details.

## Project layout

```text
betabrite_controller/       shared backend, CLI, and portable Qt application
assets/                     original SVG and generated platform icons
packaging/windows/          per-user Inno Setup installer definition
packaging/linux/            portable launch and desktop-integration assets
scripts/build-native.py     native compiler, packager, smoke test, checksums
scripts/generate-icons.py   deterministic branding asset generator
.github/workflows/          core, native, and tagged-release automation
install.sh                  retained Fedora GTK4 installer
betabrite-gui               retained Fedora GTK4 application
```

Version history is in [CHANGELOG.md](CHANGELOG.md). Every release includes source archives, a Python wheel and sdist, native desktop downloads, platform checksum manifests, and a combined `SHA256SUMS` file.

## License

No open-source license has been selected for this repository. Until one is added, normal copyright restrictions apply to the source code.
