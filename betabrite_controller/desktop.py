"""Portable PySide6 desktop controller for BetaBrite signs."""

from __future__ import annotations

import argparse
import sys

from PySide6 import __version__ as pyside_version
from PySide6.QtCore import QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from . import __app_name__, __author__, __tagline__, __version__
from .connection import BetaBriteTransportError, ConnectionDiagnostic, probe_connection
from .controller import BetaBriteController, COLORS, MODES, SPECIALS
from .desktop_controls import PRESETS, MessageDraft, can_transmit, display_name
from .desktop_model import adapter_options, default_adapter_index
from .devices import AUTO_PORT, diagnose_device, forget_port, remember_port
from .presentation import connection_view


DESKTOP_FILE_NAME = "betabrite-controller"


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
    return parser


def smoke_test() -> int:
    """Verify that PySide6 and the platform-neutral desktop model import."""
    options = adapter_options()
    diagnostic = probe_connection(AUTO_PORT)
    view = connection_view(diagnostic)

    print("BetaBrite portable desktop: OK")
    print(f"  core:    {__version__}")
    print(f"  PySide6: {pyside_version}")
    print(f"  state:   {view.state}")
    print(f"  adapters:{len(options)}")
    return 0


def section_label(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("section")
    return label


class PortableWindow(QMainWindow):
    """Cross-platform controller UI backed by the stabilized controller core."""

    def __init__(self):
        super().__init__()
        self.options = []
        self.last_ready_port: str | None = None
        self.connection_ready = False
        self.selected_color = "auto"
        self.selected_speed = 3
        self.color_buttons: dict[str, QPushButton] = {}
        self.speed_buttons: dict[int, QPushButton] = {}

        self.setWindowTitle(f"{__app_name__} // {__author__}")
        self.setMinimumSize(900, 760)
        self.resize(980, 900)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.setCentralWidget(scroll)

        root = QWidget()
        scroll.setWidget(root)

        layout = QVBoxLayout(root)
        layout.setContentsMargins(28, 26, 28, 26)
        layout.setSpacing(16)

        header = QHBoxLayout()
        header.setSpacing(18)

        header_text = QVBoxLayout()
        header_text.setSpacing(3)

        title = QLabel("BETABRITE // CONTROLLER")
        title_font = QFont()
        title_font.setPointSize(22)
        title_font.setBold(True)
        title.setFont(title_font)

        subtitle = QLabel(__tagline__.upper())
        subtitle.setObjectName("subtitle")

        meta = QLabel(f"Created by {__author__}  //  v{__version__}")
        meta.setObjectName("meta")

        header_text.addWidget(title)
        header_text.addWidget(subtitle)
        header_text.addWidget(meta)

        self.status_badge = QLabel("● CHECKING")
        badge_font = QFont()
        badge_font.setPointSize(13)
        badge_font.setBold(True)
        self.status_badge.setFont(badge_font)

        header.addLayout(header_text, 1)
        header.addWidget(self.status_badge)
        layout.addLayout(header)

        self.status_detail = QLabel("Checking the serial adapter...")
        self.status_detail.setWordWrap(True)
        self.status_detail.setObjectName("meta")
        layout.addWidget(self.status_detail)

        self.status_meta = QLabel("")
        self.status_meta.setObjectName("meta")
        layout.addWidget(self.status_meta)

        layout.addWidget(section_label("SERIAL ADAPTER"))

        self.adapter_combo = QComboBox()
        self.adapter_combo.setMinimumHeight(40)
        self.adapter_combo.currentIndexChanged.connect(self.on_adapter_changed)
        layout.addWidget(self.adapter_combo)

        adapter_actions = QHBoxLayout()
        adapter_actions.setSpacing(10)

        self.refresh_button = QPushButton("CHECK CONNECTION")
        self.refresh_button.clicked.connect(lambda: self.refresh_connection(active=True))

        self.remember_button = QPushButton("USE SELECTED ADAPTER")
        self.remember_button.clicked.connect(self.remember_selected)

        self.forget_button = QPushButton("FORGET SAVED ADAPTER")
        self.forget_button.clicked.connect(self.forget_saved)

        adapter_actions.addWidget(self.refresh_button)
        adapter_actions.addWidget(self.remember_button)
        adapter_actions.addWidget(self.forget_button)
        layout.addLayout(adapter_actions)

        layout.addWidget(section_label("MESSAGE"))

        self.message = QLineEdit("BRIEF IN PROGRESS")
        self.message.setPlaceholderText("Type a message for the sign...")
        self.message.setMinimumHeight(48)
        self.message.setObjectName("messageEntry")
        self.message.returnPressed.connect(self.send_current)
        self.message.textChanged.connect(self.update_send_enabled)
        layout.addWidget(self.message)

        layout.addWidget(section_label("COLOR"))

        color_grid = QGridLayout()
        color_grid.setHorizontalSpacing(7)
        color_grid.setVerticalSpacing(7)

        self.color_group = QButtonGroup(self)
        self.color_group.setExclusive(True)

        for index, name in enumerate(COLORS):
            button = QPushButton(display_name(name).upper())
            button.setCheckable(True)
            button.setMinimumHeight(36)
            button.clicked.connect(
                lambda checked=False, color_name=name: self.select_color(color_name)
            )
            self.color_group.addButton(button)
            self.color_buttons[name] = button
            color_grid.addWidget(button, index // 6, index % 6)

        self.color_buttons["auto"].setChecked(True)
        layout.addLayout(color_grid)

        selectors = QHBoxLayout()
        selectors.setSpacing(14)

        mode_box = QVBoxLayout()
        mode_box.addWidget(section_label("DISPLAY MODE"))

        self.mode_combo = QComboBox()
        for name in MODES:
            self.mode_combo.addItem(display_name(name), name)
        mode_box.addWidget(self.mode_combo)

        special_box = QVBoxLayout()
        special_box.addWidget(section_label("SPECIAL EFFECT"))

        self.special_combo = QComboBox()
        self.special_combo.addItem("None", None)
        for name in SPECIALS:
            self.special_combo.addItem(display_name(name), name)
        self.special_combo.currentIndexChanged.connect(self.on_special_changed)
        special_box.addWidget(self.special_combo)

        selectors.addLayout(mode_box, 1)
        selectors.addLayout(special_box, 1)
        layout.addLayout(selectors)

        layout.addWidget(section_label("SPEED"))

        speed_row = QHBoxLayout()
        speed_row.setSpacing(8)

        self.speed_group = QButtonGroup(self)
        self.speed_group.setExclusive(True)

        for level in range(1, 6):
            button = QPushButton(str(level))
            button.setCheckable(True)
            button.setMinimumHeight(38)
            button.clicked.connect(
                lambda checked=False, speed_level=level: self.select_speed(speed_level)
            )
            self.speed_group.addButton(button)
            self.speed_buttons[level] = button
            speed_row.addWidget(button)

        self.speed_buttons[3].setChecked(True)
        layout.addLayout(speed_row)

        speed_help = QLabel("SLOWEST  1   •   2   •   3   •   4   •   5  FASTEST")
        speed_help.setObjectName("meta")
        layout.addWidget(speed_help)

        options = QHBoxLayout()
        options.setSpacing(24)

        self.flash = QCheckBox("FLASH")
        self.wide = QCheckBox("WIDE TEXT")
        self.flash.stateChanged.connect(self.update_send_enabled)
        self.wide.stateChanged.connect(self.update_send_enabled)

        options.addWidget(self.flash)
        options.addWidget(self.wide)
        options.addStretch(1)
        layout.addLayout(options)

        self.send_button = QPushButton("SEND TO SIGN")
        self.send_button.setObjectName("sendButton")
        self.send_button.setMinimumHeight(56)
        self.send_button.clicked.connect(self.send_current)
        layout.addWidget(self.send_button)

        layout.addWidget(section_label("QUICK TRANSMIT"))

        preset_row = QHBoxLayout()
        preset_row.setSpacing(8)
        for label, message in PRESETS.items():
            button = QPushButton(label)
            button.clicked.connect(
                lambda checked=False, preset_message=message: self.apply_preset(
                    preset_message
                )
            )
            preset_row.addWidget(button)
        layout.addLayout(preset_row)

        self.transmit_status = QLabel("Portable controller ready.")
        self.transmit_status.setWordWrap(True)
        self.transmit_status.setObjectName("footer")
        layout.addWidget(self.transmit_status)

        note = QLabel(
            "READY confirms that this computer can open the selected serial adapter. "
            "A successful transmission means the serial write completed without a "
            "transport error; this controller path does not provide a display ACK."
        )
        note.setWordWrap(True)
        note.setObjectName("meta")
        layout.addWidget(note)

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
            QLabel#meta, QLabel#footer {
                color: #8f96a3;
            }
            QLabel#section {
                color: #c4c8d0;
                font-weight: 700;
                letter-spacing: 1px;
                padding-top: 4px;
            }
            QLineEdit#messageEntry {
                background: #171a21;
                color: #f3f4f6;
                border: 1px solid #39404d;
                border-radius: 8px;
                padding: 10px 12px;
                font-size: 18px;
            }
            QComboBox, QPushButton, QCheckBox {
                font-size: 13px;
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
            QPushButton:checked {
                background: #303947;
                border-color: #73839b;
            }
            QPushButton:disabled {
                color: #686f7a;
                border-color: #2a2e36;
            }
            QPushButton#sendButton {
                font-size: 16px;
                font-weight: 800;
            }
            QPushButton#sendButton:enabled {
                background: #234934;
                border-color: #3d8a60;
            }
            """
        )

        self.populate_adapters()
        self.refresh_connection(active=True)

        self.connection_timer = QTimer(self)
        self.connection_timer.setInterval(2000)
        self.connection_timer.timeout.connect(self.connection_tick)
        self.connection_timer.start()

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

    def current_draft(self) -> MessageDraft:
        return MessageDraft(
            message=self.message.text(),
            color_name=self.selected_color,
            mode_name=self.mode_combo.currentData(),
            special_name=self.special_combo.currentData(),
            speed_level=self.selected_speed,
            flash=self.flash.isChecked(),
            wide=self.wide.isChecked(),
        )

    def set_connection_view(self, diagnostic) -> None:
        view = connection_view(diagnostic)
        self.connection_ready = view.can_send
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
        self.update_send_enabled()

    def update_send_enabled(self, *_args) -> None:
        self.send_button.setEnabled(
            can_transmit(self.connection_ready, self.current_draft())
        )

    def refresh_connection(self, *, active: bool = False, quiet: bool = False) -> None:
        port = self.selected_port() or AUTO_PORT

        if active:
            diagnostic = probe_connection(port)
            if diagnostic.ready:
                self.last_ready_port = diagnostic.port
            else:
                self.last_ready_port = None
        else:
            diagnostic = diagnose_device(port)

        display_diagnostic = diagnostic

        if (
            not active
            and diagnostic.state == "selected"
            and diagnostic.port == self.last_ready_port
        ):
            display_diagnostic = ConnectionDiagnostic(
                state="ready",
                message=(
                    f"Serial port {diagnostic.port} remains selected after the "
                    "last successful active connection check."
                ),
                port=diagnostic.port,
                source=diagnostic.source,
            )

        if diagnostic.state in {"no-adapter", "not-found", "port-not-found"}:
            self.last_ready_port = None

        self.set_connection_view(display_diagnostic)

        if not quiet:
            port_label = display_diagnostic.port or "no port"
            self.transmit_status.setText(
                f"{port_label}  //  {display_diagnostic.state.upper()}  //  "
                f"{display_diagnostic.message}"
            )

    def connection_tick(self) -> None:
        previous_port = self.selected_port()
        self.populate_adapters()

        current_port = self.selected_port()
        if previous_port and current_port != previous_port:
            self.last_ready_port = None

        self.refresh_connection(active=False, quiet=True)

    def on_adapter_changed(self, *_args) -> None:
        self.last_ready_port = None
        self.refresh_connection(active=True)

    def select_color(self, name: str) -> None:
        self.selected_color = name
        self.update_send_enabled()

    def select_speed(self, level: int) -> None:
        self.selected_speed = level
        self.update_send_enabled()

    def on_special_changed(self, *_args) -> None:
        special_selected = self.special_combo.currentData() is not None
        self.mode_combo.setEnabled(not special_selected)
        self.update_send_enabled()

    def apply_preset(self, message: str) -> None:
        self.message.setText(message)
        self.message.setFocus()
        self.message.setCursorPosition(len(message))

    def remember_selected(self) -> None:
        port = self.selected_port()
        if not port:
            return

        try:
            remember_port(port)
            self.populate_adapters()
            self.refresh_connection(active=True)
            self.transmit_status.setText(f"Saved adapter preference for {port}.")
        except Exception as exc:
            self.transmit_status.setText(f"Could not save adapter // {exc}")

    def forget_saved(self) -> None:
        try:
            forget_port()
            self.last_ready_port = None
            self.populate_adapters()
            self.refresh_connection(active=True)
            self.transmit_status.setText("Forgot the saved adapter preference.")
        except Exception as exc:
            self.transmit_status.setText(f"Could not forget adapter // {exc}")

    def send_current(self) -> None:
        draft = self.current_draft()

        try:
            kwargs = draft.send_kwargs()
        except ValueError as exc:
            self.transmit_status.setText(str(exc))
            self.update_send_enabled()
            return

        port = self.selected_port() or AUTO_PORT
        diagnostic = probe_connection(port)
        self.set_connection_view(diagnostic)

        if not diagnostic.ready:
            self.last_ready_port = None
            self.transmit_status.setText(
                f"{diagnostic.state.replace('-', ' ').upper()}  //  "
                f"{diagnostic.message}"
            )
            return

        self.last_ready_port = diagnostic.port
        self.send_button.setEnabled(False)
        self.transmit_status.setText("TRANSMITTING...")
        QApplication.processEvents()

        controller = BetaBriteController(port=port)

        try:
            controller.send(**kwargs)
            self.last_ready_port = controller.last_port or diagnostic.port

            description = (
                kwargs["message"]
                if kwargs["message"]
                else display_name(kwargs["special_name"])
            )
            actual_port = controller.last_port or diagnostic.port or port
            self.transmit_status.setText(
                f'TRANSMITTED  //  {actual_port}  //  "{description}"  //  '
                "serial write completed; display ACK unavailable"
            )

            ready_diagnostic = ConnectionDiagnostic(
                state="ready",
                message=(
                    f"Serial port {actual_port} transmitted without a transport error."
                ),
                port=actual_port,
                source="transmit",
            )
            self.set_connection_view(ready_diagnostic)

        except BetaBriteTransportError as exc:
            self.last_ready_port = None
            failure = ConnectionDiagnostic(
                state=exc.state,
                message=str(exc),
                port=exc.port or diagnostic.port,
                source="transmit",
            )
            self.set_connection_view(failure)
            self.transmit_status.setText(
                f"{exc.state.replace('-', ' ').upper()}  //  {exc}"
            )

        except Exception as exc:
            self.last_ready_port = None
            self.connection_ready = False
            self.update_send_enabled()
            self.transmit_status.setText(f"TRANSMIT FAILED  //  {exc}")

    def closeEvent(self, event) -> None:
        self.connection_timer.stop()
        super().closeEvent(event)


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
