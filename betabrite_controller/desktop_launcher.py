"""Headless-safe launcher for the portable BetaBrite desktop."""

from __future__ import annotations

import argparse

from PySide6 import __version__ as pyside_version

from . import __version__
from .connection import probe_connection
from .desktop_model import adapter_options
from .devices import AUTO_PORT
from .presentation import connection_view


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="betabrite-desktop",
        description="Portable Qt desktop foundation for BetaBrite Controller.",
    )
    parser.add_argument(
        "--smoke-test",
        action="store_true",
        help="Verify the portable desktop runtime without opening a window",
    )
    return parser


def smoke_test() -> int:
    options = adapter_options()
    diagnostic = probe_connection(AUTO_PORT)
    view = connection_view(diagnostic)

    print("BetaBrite portable desktop: OK")
    print(f"  core:    {__version__}")
    print(f"  PySide6: {pyside_version}")
    print(f"  state:   {view.state}")
    print(f"  adapters:{len(options)}")
    return 0


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)

    if args.smoke_test:
        return smoke_test()

    from .desktop import main as desktop_main

    return desktop_main([] if argv is not None else None)


if __name__ == "__main__":
    raise SystemExit(main())
