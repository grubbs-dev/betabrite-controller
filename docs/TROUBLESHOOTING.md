# Troubleshooting

## No sign or adapter detected

Power on the sign, reconnect the USB cable, and click **Refresh / Reconnect**. Try a direct USB port instead of a hub. Discovery lists USB adapters, not the sign itself. Use **Manual port…** for non-USB serial ports. A remembered adapter that is absent deliberately blocks automatic fallback; select another port explicitly or forget the saved adapter.

## Windows COM ports and Prolific drivers

Check Device Manager → Ports (COM & LPT). Select the COM number shown there. COM numbers can change after replugging; saving the adapter identity helps follow it. Close terminal emulators and other sign software if the port is busy.

If no port appears, or the adapter has a warning symbol, use Windows Update or the adapter manufacturer's driver for that chipset. PL2303 variants have different driver support; do not install random third-party driver bundles. The historically tested adapter is PL2303GT, not every product sold as PL2303.

## macOS ports

Check System Information → USB for the adapter. Select its /dev/cu.* port, usually /dev/cu.usbserial-…. Install a manufacturer-supported driver only if required. Allow any driver/system extension using Apple's normal security controls. Unplug, reconnect, refresh and select again if the name changes.

## Linux serial permissions

If opening /dev/ttyUSB* or /dev/ttyACM* is denied, your account needs access to that serial device. Use your distribution's Users/Groups administration tool or ask an administrator to add you to the group owning the device: commonly **dialout** on Debian, Ubuntu and Fedora, or **uucp** on Arch. Log out completely and back in after changing group membership, then reconnect the cable.

For administrators using a terminal, inspect the actual device first:

```bash
ls -l /dev/ttyUSB0
id
# If the device's group is dialout:
sudo usermod -aG dialout "$USER"
# If the device's group is uucp, use uucp instead.
```

Do not use chmod 777, world-writable udev rules, or run the desktop application as root. Group access is an OS administration step; the app deliberately does not weaken device permissions.

## READY but nothing displays

READY only confirms that the adapter can open. Check sign power, cable wiring, the selected port, and the message/effect. The established protocol uses 9600/7E1 with DTR off. Start with a short plain ASCII message and Rotate mode. Review [the tested wiring](hardware.md); wire colors are not universal. Other sign models may need hardware-specific configuration that this release does not expose.

## Unplugging or busy ports

Only one sign operation runs at a time. Close other serial programs. Replug the cable and click Refresh / Reconnect. When several similar adapters lack unique serial numbers, select the intended one explicitly and save it again.

## AppImage does not launch

Enable execution in file Properties and ensure the download is on a filesystem that permits executing programs. If the runtime reports a FUSE problem, install your distribution's supported FUSE package through its software manager. Ubuntu 24.04 commonly provides libfuse2t64.

Advanced diagnostic fallback:

```bash
APPIMAGE_EXTRACT_AND_RUN=1 ./BetaBrite-Controller-1.4.1-Linux-x86_64.AppImage --smoke-test
```

An older distribution may also lack the system libraries required by Qt or the compiler runtime. CI's baseline is Ubuntu 24.04; local Fedora builds do not prove compatibility with that baseline.

## Configuration or logs

Open **About / Diagnostics** for the log location. Configuration errors fall back to defaults rather than stopping startup. To reset preferences, quit the app and rename settings.json in the [documented settings directory](USER_GUIDE.md). Keep a copy if you need to recover saved messages.

Log files contain local technical errors and may include port names or paths; review them before sharing. To report a bug, include app version, OS, adapter/sign models, steps, expected behavior, actual behavior, and a relevant log excerpt at [GitHub Issues](https://github.com/grubbs-dev/betabrite-controller/issues). Never post credentials or unrelated personal information.
