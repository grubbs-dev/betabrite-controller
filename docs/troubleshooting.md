# Troubleshooting

## Start with serial discovery

Run:

```bash
betabrite --list-ports
```

For the physically tested DSD TECH / PL2303GT adapter, look for USB ID:

```text
067b:23a3
```

The tested adapter is marked with `*`.

If no ports are listed, the operating system is not currently exposing the USB adapter as a serial device. Check the cable, USB connection, and any required chipset driver.

## Multiple USB serial adapters are connected

Automatic mode refuses to guess when several possible USB serial adapters are present.

List the ports:

```bash
betabrite --list-ports
```

Then select the BetaBrite adapter explicitly.

Windows:

```bash
betabrite "TEST" --port COM4
```

macOS:

```bash
betabrite "TEST" --port /dev/cu.usbserial-XXXX
```

Linux:

```bash
betabrite "TEST" --port /dev/ttyUSB0
```

## Windows

If the adapter does not appear in `betabrite --list-ports`, open **Device Manager** and look under **Ports (COM & LPT)**.

The tested hardware uses a Prolific PL2303GT chipset. The exact COM number is assigned by Windows and may differ between computers or USB ports.

## macOS

Check the controller's detected list first:

```bash
betabrite --list-ports
```

macOS serial devices commonly appear as `/dev/cu.*`. If a USB serial adapter is missing completely, verify that macOS recognizes the adapter and that any required vendor driver is installed.

## Linux / Fedora

The cross-platform controller can use the normal `/dev/ttyUSB*` device directly. The Fedora installer additionally creates the stable `/dev/betabrite` symlink for the tested adapter.

Check USB detection:

```bash
lsusb
```

Check the stable symlink:

```bash
ls -l /dev/betabrite
```

If needed, reload udev rules:

```bash
sudo udevadm control --reload-rules
sudo udevadm trigger
```

### Permission denied

Check your group membership:

```bash
groups
```

The user running BetaBrite Controller should normally be a member of `dialout` on Fedora.

If the installer just added that membership, log out of Fedora and log back in once.

## Test from the command line

Verify the CLI:

```bash
betabrite --version
betabrite --list-ports
```

Then send a known-simple message:

```bash
betabrite "TEST" --color green --mode hold
```

If necessary, specify the detected serial port explicitly with `--port`.

## Fedora GUI does not start

The current GTK4 GUI is still a Fedora/Linux component.

Run it from a terminal so GTK/Python errors are visible:

```bash
betabrite-gui
```

Check the required packages:

```bash
rpm -q python3 python3-pip python3-gobject gtk4
```

## Tests

From a repository checkout on any supported core platform:

```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

The discovery tests use mocked serial-port metadata and do not require a physical sign.
