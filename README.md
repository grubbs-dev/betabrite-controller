# BetaBrite Controller

**Legacy sign. Modern control.**

A small Linux controller for classic Alpha/BetaBrite LED signs, with both a GTK4 desktop app and a command-line interface.

[![CI](https://github.com/grubbs-dev/betabrite-controller/actions/workflows/ci.yml/badge.svg)](https://github.com/grubbs-dev/betabrite-controller/actions/workflows/ci.yml)
[![Latest release](https://img.shields.io/github/v/release/grubbs-dev/betabrite-controller?display_name=tag)](https://github.com/grubbs-dev/betabrite-controller/releases/latest)
[![Platform](https://img.shields.io/badge/platform-Fedora%20Linux-blue)](#requirements)

## What it does

BetaBrite Controller sends messages, colors, display modes, speeds, formatting, and built-in special effects to supported Alpha/BetaBrite serial LED signs.

It includes:

- GTK4 desktop controller with live sign connection status
- Command-line controller for scripts and quick messages
- Automatic `/dev/betabrite` device naming through udev
- Fedora installer that configures dependencies, permissions, launchers, and the desktop entry
- Hardware setup screen with the tested RJ12 wiring reference
- Installation health checks and unit tests

## Tested hardware

The current release is physically tested with:

- **Sign:** Adaptive Micro Systems BetaBrite 213C-1, Series B
- **Adapter:** DSD TECH SH-RJ12C using a Prolific PL2303GT USB serial chipset
- **Serial settings:** 9600 baud, 7 data bits, even parity, 1 stop bit
- **Operating system:** Fedora Linux

Other Alpha/BetaBrite models may work with the same protocol, but they are not claimed as tested unless listed here.

See [Hardware setup](docs/hardware.md) before rewiring any cable. Wire colors are not a universal serial standard.

## Install

### Recommended: latest release

1. Open the [latest release](https://github.com/grubbs-dev/betabrite-controller/releases/latest).
2. Download the Linux `.tar.gz` or `.zip` archive.
3. Extract it.
4. Open a terminal in the extracted folder and run:

```bash
bash install.sh
```

The installer will:

- install Fedora system dependencies with `dnf`
- create an isolated Python environment under `/opt/betabrite-controller`
- install the Alpha sign protocol dependency
- create the `betabrite` and `betabrite-gui` launchers
- install the desktop application entry
- install the udev rule for the tested USB adapter
- add the current user to `dialout` when required
- run an installation health check

If the installer says a logout is required, log out of Fedora and back in once so the new serial-device group membership takes effect.

### Install from source

```bash
git clone https://github.com/grubbs-dev/betabrite-controller.git
cd betabrite-controller
bash install.sh
```

## Use

### Desktop app

Open the application launcher and search for **BetaBrite Controller**, or run:

```bash
betabrite-gui
```

The GUI provides message entry, colors, motion modes, special effects, speed, flash/wide text controls, quick-transmit presets, connection monitoring, and a hardware setup screen.

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

See all options:

```bash
betabrite --help
```

List supported values:

```bash
betabrite --list-colors
betabrite --list-modes
betabrite --list-special
```

## Troubleshooting

If the app reports **SIGN OFFLINE**, start with:

```bash
ls -l /dev/betabrite
```

If the device is missing, see [Troubleshooting](docs/troubleshooting.md) for USB detection, udev, `dialout`, and serial-device checks.

## Uninstall

From a copy of the repository or release archive:

```bash
bash uninstall.sh
```

This removes the application, command launchers, desktop entry, and udev rule. It does not remove Fedora packages that may also be used by other applications.

## Development

Run the unit tests from the repository root:

```bash
bash test.sh
```

For a clean development environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m unittest discover -s tests -p 'test_*.py' -v
```

Release archives are built with:

```bash
bash scripts/build-release.sh v1.0.0
```

See [Contributing](CONTRIBUTING.md) for the development workflow.

## Project layout

```text
betabrite-controller/
├── betabrite                     # CLI entry point
├── betabrite-gui                 # GTK4 desktop application
├── betabrite_controller/         # controller backend
├── packaging/                    # desktop entry and udev rule
├── tests/                        # unit tests
├── docs/                         # hardware and troubleshooting docs
├── scripts/                      # release tooling
├── install.sh                    # Fedora installer
└── uninstall.sh                  # uninstaller
```

## Releases

Pushing a version tag such as `v1.0.0` runs the release workflow. It executes the test suite, builds `.tar.gz` and `.zip` distributions, generates SHA-256 checksums, and publishes a GitHub Release.

Version history is tracked in [CHANGELOG.md](CHANGELOG.md).

## License

No open-source license has been selected for this repository yet. Until a license is added, normal copyright restrictions apply to the source code.
