# Portable desktop application

BetaBrite Controller 1.2.0 includes a release-grade PySide6/Qt 6 desktop controller for Windows, macOS, and Linux. Native packages bundle the runtime; the Python installation described here is primarily for development.

The existing GTK4 application remains in the repository as the Fedora compatibility/reference interface while the Qt packages accumulate broader physical hardware validation.

## Architecture

The portable application reuses the established `betabrite_controller` backend rather than implementing serial or Alpha/BetaBrite protocol behavior in the GUI.

Shared backend responsibilities:

- serial discovery and tested-adapter preference
- persistent adapter identity
- active transport diagnostics
- customer-facing connection states
- Alpha/BetaBrite protocol formatting and transmission

Portable desktop responsibilities:

- present device state and allow adapter selection
- remember or forget an adapter
- compose messages, modes, colors, speed, formatting, and effects
- gate transmission on an active READY check
- surface transport failures without claiming a display acknowledgment

`desktop_model.py` contains toolkit-independent adapter presentation logic. `desktop_controls.py` contains toolkit-independent draft validation, presets, and transmit-state logic. `desktop.py` owns the Qt window, while `desktop_launcher.py` keeps the smoke-test path headless-safe.

## Features

The portable controller provides:

- real serial adapter enumeration
- tested/saved adapter labels
- active connection checks and passive plug/unplug monitoring
- remembered-adapter controls
- message composition and quick presets
- backend-provided colors and display modes
- built-in special effects
- speed 1–5, flash, and wide-text formatting
- READY-gated physical transmission through `BetaBriteController`
- explicit messaging that successful writes do not prove a display acknowledgment

READY means the selected serial transport opened. It is not a sign ACK.

## Development

Install the desktop extra:

```bash
python -m pip install -e ".[desktop]"
```

Verify the runtime without a window:

```bash
betabrite-desktop --smoke-test
```

Launch the application:

```bash
betabrite-desktop
```

The application icon is loaded from packaged project data, so wheel installs and Nuitka applications use the same branding.

## Distribution and validation

Target-specific CI compiles and executes the actual native binary on Windows, macOS, and Linux, then executes the application again from the platform package. The release outputs are:

| Platform | Outputs |
| --- | --- |
| Windows x64 | standalone executable, portable ZIP, per-user installer |
| macOS ARM64 | app-preserving ZIP and DMG |
| Linux x64 | standalone binary and tar package with desktop integration |

Unsigned Windows and macOS files are labeled in their filenames. Optional signing and notarization hooks do not affect ordinary pull-request builds.

The cross-platform CI checks validate native startup and package structure. Physical sign hardware has primarily been exercised on Fedora/Linux with the documented BetaBrite 213C and PL2303GT setup; Windows and macOS hardware operation should not be inferred from CI alone.

See [Packaging and distribution](packaging.md) for build, installer, checksum, signing, notarization, and release details.
