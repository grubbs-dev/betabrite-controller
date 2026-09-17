# BetaBrite Controller

**Legacy sign. Modern control.**

BetaBrite Controller is a controller for classic Alpha/BetaBrite LED signs. The controller core and command-line interface are designed to work on Windows, macOS, and Linux. The current GTK4 desktop GUI remains Linux/Fedora-specific while the portable desktop application is being built.

[![CI](https://github.com/grubbs-dev/betabrite-controller/actions/workflows/ci.yml/badge.svg)](https://github.com/grubbs-dev/betabrite-controller/actions/workflows/ci.yml)
[![Latest release](https://img.shields.io/github/v/release/grubbs-dev/betabrite-controller?display_name=tag)](https://github.com/grubbs-dev/betabrite-controller/releases/latest)
[![Core platforms](https://img.shields.io/badge/core-Windows%20%7C%20macOS%20%7C%20Linux-blue)](#platform-support)

## What it does

BetaBrite Controller sends custom messages, colors, display modes, speeds, formatting, and built-in special effects to supported Alpha/BetaBrite serial LED signs.

The project currently includes:

- Cross-platform serial discovery for Windows, macOS, and Linux
- Automatic detection of the physically tested PL2303GT USB serial adapter
- Command-line controller for messages, effects, automation, and diagnostics
- Persistent per-user USB adapter selection with stable USB identity matching
- Active serial connection checks with customer-friendly error states
- Portable PySide6 / Qt desktop controller for Windows, macOS, and Linux
- GTK4 desktop controller for Fedora Linux using the same connection-state backend
- Fedora one-click installer with udev and serial-permission setup
- Hardware and wiring documentation for the tested sign/adapter combination
- Automated tests across Windows, macOS, and Linux

## Platform support

| Component | Windows | macOS | Linux |
| --- | :---: | :---: | :---: |
| Controller backend | ✓ | ✓ | ✓ |
| Serial auto-discovery | ✓ | ✓ | ✓ |
| Command-line interface | ✓ | ✓ | ✓ |
| Portable Qt GUI (development) | CI | CI | CI |
| Current GTK4 GUI | — | — | ✓ |
| Current one-click installer | — | — | Fedora |

The portable Qt GUI is now under active 1.2 development. The controller surface and runtime are CI-tested on Windows, macOS, and Linux; physical BetaBrite validation remains centered on Fedora until the same hardware path is exercised on Windows and macOS and native packaging is complete.

## Tested hardware

The physically tested configuration is:

- **Sign:** Adaptive Micro Systems BetaBrite 213C-1, Series B
- **Adapter:** DSD TECH SH-RJ12C
- **USB chipset:** Prolific PL2303GT (`067b:23a3`)
- **Serial settings:** 9600 baud, 7 data bits, even parity, 1 stop bit

Other compatible Alpha/BetaBrite signs and USB serial adapters may work, but should be treated as unverified until physically tested.

See [Hardware setup](docs/hardware.md) before changing wiring.

## Serial discovery

By default the controller uses:

```text
auto
```

Automatic selection prefers the tested Prolific PL2303GT adapter. If that adapter is not present and exactly one other USB serial adapter is connected, that device is selected.

List detected ports:

```bash
betabrite --list-ports
```

Example devices:

```text
Windows   COM4
macOS     /dev/cu.usbserial-XXXX
Linux     /dev/ttyUSB0
```

You can always select a port manually:

```bash
betabrite "HELLO WORLD" --port COM4
betabrite "HELLO WORLD" --port /dev/cu.usbserial-XXXX
betabrite "HELLO WORLD" --port /dev/ttyUSB0
```

## Install

### Fedora desktop application

The current complete GUI installer supports Fedora Linux.

1. Open the [latest release](https://github.com/grubbs-dev/betabrite-controller/releases/latest).
2. Download and extract the release archive.
3. Open a terminal in the extracted folder.
4. Run:

```bash
bash install.sh
```

The installer configures the GTK4 application, installs the controller through the standard Python package metadata, creates an isolated runtime with Fedora's GTK bindings, adds launchers, configures the tested USB adapter rule, and enables serial permissions.

### Cross-platform controller core

For development, testing, and CLI use on Windows, macOS, or Linux:

```bash
python -m pip install .
```

After installation:

```bash
betabrite --version
betabrite --list-ports
betabrite "HELLO WORLD"
```

This Python-based installation is an interim developer/advanced-user path. Tagged releases also publish a standard wheel and Python source distribution. The portable GUI release will bundle its runtime and dependencies so normal desktop users do not need Python or pip.

### Portable desktop development

Install the Qt desktop extra:

```bash
python -m pip install -e ".[desktop]"
```

Verify the runtime without opening a window:

```bash
betabrite-desktop --smoke-test
```

Launch the portable desktop foundation:

```bash
betabrite-desktop
```

See [Portable desktop application](docs/portable-gui.md) for architecture and migration status.

### Native desktop build development

Phase 8 adds native build automation around the portable Qt controller. Builds are produced on the operating system they target with Qt for Python's `pyside6-deploy` wrapper around Nuitka.

Development artifacts currently include:

| Platform | Development artifacts |
| --- | --- |
| Windows | portable `.exe`, `.zip`, and an unsigned Inno Setup installer |
| macOS | `.app` packaged as `.zip`, plus an unsigned `.dmg` |
| Linux | portable self-contained `.bin` and `.tar.gz` |

These development builds bundle the Python and Qt runtime. They do not require the user to install Python, pip, or Git.

Build the native artifact for the current operating system. On Fedora, install `python3-devel` first so Nuitka can access `Python.h`:

```bash
sudo dnf install python3-devel
python scripts/build-native.py
```

Inspect the deployment command without compiling:

```bash
python scripts/build-native.py --dry-run
```

Native build CI uploads the resulting artifacts for Windows, macOS, and Linux. Code signing, Apple notarization, and final release promotion remain separate release gates.

## Use

### Command line

Send a simple message:

```bash
betabrite "HELLO WORLD"
```

Choose a color and mode:

```bash
betabrite "SYSTEM ONLINE" --color green --mode hold
```

Add formatting and speed:

```bash
betabrite "WARNING" --color red --flash --speed 5
```

Run a built-in sign effect:

```bash
betabrite --special fireworks
```

Inspect serial devices:

```bash
betabrite --list-ports
```

Inspect passive adapter selection:

```bash
betabrite --status
```

Actively verify that the serial adapter can be opened:

```bash
betabrite --check-connection
```

Remember or clear the preferred adapter:

```bash
betabrite --remember-port
betabrite --forget-port
```

See all options:

```bash
betabrite --help
```

### Portable desktop foundation

During 1.2 development, launch the cross-platform Qt application with:

```bash
betabrite-desktop
```

The portable application provides real adapter discovery, remembered-adapter controls, active READY diagnostics, message composition, colors, display modes, special effects, speed, flash/wide formatting, quick presets, and physical transmission through the same controller backend used by the CLI and Fedora GTK application.

### Fedora desktop app

Open the application launcher and search for **BetaBrite Controller**, or run:

```bash
betabrite-gui
```

The current GUI provides message entry, colors, motion modes, special effects, speed, flash/wide text controls, quick-transmit presets, connection monitoring, and hardware setup.

## Troubleshooting

Start with:

```bash
betabrite --list-ports
```

If the adapter appears but automatic selection is ambiguous, pass the correct device explicitly with `--port`.

See [Troubleshooting](docs/troubleshooting.md) for platform-specific checks.

## Development

Create a virtual environment and install the project:

```bash
python -m venv .venv
python -m pip install -e .
```

Activate the environment using the command appropriate for your operating system, then run:

```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

GitHub CI runs the controller core on Windows, macOS, and Linux.

## Project layout

```text
betabrite-controller/
├── betabrite                     # source-checkout CLI shim
├── betabrite-gui                 # current GTK4 desktop application
├── betabrite_controller/
│   ├── controller.py             # sign protocol/controller
│   ├── devices.py                # cross-platform serial discovery
│   ├── desktop.py                # portable PySide6 desktop entry point
│   ├── desktop_model.py          # toolkit-independent desktop view model
│   ├── desktop_controls.py       # toolkit-independent composer/transmit model
│   └── cli.py                    # portable command-line interface
├── packaging/                    # current Linux desktop/udev assets
├── tests/
├── docs/
├── scripts/
├── pyproject.toml
├── install.sh                    # current Fedora GUI installer
└── uninstall.sh
```

## Releases

Version history is tracked in [CHANGELOG.md](CHANGELOG.md).

Tagged releases publish complete source archives, a standard Python wheel, a Python source distribution, and checksums. See [Packaging and distribution](docs/packaging.md) for the artifact boundary and future native-app targets.

Native Windows, macOS, and portable Linux desktop artifacts will be added only after the portable GUI packaging phase is implemented and validated.

## License

No open-source license has been selected for this repository yet. Until a license is added, normal copyright restrictions apply to the source code.
