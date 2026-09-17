"""Command-line interface for BetaBrite Controller."""

from __future__ import annotations

import argparse
import sys

from . import __author__, __version__
from .connection import BetaBriteTransportError
from .controller import (
    BetaBriteController,
    COLORS,
    DEFAULT_PORT,
    MODES,
    SPECIALS,
)
from .devices import (
    device_matches_preference,
    diagnose_device,
    forget_port,
    list_candidate_devices,
    list_serial_devices,
    remember_port,
)
from .settings import load_settings, settings_path


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
            "Serial port. Use 'auto' for discovery (default). "
            "Examples: COM4, /dev/ttyUSB0, /dev/cu.usbserial-XXXX"
        ),
    )
    parser.add_argument(
        "--list-ports",
        action="store_true",
        help="List detected USB serial adapters",
    )
    parser.add_argument(
        "--list-all-ports",
        action="store_true",
        help="List every serial port, including system/legacy ports",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Show passive adapter selection and saved-device diagnostics",
    )
    parser.add_argument(
        "--check-connection",
        action="store_true",
        help="Actively verify that the selected serial port can be opened",
    )
    parser.add_argument(
        "--remember-port",
        nargs="?",
        const="auto",
        metavar="PORT",
        help="Remember PORT for future automatic selection; omit PORT to use auto",
    )
    parser.add_argument(
        "--forget-port",
        action="store_true",
        help="Forget the remembered serial adapter",
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


def print_ports(*, include_system: bool = False) -> None:
    devices = list_serial_devices() if include_system else list_candidate_devices()
    title = "Detected serial ports" if include_system else "Detected USB serial adapters"
    print(f"\n{title}:")

    if not devices:
        print("  none")
        return

    preference = load_settings().preferred_device

    for device in devices:
        markers = []
        if device.preferred:
            markers.append("tested")
        if preference is not None:
            if device_matches_preference(device, preference):
                markers.append("remembered")

        usb_id = f" [{device.usb_id}]" if device.usb_id else ""
        marker_text = f" ({', '.join(markers)})" if markers else ""
        print(
            f"  {device.device:<18} "
            f"{device.display_name}{usb_id}{marker_text}"
        )


def print_status(port: str) -> int:
    settings = load_settings()
    preference = settings.preferred_device
    diagnostic = diagnose_device(port, settings=settings)

    print("\nBetaBrite device status:")
    print(f"  state:      {diagnostic.state.upper()}")
    print(f"  settings:   {settings_path()}")

    if preference is None:
        print("  remembered: none")
    else:
        identity = preference.usb_id or preference.device or "unknown"
        serial = f" / serial {preference.serial_number}" if preference.serial_number else ""
        print(f"  remembered: {preference.label} [{identity}]{serial}")

    if diagnostic.port:
        print(f"  port:       {diagnostic.port}")
    if diagnostic.source:
        print(f"  selected:   {diagnostic.source}")
    print(f"  detail:     {diagnostic.message}")
    return 0 if diagnostic.ready else 1


def print_connection_check(port: str) -> int:
    controller = BetaBriteController(port=port)
    diagnostic = controller.check_connection()

    print("\nBetaBrite connection check:")
    print(f"  state:      {diagnostic.state.upper()}")
    if diagnostic.port:
        print(f"  port:       {diagnostic.port}")
    if diagnostic.source:
        print(f"  selected:   {diagnostic.source}")
    print(f"  detail:     {diagnostic.message}")
    print(
        "  note:       This verifies the computer-to-adapter serial path. "
        "It does not prove the display acknowledged a message."
    )
    return 0 if diagnostic.ready else 2


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.list_ports:
        print_ports()
        return 0

    if args.list_all_ports:
        print_ports(include_system=True)
        return 0

    if args.status:
        return print_status(args.port)

    if args.check_connection:
        return print_connection_check(args.port)

    if args.remember_port is not None:
        try:
            selection = remember_port(args.remember_port)
        except Exception as exc:
            print(f"BetaBrite error: {exc}", file=sys.stderr)
            return 1
        device_name = (
            selection.device.display_name
            if selection.device is not None
            else selection.port
        )
        print(f"Remembered {device_name} on {selection.port}.")
        return 0

    if args.forget_port:
        forget_port()
        print("Forgot the remembered BetaBrite serial adapter.")
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
    except BetaBriteTransportError as exc:
        label = exc.state.replace("-", " ").upper()
        print(f"BetaBrite {label}: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"BetaBrite error: {exc}", file=sys.stderr)
        return 1

    description = message if message else args.special
    port = controller.last_port or controller.resolved_port or args.port
    print(f'BetaBrite [{port}]: "{description}"')
    return 0
