# Install BetaBrite Controller

Download the installer for your OS from [Releases](https://github.com/grubbs-dev/betabrite-controller/releases). No Python or terminal is needed for normal installation.

## Windows 10/11 x64

Open the file ending in `-setup.exe`. Installation is per-user and creates a Start Menu shortcut; an optional desktop shortcut is offered. Uninstall through Windows Settings → Apps. Preferences remain in your user profile.

Unsigned builds can trigger SmartScreen. Verify the repository and release checksum before deciding whether to run one. A release filename alone is not proof of signing: check the executable's Digital Signatures tab. Do not disable Windows security globally.

## macOS Apple Silicon

Open the ARM64 DMG and drag **BetaBrite Controller.app** onto **Applications**. Eject the disk image and launch from Applications or Launchpad.

Unsigned/ad-hoc builds are not notarized and may be blocked by Gatekeeper. Only after verifying the download, use the OS-provided approval in System Settings → Privacy & Security if available. Managed computers may prohibit this; use a signed, notarized release in that case. Do not disable Gatekeeper globally.

Intel Macs are not currently included in the release matrix.

## Linux x86_64

Download the AppImage to a permanent folder. In your file manager's Properties/Permissions, enable execution as a program, then double-click it. If your file manager asks, choose Run.

Inside the application, choose **Install in application menu** to copy it into your per-user application directory and create a normal launcher. No administrator rights are required. Installing a newer AppImage using this button replaces that per-user copy; quit other running copies first.

The menu installation stores files under `~/.local/share` (or `XDG_DATA_HOME`): `betabrite-controller/BetaBrite-Controller.AppImage`, `applications/dev.grubbs.BetaBriteController.desktop`, and `icons/hicolor/256x256/apps/dev.grubbs.BetaBriteController.png`. Remove those files in the file manager to uninstall. Preferences are retained.

CI builds on Ubuntu 24.04. Older distributions may lack required glibc or graphical system libraries. AppImage runtime/FUSE failures and serial permissions are covered in [Troubleshooting](TROUBLESHOOTING.md). Desktop launch and hardware behavior still need the release checklist's platform checks.

## USB drivers

Plug in the supported cable and let the OS install its driver. If a Prolific adapter is missing, obtain a driver appropriate to its exact chipset from the manufacturer or Windows Update. The app does not bundle or install proprietary USB drivers.
