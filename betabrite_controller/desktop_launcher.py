"""Headless-safe launcher for the portable BetaBrite desktop."""

from __future__ import annotations

import argparse
import os
import tempfile
import logging

from PySide6 import __version__ as pyside_version

from . import __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="betabrite-desktop",
        description="Portable Qt desktop controller for BetaBrite signs.",
    )
    parser.add_argument(
        "--smoke-test",
        action="store_true",
        help="Verify the portable desktop runtime without opening a window",
    )
    parser.add_argument("--version", action="version", version=__version__)
    return parser


def smoke_test() -> int:
    # Exercise the actual GUI and plugins without opening any serial ports or
    # modifying user preferences. Compiled artifacts follow this same path.
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    from PySide6.QtGui import QIcon
    from .desktop import PortableWindow
    from .branding import application_icon_path
    from .settings import AppSettings, save_settings, load_settings
    previous = os.environ.get("BETABRITE_CONFIG_DIR")
    with tempfile.TemporaryDirectory(prefix="betabrite-smoke-") as directory:
        os.environ["BETABRITE_CONFIG_DIR"] = directory
        try:
            app = QApplication.instance() or QApplication([])
            assert not QIcon(str(application_icon_path())).isNull(), "Missing application icon"
            assert (application_icon_path().parent / "licenses" / "LGPL-3.0.txt").is_file(), "Missing license resources"
            save_settings(AppSettings())
            assert load_settings() == AppSettings()
            window = PortableWindow(passive=True)
            window.show()
            app.processEvents()
            window.close()
            app.processEvents()
            print(f"BetaBrite Controller {__version__}: GUI, resources, settings and discovery OK (Qt {pyside_version})")
        finally:
            if previous is None:
                os.environ.pop("BETABRITE_CONFIG_DIR", None)
            else:
                os.environ["BETABRITE_CONFIG_DIR"] = previous
    return 0


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)

    if args.smoke_test:
        return smoke_test()

    from .desktop import main as desktop_main

    from .diagnostics import configure_logging
    configure_logging()
    try:
        return desktop_main([] if argv is not None else None)
    except Exception:
        logging.getLogger(__name__).exception("Application startup failed")
        from PySide6.QtWidgets import QApplication, QMessageBox
        app = QApplication.instance() or QApplication([])
        QMessageBox.critical(None, "BetaBrite Controller", "The application could not start. See the application log in your configuration folder.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
