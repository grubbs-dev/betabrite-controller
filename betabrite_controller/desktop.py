"""Portable PySide6 desktop foundation for BetaBrite Controller."""

from __future__ import annotations

import argparse
import sys

from PySide6 import __version__ as pyside_version
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from . import __app_name__, __author__, __tagline__, __version__
from .connection import probe_connection
from .desktop_model import adapter_options, default_adapter_index
from .devices import AUTO_PORT, forget_port, remember_port
from .presentation import connection_view


DESKTOP_FILE_NAME = "betabrite-controller"


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
    """Verify that PySide6 and the platform-neutral desktop model import."""
    options = adapter_options()
    diagnostic = probe_connection(AUTO_PORT)
    view = connection_view(diagnostic)

    print(f"BetaBrite portable desktop: OK")
    print(f"  core:    {__version__}")
    print(f"  PySide6: {pyside_version}")
    print(f"  state:   {view.state}")
    print(f"  adapters:{len(options)}")
    return 0


class PortableWindow(QMainWindow):
    """First cross-platform shell around the stabilized controller backend."""

    def __init__(self):
        super().__init__()
        self.options = []

        self.setWindowTitle(f"{__app_name__} // Portable")
        self.setMinimumSize(760, 480)

        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(28, 26, 28, 26)
        layout.setSpacing(18)
        self.setCentralWidget(root)

        title = QLabel("BETABRITE // CONTROLLER")
        title_font = QFont()
        title_font.setPointSize(22)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        subtitle = QLabel(__tagline__.upper())
        subtitle.setObjectName("subtitle")
        layout.addWidget(subtitle)

        meta = QLabel(
            f"PORTABLE DESKTOP FOUNDATION  //  CORE {__version__}  //  {__author__}"
        )
        meta.setObjectName("meta")
        layout.addWidget(meta)

        layout.addSpacing(6)

        status_card = QFrame()
        status_card.setObjectName("statusCard")
        status_layout = QVBoxLayout(status_card)
        status_layout.setContentsMargins(18, 16, 18, 16)
        status_layout.setSpacing(8)

        self.status_badge = QLabel("● CHECKING")
        badge_font = QFont()
        badge_font.setPointSize(14)
        badge_font.setBold(True)
        self.status_badge.setFont(badge_font)

        self.status_detail = QLabel("Checking the serial adapter...")
        self.status_detail.setWordWrap(True)

        self.status_meta = QLabel("")
        self.status_meta.setObjectName("meta")

        status_layout.addWidget(self.status_badge)
        status_layout.addWidget(self.status_detail)
        status_layout.addWidget(self.status_meta)
        layout.addWidget(status_card)

        adapter_label = QLabel("SERIAL ADAPTER")
        adapter_label.setObjectName("section")
        layout.addWidget(adapter_label)

        self.adapter_combo = QComboBox()
        self.adapter_combo.setMinimumHeight(38)
        layout.addWidget(self.adapter_combo)

        buttons = QHBoxLayout()
        buttons.setSpacing(10)

        self.refresh_button = QPushButton("CHECK CONNECTION")
        self.refresh_button.clicked.connect(self.check_selected)

        self.remember_button = QPushButton("USE SELECTED ADAPTER")
        self.remember_button.clicked.connect(self.remember_selected)

        self.forget_button = QPushButton("FORGET SAVED ADAPTER")
        self.forget_button.clicked.connect(self.forget_saved)

        buttons.addWidget(self.refresh_button)
        buttons.addWidget(self.remember_button)
        buttons.addWidget(self.forget_button)
        layout.addLayout(buttons)

        note = QLabel(
            "READY verifies that the computer can open the selected serial adapter. "
            "It does not claim the physical sign acknowledged a message."
        )
        note.setWordWrap(True)
        note.setObjectName("meta")
        layout.addWidget(note)

        roadmap = QLabel(
            "Foundation milestone: portable window + real device state. "
            "Message composition and full GTK feature parity come next."
        )
        roadmap.setWordWrap(True)
        roadmap.setObjectName("roadmap")
        layout.addWidget(roadmap)

        layout.addStretch(1)

        self.setStyleSheet(
            """
            QMainWindow, QWidget {
                background: #111318;
                color: #f3f4f6;
            }
            QLabel#subtitle {
                color: #aeb4bf;
                letter-spacing: 1px;
            }
            QLabel#meta {
                color: #8f96a3;
            }
            QLabel#section {
                color: #c4c8d0;
                font-weight: 700;
                letter-spacing: 1px;
            }
            QLabel#roadmap {
                color: #9ba3af;
                padding-top: 6px;
            }
            QFrame#statusCard {
                background: #181b22;
                border: 1px solid #303641;
                border-radius: 12px;
            }
            QComboBox, QPushButton {
                background: #1b1f27;
                color: #f3f4f6;
                border: 1px solid #39404d;
                border-radius: 8px;
                padding: 9px 12px;
            }
            QPushButton:hover {
                background: #252a34;
            }
            QPushButton:disabled {
                color: #686f7a;
                border-color: #2a2e36;
            }
            """
        )

        self.refresh_all()

    def selected_port(self) -> str | None:
        index = self.adapter_combo.currentIndex()
        if index < 0 or index >= len(self.options):
            return None
        return self.options[index].port

    def populate_adapters(self) -> None:
        previous_port = self.selected_port()
        self.options = adapter_options()

        self.adapter_combo.blockSignals(True)
        self.adapter_combo.clear()

        if not self.options:
            self.adapter_combo.addItem("No USB serial adapters detected")
            self.adapter_combo.setEnabled(False)
            self.remember_button.setEnabled(False)
        else:
            for option in self.options:
                self.adapter_combo.addItem(option.label)

            index = default_adapter_index(self.options)
            if previous_port:
                for candidate, option in enumerate(self.options):
                    if option.port == previous_port:
                        index = candidate
                        break

            self.adapter_combo.setCurrentIndex(index)
            self.adapter_combo.setEnabled(True)
            self.remember_button.setEnabled(True)

        self.adapter_combo.blockSignals(False)

    def set_connection_view(self, diagnostic) -> None:
        view = connection_view(diagnostic)
        self.status_badge.setText(view.headline)
        self.status_detail.setText(view.detail)

        pieces = []
        if view.port:
            pieces.append(view.port)
        source = getattr(diagnostic, "source", None)
        if source:
            pieces.append(source)
        self.status_meta.setText("  //  ".join(pieces))

        colors = {
            "online": ("#173c2d", "#63d69b", "#2c7654"),
            "selected": ("#3b3219", "#f0c96a", "#796329"),
            "offline": ("#3d2024", "#ef818b", "#7f353d"),
        }
        background, foreground, border = colors[view.tone]
        self.status_badge.setStyleSheet(
            "QLabel {"
            f"background: {background};"
            f"color: {foreground};"
            f"border: 1px solid {border};"
            "border-radius: 12px;"
            "padding: 8px 12px;"
            "}"
        )

    def refresh_all(self) -> None:
        self.populate_adapters()
        self.set_connection_view(probe_connection(AUTO_PORT))

    def check_selected(self) -> None:
        port = self.selected_port() or AUTO_PORT
        self.set_connection_view(probe_connection(port))

    def remember_selected(self) -> None:
        port = self.selected_port()
        if not port:
            return

        remember_port(port)
        self.refresh_all()

    def forget_saved(self) -> None:
        forget_port()
        self.refresh_all()


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)

    if args.smoke_test:
        return smoke_test()

    app = QApplication(sys.argv if argv is None else [sys.argv[0], *argv])
    app.setApplicationName(__app_name__)
    app.setApplicationDisplayName(__app_name__)
    app.setOrganizationName("Grubbs")
    app.setDesktopFileName(DESKTOP_FILE_NAME)

    window = PortableWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
