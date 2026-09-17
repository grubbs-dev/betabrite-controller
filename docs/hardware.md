# Hardware setup

## Tested configuration

BetaBrite Controller is currently tested with the following combination:

| Component | Tested hardware |
| --- | --- |
| Sign | Adaptive Micro Systems BetaBrite 213C-1, Series B |
| USB serial adapter | DSD TECH SH-RJ12C |
| USB serial chipset | Prolific PL2303GT |
| Linux device | `/dev/betabrite` after the udev rule is installed |
| Serial settings | 9600 baud, 7 data bits, even parity, 1 stop bit |

## Tested RJ12 wiring

For the tested DSD TECH adapter and BetaBrite 213C combination, the BetaBrite-side RJ12 connector is wired as follows:

| Pin | Wire | Function |
| ---: | --- | --- |
| 1 | Yellow | Ground |
| 2 | Empty | — |
| 3 | Red | Adapter TX → Sign RX |
| 4 | Green | Adapter RX ← Sign TX |
| 5 | Empty | — |
| 6 | Empty | — |

Physical order:

```text
YELLOW — EMPTY — RED — GREEN — EMPTY — EMPTY
```

> **Important:** wire colors are not a universal RS-232 standard. This table documents the physically tested DSD TECH SH-RJ12C / PL2303GT and BetaBrite 213C setup. Verify your own adapter pinout before changing wiring.

## Device rule

The packaged udev rule matches the tested Prolific adapter:

```text
Vendor ID:  067b
Product ID: 23a3
```

When matched, Linux creates the stable symlink:

```text
/dev/betabrite
```

The installer also grants the `dialout` group access to the serial device.

## Verify the connection

After installation and any required logout/login, connect the adapter and run:

```bash
ls -l /dev/betabrite
```

Then launch the GUI:

```bash
betabrite-gui
```

The header should report **SIGN ONLINE**. The **Hardware Setup** window can send a known-good `BETABRITE // READY` test message.
