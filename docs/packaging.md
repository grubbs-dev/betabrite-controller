# Packaging and distribution

BetaBrite Controller has two packaging layers today:

1. A standard Python package for the cross-platform controller core and CLI.
2. A Fedora desktop installer for the current GTK4 graphical application.

The Python package is not the final nontechnical customer experience. It exists so the same tested controller code can be installed, validated, and reused by future desktop packaging.

## Current release artifacts

Tagged releases are expected to publish:

- `betabrite-controller-vX.Y.Z.tar.gz` — complete source/Fedora installer archive
- `betabrite-controller-vX.Y.Z.zip` — complete source/Fedora installer archive
- `betabrite_controller-X.Y.Z-py3-none-any.whl` — standard Python wheel
- `betabrite_controller-X.Y.Z.tar.gz` — standard Python source distribution
- `SHA256SUMS` — checksums for all release artifacts

The wheel and Python source distribution are intended for development, automation, and advanced CLI use. Normal desktop users should use a native/portable desktop application once those artifacts are implemented.

## Fedora installer

`install.sh` creates an isolated virtual environment with access to Fedora's system GTK4 bindings and installs the project through `pyproject.toml`. This keeps the installed backend aligned with the same package metadata exercised by CI.

Application launchers:

- `/usr/local/bin/betabrite`
- `/usr/local/bin/betabrite-gui`

Application files:

- `/opt/betabrite-controller`

Per-user settings are stored separately under the platform configuration directory and survive application upgrades and normal uninstall. Use `uninstall.sh --purge-settings` only when settings should also be removed.

## Future portable desktop artifacts

The portable GUI phase should produce artifacts that do not require users to install Python, Git, pip, or development tools.

Target deliverables:

| Platform | Target artifact |
| --- | --- |
| Windows | signed installer `.exe` plus application executable |
| macOS | signed/notarized `.app` distributed in `.dmg` |
| Linux | portable AppImage, with distro packages considered later |

The future GUI should consume `betabrite_controller` as an internal package rather than duplicating serial discovery, persistence, diagnostics, or protocol code.

## Build boundary

The current GTK4 GUI remains Fedora-specific. Native Windows and macOS GUI artifacts should not be published until the portable GUI migration is implemented and physically exercised on those platforms.

CI support for Windows and macOS currently validates the controller package and CLI, not the GTK4 desktop application.
