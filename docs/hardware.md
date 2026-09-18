# Hardware setup

## Tested configuration

BetaBrite Controller is physically tested with the following combination:

| Component | Tested hardware |
| --- | --- |
| Sign | Adaptive Micro Systems BetaBrite 213C-1, Series B |
| USB serial adapter | DSD TECH SH-RJ12C |
| USB serial chipset | Prolific PL2303GT |
| USB vendor/product ID | `067b:23a3` |
| Serial settings | 9600 baud, 7 data bits, even parity, 1 stop bit |

The controller now recognizes serial devices by the operating system's normal port name. Typical examples are:

| Platform | Example |
| --- | --- |
| Windows | `COM4` |
| macOS | `/dev/cu.usbserial-XXXX` |
| Linux | `/dev/ttyUSB0` or `/dev/betabrite` |

The tested `067b:23a3` adapter is preferred automatically when present.

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

## Detect the adapter

With the controller core installed, run:

```bash
betabrite --list-ports
```

The tested adapter is marked as `tested`.

If multiple USB serial adapters are connected, select the BetaBrite adapter explicitly:

```bash
betabrite "TEST" --port COM4
```

Replace `COM4` with the device shown on your operating system.

## Linux udev enhancement

The Fedora installer also installs a udev rule for the tested Prolific adapter. When matched, Linux creates:

```text
/dev/betabrite
```

and configures `dialout` access.

That stable symlink is convenient on Linux, but it is no longer required by the controller core because automatic serial discovery is platform-independent.
