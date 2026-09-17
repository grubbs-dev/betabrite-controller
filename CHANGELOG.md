# Changelog

All notable changes to BetaBrite Controller are documented here.

The project uses semantic versioning for public releases.

## [1.2.0] - Unreleased

### Added

- Portable PySide6 / Qt 6 desktop foundation for Windows, macOS, and Linux
- Full portable Qt message composer with colors, display modes, special effects, speed, flash, wide text, and quick presets
- READY-gated physical transmission from the portable Qt application through the shared controller backend
- Passive adapter monitoring that preserves READY only after a successful active probe on the same port
- Toolkit-independent message-draft validation and transmit-state tests
- `betabrite-desktop` application entry point
- Cross-platform adapter selection, remember/forget controls, and active connection status in the portable window
- Toolkit-independent desktop adapter presentation model and unit tests
- Portable desktop smoke-test CI on Windows, macOS, and Linux
- Portable GUI architecture and deployment documentation

### Changed

- Development package version advanced to `1.2.0.dev0`
- GitHub Actions checkout/setup-python actions moved to their current Node 24 generation
- Portable Qt controls now source color, mode, special-effect, and transmission behavior from the shared backend

### Notes

- The GTK4 desktop application remains the Fedora reference UI during the portable GUI migration.
- Portable desktop CI validates the application runtime, but physical Windows/macOS BetaBrite hardware validation is still pending.

## [1.1.0] - 2026-09-17

### Added

- Cross-platform serial-port discovery using pySerial
- Automatic preference for the physically tested PL2303GT adapter (`067b:23a3`)
- Safe fallback when exactly one other USB serial adapter is connected
- `betabrite --list-ports` for inspecting detected serial devices
- Standard Python project metadata and a `betabrite` console entry point
- Core CI coverage on Windows, macOS, and Linux
- Persistent per-user adapter selection using USB VID/PID and serial identity
- `--status`, `--remember-port`, `--forget-port`, and `--list-all-ports`
- Active serial transport verification with `--check-connection`
- Stable customer-facing states for missing, busy, permission-denied, and failed serial ports
- Shared connection-state presentation helpers for desktop interfaces
- GTK4 Hardware Setup controls for remembering and forgetting the preferred adapter
- Standard wheel and Python source-distribution validation in CI
- Release-time package-version/tag validation
- Packaging and distribution documentation for current and future artifacts

### Changed

- The controller now uses `auto` as its default port instead of hard-coding `/dev/betabrite`
- Explicit Windows `COM` ports and macOS/Linux device paths can be selected with `--port`
- pySerial is now an explicit project dependency
- The GTK4 GUI now displays real backend connection states instead of a simple online/offline boolean
- The GUI displays the resolved serial port instead of the literal `auto` selector
- The Fedora installer now installs the controller through `pyproject.toml` instead of manually copying the backend package
- Normal uninstall preserves per-user device settings; `--purge-settings` removes them explicitly
- Tagged releases now include standard Python wheel/source-distribution artifacts in addition to complete source archives

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
