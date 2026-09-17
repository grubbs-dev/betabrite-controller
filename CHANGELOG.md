# Changelog

All notable changes to BetaBrite Controller are documented here.

The project uses semantic versioning for public releases.

## [1.1.0] - Unreleased

### Added

- Cross-platform serial-port discovery using pySerial
- Automatic preference for the physically tested PL2303GT adapter (`067b:23a3`)
- Safe fallback when exactly one other USB serial adapter is connected
- `betabrite --list-ports` for inspecting detected serial devices
- Standard Python project metadata and a `betabrite` console entry point
- Core CI coverage on Windows, macOS, and Linux

### Changed

- The controller now uses `auto` as its default port instead of hard-coding `/dev/betabrite`
- Explicit Windows `COM` ports and macOS/Linux device paths can be selected with `--port`
- pySerial is now an explicit project dependency

### Notes

- The controller backend and CLI are cross-platform in this milestone.
- The existing GTK4 GUI and one-click installer remain Linux/Fedora-specific until the portable GUI packaging phase.

## [1.0.0] - 2026-09-17

### Added

- GTK4 desktop controller for Alpha/BetaBrite LED signs
- Command-line controller
- Color, display-mode, speed, flash, wide-text, and special-effect controls
- Automatic sign connection monitoring
- Hardware setup and test-sign workflow
- Fedora installation and uninstallation scripts
- udev configuration for the tested PL2303GT USB serial adapter
- Unit tests for the controller backend
- GitHub CI and automated release packaging
