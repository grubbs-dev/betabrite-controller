"""Command-line interface for BetaBrite Controller."""

from __future__ import annotations

import argparse
import sys

from . import __author__, __version__
from .controller import (
    BetaBriteController,
    COLORS,
    DEFAULT_PORT,
    MODES,
    SPECIALS,
)
from .devices import list_serial_devices


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="betabrite",
        description="Control an Alpha/BetaBrite LED display.",
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__} // Created by {__author__}",
    )
    parser.add_argument("message", nargs="*", help="Message to display")
    parser.add_argument(
        "-c",
        "--color",
        choices=COLORS,
        default="auto",
        help="Text color (default: auto)",
    )
    parser.add_argument(
        "-m",
        "--mode",
        choices=MODES,
        default="rotate",
        help="Display mode (default: rotate)",
    )
    parser.add_argument(
        "--special",
        choices=SPECIALS,
        help="Use a BetaBrite special animation",
    )
    parser.add_argument(
        "--flash",
        action="store_true",
        help="Flash the message text",
    )
    parser.add_argument(
        "--wide",
        action="store_true",
        help="Use wide characters",
    )
    parser.add_argument(
        "--speed",
        type=int,
        choices=range(1, 6),
        metavar="1-5",
        help="Display speed: 1=slowest, 5=fastest",
    )
    parser.add_argument(
        "--port",
        default=DEFAULT_PORT,
        help=(
            "Serial port. Use 'auto' for USB discovery "
            "(default: auto). Examples: COM4, /dev/ttyUSB0, "
            "/dev/cu.usbserial-XXXX"
        ),
    )
    parser.add_argument(
        "--list-ports",
        action="store_true",
        help="List detected serial ports",
    )
    parser.add_argument(
        "--list-colors",
        action="store_true",
        help="List available colors",
    )
    parser.add_argument(
        "--list-modes",
        action="store_true",
        help="List available display modes",
    )
    parser.add_argument(
        "--list-special",
        action="store_true",
        help="List special animations",
    )
    return parser


def print_items(title, items):
    print(f"\n{title}:")
    for name in items:
        print(f"  {name}")


def print_ports() -> None:
    devices = list_serial_devices()
    print("\nDetected serial ports:")

    if not devices:
        print("  none")
        return

    for device in devices:
        marker = "*" if device.preferred else " "
        usb_id = f" [{device.usb_id}]" if device.usb_id else ""
        print(
            f" {marker} {device.device:<18} "
            f"{device.display_name}{usb_id}"
        )

    print("\n* tested BetaBrite USB adapter")


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.list_ports:
        print_ports()
        return 0

    if args.list_colors:
        print_items("Available colors", COLORS)
        return 0

    if args.list_modes:
        print_items("Available modes", MODES)
        return 0

    if args.list_special:
        print_items("Available special animations", SPECIALS)
        return 0

    if not args.message and not args.special:
        parser.print_help()
        return 1

    message = " ".join(args.message)
    controller = BetaBriteController(port=args.port)

    try:
        controller.send(
            message=message,
            color_name=args.color,
            mode_name=args.mode,
            special_name=args.special,
            speed_level=args.speed,
            flash=args.flash,
            wide=args.wide,
        )
    except Exception as exc:
        print(f"BetaBrite error: {exc}", file=sys.stderr)
        return 1

    description = message if message else args.special
    port = controller.last_port or controller.resolved_port or args.port
    print(f'BetaBrite [{port}]: "{description}"')
    return 0
