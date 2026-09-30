# Development

Python 3.13 is the CI baseline. Create and activate a virtual environment (see README), then:

```bash
python -m pip install --upgrade pip
python -m pip install -e ".[desktop]"
python -m unittest discover -s tests -v
python -m betabrite_controller.desktop_launcher --smoke-test
betabrite --version
betabrite --list-ports
python -m compileall -q betabrite_controller scripts tests
```

Core-only installs omit the desktop extra; GUI integration tests are explicitly skipped there and run in desktop CI. Tests use fake transports; no test sends to attached hardware. Smoke tests use temporary configuration and passive discovery.

## Architecture

- desktop.py: Qt widgets and user interaction
- desktop_worker.py: one background serial operation at a time
- desktop_controls.py / desktop_model.py: editor and adapter presentation
- service.py: desktop transmission operation
- controller.py: shared CLI/GUI controller and established alphasignpy packet construction
- connection.py: active probes and transport-error translation
- devices.py: passive discovery and identity matching
- settings.py: validated per-user JSON and atomic replacement
- diagnostics.py: bounded local logging
- platform_integration.py: Linux per-user AppImage shortcut
- scripts/build-native.py: native Nuitka deployment and packaging
- scripts/appimage.py: versioned, checksum-verified AppImage tooling

The legacy GTK application remains a compatibility reference, not a second official product. Do not duplicate protocol code in either GUI. Keep the established serial framing, sign addressing, packet label A and FILL behavior unless new hardware tests justify a change. The pinned alphasignpy 0.1.1 serial handle is used only to set a five-second write timeout; tests cover this dependency boundary.

## Build

Install the desktop extra. Linux compilation also requires a C compiler, matching Python development headers, and patchelf; use your distribution's package manager. On Fedora: python3-devel and patchelf. On Ubuntu: python3-dev, build-essential and patchelf.

```bash
python scripts/build-native.py --dry-run
python scripts/build-native.py
python -m pip install build twine "Pillow==12.3.0"
python scripts/generate-icons.py --check
python -m build
python -m twine check dist/*.whl dist/*.tar.gz
```

Windows installer creation uses Inno Setup 6 as shown in native-desktop.yml. macOS DMGs require hdiutil and are built on a Mac. Native outputs are ignored under dist/native. Do not commit compiler outputs or venvs.

For workflow checking, install actionlint and run actionlint at the repository root. For dependency review, install pip-audit and run python -m pip_audit. Use gitleaks git --redact to scan history. These tools run only during development/builds, not in the application.

Version comes exclusively from betabrite_controller/__init__.py. Setuptools reads it dynamically; About, CLI, native metadata and artifact names consume the same value. The release tag must be v followed by that version.
