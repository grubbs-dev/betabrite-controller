# Portable desktop application

BetaBrite Controller 1.2 development introduces a portable desktop foundation built with PySide6 / Qt 6.

The existing GTK4 application remains the Fedora reference application while the portable interface reaches feature parity.

## Architecture

The portable desktop must reuse the existing `betabrite_controller` backend rather than reimplementing hardware behavior in the GUI.

Shared backend responsibilities:

- serial discovery
- tested-adapter preference
- persistent adapter identity
- active transport diagnostics
- customer-facing connection states
- Alpha/BetaBrite protocol transmission

Portable desktop responsibilities:

- present device state
- let the user select and remember an adapter
- compose messages and effects
- surface transport errors
- provide native desktop interaction on Windows, macOS, and Linux

`desktop_model.py` intentionally contains toolkit-independent adapter presentation logic so it can be unit tested without a graphical runtime.

`desktop_controls.py` contains toolkit-independent message-draft validation, preset data, and READY-gated transmit-state logic.

`desktop.py` is the PySide6 graphical application. `desktop_launcher.py` keeps the smoke-test path headless-safe for CI.

## Development

Install the desktop extra:

```bash
python -m pip install -e ".[desktop]"
```

Verify the Qt runtime without opening a window:

```bash
betabrite-desktop --smoke-test
```

Launch the portable window:

```bash
betabrite-desktop
```

The portable controller currently provides:

- branded Qt window
- actual serial adapter enumeration
- tested/saved adapter labels
- active connection checking and passive plug/unplug monitoring
- remember/forget adapter controls
- READY-gated physical transmission
- message composition and quick presets
- backend-driven color and display-mode selection
- special effects
- speed 1-5, flash, and wide-text formatting
- the existing READY / NO ADAPTER / permission / busy / failure state model
- explicit language that successful writes do not prove display acknowledgment

The GTK4 controller remains the Fedora reference application while native packaging and target-platform physical hardware validation are completed.

## Cross-platform CI

The desktop extra is smoke-tested on:

- Windows
- macOS
- Linux

These CI checks validate that PySide6 installs and the portable desktop entry point imports and executes against the shared backend.

Physical BetaBrite hardware remains validated on Fedora until the same hardware path is exercised on Windows and macOS.

## Deployment direction

The intended native deployment path is Qt for Python's `pyside6-deploy`, which can build platform-specific executables from the PySide6 application.

Packaging comes after feature parity. The repository should not publish a Windows installer, macOS application bundle, or Linux AppImage until those artifacts have been built and tested on their target platforms.

Target customer artifacts remain:

| Platform | Target |
| --- | --- |
| Windows | native application executable and installer |
| macOS | `.app` distributed through a `.dmg` |
| Linux | portable AppImage, with native packages considered later |
