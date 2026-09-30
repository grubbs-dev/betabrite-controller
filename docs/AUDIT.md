# Release audit

Initial branch: chore/v1.2.0-release-prep, HEAD 424373a. Existing tags: v1.0.0 and v1.1.0. Application and pyproject independently said 1.2.0. Existing local changes to betabrite-gui and its untracked backup were preserved.

## Already implemented

- Shared alphasignpy controller for Qt, legacy GTK and CLI, with tested 9600/7E1/DTR-off behavior.
- USB discovery and VID/PID/serial identity matching; active transport probes and friendly common errors.
- Qt editor for existing colors/modes/effects/speed/flash/wide controls and original icon assets.
- Native Nuitka builds, Windows Inno installer, macOS DMG, Linux portable binary/tar package.
- Optional Windows/macOS signing hooks and tagged-release orchestration.
- 63 passing baseline tests, hardware wiring documentation and prior release history.

## Release gaps found and addressed

- Serial sends blocked the GUI and used processEvents; moved to a single background operation with duplicate-send protection and a bounded write timeout.
- Smoke tests only imported PySide6; now construct/render the real Qt window and check bundled resources and isolated configuration.
- Settings stored only one preferred adapter; added named signs, editor state, saved messages and recent successful transmissions.
- Shared temporary settings filename and weak malformed-field handling; added unique private temporary files, atomic replacement and validation.
- A missing remembered adapter could redirect automatic selection; automatic selection now refuses that fallback.
- USB-only GUI lacked a manual port workflow; added explicit port entry and saved-sign reconnect behavior.
- No About/logging/license; added diagnostics, rotating logs, MIT license and dependency notices.
- Linux required shell scripts for menu installation; added AppImage and a GUI per-user install action.
- Duplicated version metadata; setuptools now reads the application's authoritative version.
- Release publishing lacked GH_REPO context without checkout and used broad write permissions; fixed repository targeting and limited write access to the publishing job.
- Installer/DMG checks did not exercise installation/mounting; added native CI gates and reduced public downloads to one per OS plus checksums.
- Source packaging deleted the entire dist directory; it now preserves unrelated build outputs and uses an isolated temporary staging directory.
- Documentation led with developer/legacy workflows and overstated validation; replaced with user installation/use guides and explicit release evidence.

## Preserved intentionally

The GTK application and Fedora system installer are retained as historical compatibility/reference paths, especially because the GTK file contains user work. They are not the official cross-platform desktop distribution. The existing protocol packet/address/label/position behavior is preserved and covered by a golden byte fixture. No new alignment, memory-management or clear-sign protocol command was invented.

The old root-owned build output blocked clean package installation; it was preserved under ignored .prior-build. The user's GTK backup remains present and is ignored. No tracked native executables or credentials were found. Generated build outputs remain ignored.

See RELEASE_VALIDATION.md for executed gates and remaining external validation; implementation is not evidence of hardware or cross-platform success.
