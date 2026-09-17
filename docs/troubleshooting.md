# Troubleshooting

## `SIGN OFFLINE` or `/dev/betabrite` is missing

Confirm the USB serial adapter is connected:

```bash
lsusb
```

For the tested PL2303GT adapter, look for vendor/product IDs `067b:23a3`.

Then check for the stable device symlink:

```bash
ls -l /dev/betabrite
```

If it is missing, reload udev rules:

```bash
sudo udevadm control --reload-rules
sudo udevadm trigger
```

Unplug and reconnect the adapter, then check again.

## Permission denied opening the serial device

Check your group membership:

```bash
groups
```

The user running BetaBrite Controller should be a member of `dialout`.

If the installer just added that membership, log out of Fedora and log back in once. Starting a new terminal alone does not always refresh the login session's groups.

## Confirm the installed udev rule

```bash
cat /etc/udev/rules.d/99-betabrite.rules
```

The tested adapter rule should contain vendor ID `067b` and product ID `23a3`.

## Test from the command line

Verify the CLI is installed:

```bash
betabrite --version
```

Then try a simple message:

```bash
betabrite "TEST" --color green --mode hold
```

If the GUI and CLI both fail in the same way, the problem is usually below the UI layer: device detection, permissions, wiring, or serial hardware.

## GUI does not start

Run it from a terminal so Python/GTK errors are visible:

```bash
betabrite-gui
```

Check the required Fedora packages:

```bash
rpm -q python3 python3-pip python3-gobject gtk4
```

Re-running the installer is safe for the application files; it recreates the isolated runtime and verifies the backend at the end.

## Tests

From a repository checkout:

```bash
bash test.sh
```

The unit tests do not require a physical sign because they use a nonexistent test device path for connection checks.
