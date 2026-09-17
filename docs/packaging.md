# Packaging and distribution

BetaBrite Controller now has three packaging layers:

1. A standard Python package for the cross-platform controller core and CLI.
2. The established Fedora GTK4 installer retained for the v1.1 Linux path.
3. Native development builds of the portable PySide6 / Qt controller for Windows, macOS, and Linux.

The Python package remains useful for development, automation, and advanced CLI workflows. The native desktop path is intended to become the normal-user distribution path for the 1.2 release.

## Current release artifacts

The frozen v1.1 release path publishes:

- `betabrite-controller-vX.Y.Z.tar.gz` — complete source/Fedora installer archive
- `betabrite-controller-vX.Y.Z.zip` — complete source/Fedora installer archive
- `betabrite_controller-X.Y.Z-py3-none-any.whl` — standard Python wheel
- `betabrite_controller-X.Y.Z.tar.gz` — standard Python source distribution
- `SHA256SUMS` — checksums for release artifacts

The v1.1 tag and release are not mutated by 1.2 development.

## Native desktop development builds

The portable Qt application is packaged with Qt for Python's `pyside6-deploy`, which wraps Nuitka and creates a platform-native executable or app bundle on the target operating system.

Current Phase 8 build outputs:

| Platform | Native build output | Distribution wrapper |
| --- | --- | --- |
| Windows x86_64 | `BetaBriteController.exe` | portable `.exe`, `.zip`, unsigned Inno Setup `.exe` |
| macOS runner architecture | `BetaBriteController.app` | `.zip`, unsigned `.dmg` |
| Linux x86_64 | `BetaBriteController.bin` | portable `.bin`, `.tar.gz` |

Every native build also emits a platform-specific SHA-256 manifest.

The top-level `betabrite_desktop.py` file is the deployment entry point. It delegates to the headless-safe desktop launcher so a compiled application can still run `--smoke-test` without opening a GUI.

`scripts/build-native.py` is the authoritative native build wrapper. It:

- detects the current platform and architecture
- invokes `pyside6-deploy`
- smoke-tests the compiled output
- renames artifacts consistently
- packages platform-friendly archives
- creates SHA-256 manifests

## Native build CI

`.github/workflows/native-desktop.yml` builds independently on:

- `ubuntu-latest`
- `windows-latest`
- `macos-latest`

The workflow runs on pull requests, pushes to `main`, and manual dispatch. Each runner builds its own native artifact rather than cross-compiling another platform.

Windows CI additionally compiles an Inno Setup installer around the portable executable.

Native build CI proves that the application can be compiled and that the bundled executable completes the headless smoke path. It does not prove physical BetaBrite serial hardware behavior on Windows or macOS.

## Signing and release gates

Development artifacts are intentionally unsigned.

Before a 1.2 native desktop release is treated as a normal end-user release:

- Windows executable and installer signing should be configured with an appropriate code-signing identity.
- macOS application signing and Apple notarization should be configured before public distribution.
- Physical BetaBrite hardware validation should be performed on Windows and macOS.
- Linux desktop integration and an AppImage can be added after the portable binary path is proven.
- Native artifacts should then be promoted into the tagged GitHub Release workflow.

These gates are kept separate from the build itself so missing signing credentials do not block ordinary development and CI.

## Fedora installer

`install.sh` remains the established Fedora GTK4 installer. It creates an isolated virtual environment with access to Fedora's system GTK4 bindings and installs the project through `pyproject.toml`.

Application launchers:

- `/usr/local/bin/betabrite`
- `/usr/local/bin/betabrite-gui`

Application files:

- `/opt/betabrite-controller`

Per-user settings are stored separately under the platform configuration directory and survive normal uninstall.

The Fedora installer is retained during the 1.2 migration and should not be removed until the portable Qt Linux distribution path is fully validated.
