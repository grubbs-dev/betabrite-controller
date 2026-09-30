"""Portable PySide6 desktop controller for BetaBrite signs."""

from __future__ import annotations

import sys
import logging
import platform
import os
from dataclasses import asdict, replace

from PySide6.QtCore import QTimer
from PySide6.QtGui import QFont, QIcon
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
    QMessageBox,
    QInputDialog,
    QDialog,
    QTextBrowser,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from . import __app_name__, __author__, __tagline__, __version__
from .branding import application_icon_path
from .connection import ConnectionDiagnostic, probe_connection
from .controller import COLORS, MODES, SPECIALS
from .desktop_controls import PRESETS, MessageDraft, can_transmit, display_name
from .desktop_model import adapter_options, default_adapter_index
from .devices import AUTO_PORT, diagnose_device, forget_port, remember_port
from .presentation import connection_view
from .settings import load_settings, save_settings, DevicePreference
from .diagnostics import log_path
from .desktop_worker import Operation
from .service import transmit
from .desktop_launcher import build_parser


DESKTOP_FILE_NAME = "betabrite-controller"


def smoke_test() -> int:
    from .desktop_launcher import smoke_test as run_smoke_test
    return run_smoke_test()


def section_label(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("section")
    return label


class PortableWindow(QMainWindow):
    """Cross-platform controller UI backed by the stabilized controller core."""

    def __init__(self, *, passive=False):
        super().__init__()
        self.busy = False
        self.operation = None
        self.manual_port = None
        self.active_sign = None
        self.settings = load_settings()
        self.options = []
        self.last_ready_port: str | None = None
        self.connection_ready = False
        self.selected_color = "auto"
        self.selected_speed = 3
        self.color_buttons: dict[str, QPushButton] = {}
        self.speed_buttons: dict[int, QPushButton] = {}

        self.setWindowTitle(__app_name__)
        self.setWindowIcon(QIcon(str(application_icon_path())))
        self.setMinimumSize(640, 480)
        self.resize(980, 900)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        shell = QWidget()
        shell_layout = QVBoxLayout(shell)
        shell_layout.setContentsMargins(12, 0, 12, 12)
        shell_layout.addWidget(scroll, 1)
        self.setCentralWidget(shell)

        root = QWidget()
        scroll.setWidget(root)

        layout = QVBoxLayout(root)
        layout.setContentsMargins(28, 26, 28, 26)
        layout.setSpacing(10)

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

        self.sign_combo = QComboBox()
        self.sign_combo.addItem("Saved signs — one sign communicates at a time", None)
        for name in self.settings.signs:
            self.sign_combo.addItem(name, name)
        self.sign_combo.activated.connect(self.select_saved_sign)
        layout.addWidget(self.sign_combo)
        actions = QHBoxLayout()
        for label, callback in (("Manual port…", self.choose_manual_port),
                                ("Save sign as…", self.save_sign),
                                ("About / Diagnostics", self.show_diagnostics),
                                ("Licenses", self.show_licenses)):
            button = QPushButton(label)
            button.clicked.connect(callback)
            actions.addWidget(button)
        layout.addLayout(actions)
        if sys.platform.startswith("linux") and os.environ.get("APPIMAGE"):
            install_button = QPushButton("Install in application menu")
            install_button.clicked.connect(self.install_desktop)
            layout.addWidget(install_button)
        first_run = QLabel("Power on the sign, connect its USB/serial cable, then click Refresh / Reconnect. "
                           "If discovery fails, select a manual port. Only one sign is active at a time.")
        first_run.setWordWrap(True)
        layout.addWidget(first_run)

        layout.addWidget(section_label("MESSAGE"))

        self.message = QLineEdit("BRIEF IN PROGRESS")
        self.message.setPlaceholderText("Type a message for the sign...")
        self.message.setMinimumHeight(48)
        self.message.setObjectName("messageEntry")
        self.message.returnPressed.connect(self.send_current)
        self.message.textChanged.connect(self.update_send_enabled)
        layout.addWidget(self.message)
        self.message_hint = QLabel()
        layout.addWidget(self.message_hint)

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

        self.send_button = QPushButton("Send to Sign")
        self.send_button.setObjectName("sendButton")
        self.send_button.setMinimumHeight(56)
        self.send_button.clicked.connect(self.send_current)
        # Keep the primary action visible even on smaller laptop screens.
        shell_layout.addWidget(self.send_button)

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

        library = QHBoxLayout()
        self.library_combo = QComboBox()
        self.library_combo.activated.connect(self.load_message)
        library.addWidget(self.library_combo, 1)
        save_button = QPushButton("Save message…")
        save_button.clicked.connect(self.save_message)
        library.addWidget(save_button)
        remove_button = QPushButton("Delete saved message")
        remove_button.clicked.connect(self.delete_message)
        library.addWidget(remove_button)
        layout.addLayout(library)

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

        self.refresh_button.setText("Refresh / Reconnect")
        self.restore_draft(self.settings.draft)
        self.refresh_library()
        self.populate_adapters()
        self.refresh_connection(active=not passive)

        self.connection_timer = QTimer(self)
        self.connection_timer.setInterval(2000)
        self.connection_timer.timeout.connect(self.connection_tick)
        self.connection_timer.start()

    def selected_port(self) -> str | None:
        if self.manual_port:
            return self.manual_port
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
            if previous_port is None:
                from .devices import resolve_device, DeviceDiscoveryError
                try:
                    selected = resolve_device().port
                    index = next((i for i, option in enumerate(self.options) if option.port == selected), -1)
                except DeviceDiscoveryError:
                    index = -1
            if previous_port:
                for candidate, option in enumerate(self.options):
                    if option.port == previous_port:
                        index = candidate
                        break

            self.adapter_combo.setCurrentIndex(index)
            self.adapter_combo.setPlaceholderText("Select a serial adapter")
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
        if not hasattr(self, "send_button"):
            return
        self.send_button.setEnabled(
            not self.busy and can_transmit(self.connection_ready, self.current_draft())
        )
        text = self.message.text()
        self.message_hint.setText(f"{len(text)} characters" +
                                  (" • Non-ASCII characters display as ?" if not text.isascii() else ""))

    def refresh_connection(self, *, active: bool = False, quiet: bool = False) -> None:
        if self.busy:
            return
        if self.active_sign:
            from .devices import resolve_device, DeviceDiscoveryError
            current = load_settings()
            try:
                selected = resolve_device(settings=replace(current, preferred_device=current.signs[self.active_sign]))
                self.manual_port = selected.port
            except (DeviceDiscoveryError, KeyError) as exc:
                self.last_ready_port = None
                self.set_connection_view(ConnectionDiagnostic(state="not-found", message=str(exc)))
                return
        if active:
            self.populate_adapters()
            port = self.selected_port() or AUTO_PORT
            self.start_operation(lambda: probe_connection(port))
            return
        port = self.selected_port() or AUTO_PORT

        diagnostic = diagnose_device(port)
        from .devices import port_is_available
        if diagnostic.port and not port_is_available(diagnostic.port):
            diagnostic = ConnectionDiagnostic(state="port-not-found", message="The adapter is disconnected. Reconnect it and click Refresh / Reconnect.", port=diagnostic.port)

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
        if self.busy:
            return
        previous_port = self.selected_port()
        self.populate_adapters()

        current_port = self.selected_port()
        if previous_port and current_port != previous_port:
            self.last_ready_port = None

        self.refresh_connection(active=False, quiet=True)

    def on_adapter_changed(self, *_args) -> None:
        self.manual_port = None
        self.active_sign = None
        if hasattr(self, "sign_combo"):
            self.sign_combo.setCurrentIndex(0)
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
        except Exception:
            self.settings_error()

    def forget_saved(self) -> None:
        try:
            forget_port()
            self.active_sign = None
            self.manual_port = None
            self.sign_combo.setCurrentIndex(0)
            self.last_ready_port = None
            self.populate_adapters()
            self.refresh_connection(active=True)
            self.transmit_status.setText("Forgot the saved adapter preference.")
        except Exception:
            self.settings_error()

    def send_current(self) -> None:
        if self.busy or not self.connection_ready:
            return
        draft = self.current_draft()
        try:
            draft.validate()
        except ValueError as exc:
            self.transmit_status.setText(str(exc))
            self.update_send_enabled()
            return
        port = self.selected_port() or AUTO_PORT
        self.sent_draft = asdict(draft)
        self.start_operation(lambda: transmit(port, draft))

    def start_operation(self, callback):
        if self.busy:
            return
        self.busy = True
        self.update_send_enabled()
        for widget in (self.adapter_combo, self.refresh_button, self.remember_button,
                       self.forget_button, self.sign_combo):
            widget.setEnabled(False)
        self.transmit_status.setText("Working…")
        self.operation = Operation(callback, self)
        self.operation.finished.connect(self.operation_finished)
        self.operation.start()

    def operation_finished(self):
        result = self.operation.result
        self.operation.deleteLater()
        self.operation = None
        self.busy = False
        for widget in (self.adapter_combo, self.refresh_button, self.remember_button,
                       self.forget_button, self.sign_combo):
            widget.setEnabled(True)
        self.last_ready_port = result.port if result.ready else None
        self.set_connection_view(result)
        self.transmit_status.setText(result.message)
        if result.ready and result.source == "transmit":
            current = load_settings()
            recent = [self.sent_draft] + [item for item in current.recent_messages if item != self.sent_draft]
            self.persist(replace(current, draft=self.sent_draft, recent_messages=recent[:20]))
            self.refresh_library()

    def settings_error(self):
        logging.getLogger(__name__).exception("Could not save preferences")
        self.transmit_status.setText("Could not save preferences. Check free disk space and access to your configuration folder. See About / Diagnostics.")

    def persist(self, settings):
        try:
            save_settings(settings)
            self.settings = settings
            return True
        except OSError:
            self.settings_error()
            return False

    def restore_draft(self, value):
        if not value:
            return
        draft = MessageDraft(**value)
        self.message.setText(draft.message)
        self.selected_color = draft.color_name
        self.color_buttons[draft.color_name].setChecked(True)
        self.selected_speed = draft.speed_level
        self.speed_buttons[draft.speed_level].setChecked(True)
        self.mode_combo.setCurrentIndex(self.mode_combo.findData(draft.mode_name))
        self.special_combo.setCurrentIndex(self.special_combo.findData(draft.special_name))
        self.flash.setChecked(draft.flash)
        self.wide.setChecked(draft.wide)
        self.update_send_enabled()

    def refresh_library(self):
        current = load_settings()
        self.library_combo.clear()
        self.library_combo.addItem("Saved and recent messages…", None)
        for name, draft in current.saved_messages.items():
            self.library_combo.addItem(f"Saved: {name}", (name, draft))
        for draft in current.recent_messages:
            self.library_combo.addItem(f"Recent: {draft['message'][:50] or draft.get('special_name')}", (None, draft))

    def load_message(self):
        value = self.library_combo.currentData()
        if value:
            self.restore_draft(value[1])

    def save_message(self):
        try:
            draft = asdict(self.current_draft().validate())
        except ValueError as exc:
            self.transmit_status.setText(str(exc))
            return
        name, accepted = QInputDialog.getText(self, "Save message", "Message name (reuse a name to update it):")
        if accepted and name.strip():
            current = load_settings()
            self.persist(replace(current, saved_messages={**current.saved_messages, name.strip(): draft}))
            self.refresh_library()

    def delete_message(self):
        value = self.library_combo.currentData()
        if value and value[0]:
            current = load_settings()
            messages = dict(current.saved_messages)
            messages.pop(value[0], None)
            self.persist(replace(current, saved_messages=messages))
            self.refresh_library()

    def choose_manual_port(self):
        if self.busy:
            return
        port, accepted = QInputDialog.getText(self, "Manual serial port", "Port (for example COM4 or /dev/ttyUSB0):")
        if accepted and port.strip():
            self.active_sign = None
            self.sign_combo.setCurrentIndex(0)
            self.manual_port = port.strip()
            self.last_ready_port = None
            self.refresh_connection(active=True)

    def save_sign(self):
        if self.busy or not self.selected_port():
            return
        name, accepted = QInputDialog.getText(self, "Save sign", "Friendly sign name (reuse a name to update it):")
        if accepted and name.strip():
            try:
                selection = remember_port(self.selected_port())
                device = DevicePreference.from_device(selection.device)
                current = load_settings()
                if self.persist(replace(current, signs={**current.signs, name.strip(): device})):
                    self.sign_combo.clear()
                    self.sign_combo.addItem("Saved signs — one sign communicates at a time", None)
                    for saved in self.settings.signs:
                        self.sign_combo.addItem(saved, saved)
            except Exception:
                self.settings_error()

    def select_saved_sign(self):
        if self.busy:
            return
        name = self.sign_combo.currentData()
        if name:
            self.active_sign = name
            self.manual_port = None
            self.last_ready_port = None
            from .devices import resolve_device
            current = load_settings()
            preference = current.signs.get(name)
            try:
                selection = resolve_device(settings=replace(current, preferred_device=preference))
                # A saved sign must never silently fall back to another adapter.
                if selection.source not in {"remembered", "remembered-port"}:
                    raise ValueError("Saved sign is disconnected. Reconnect its adapter or select a port manually.")
                self.manual_port = selection.port
                self.active_sign = name
                self.persist(replace(current, preferred_device=preference))
                self.refresh_connection(active=True)
            except (ValueError, RuntimeError) as exc:
                self.last_ready_port = None
                self.set_connection_view(ConnectionDiagnostic(state="not-found", message=str(exc)))
                self.transmit_status.setText(str(exc))

    def show_diagnostics(self):
        ports = "\n".join(option.port for option in self.options) or "No USB adapters detected"
        QMessageBox.information(self, "About / Diagnostics",
            f"{__app_name__} {__version__}\nMIT License — Copyright 2026 Grubbs\n"
            "https://github.com/grubbs-dev/betabrite-controller\n\n"
            f"OS: {platform.system()} {platform.release()}\n"
            f"Selected: {self.selected_port() or 'Automatic'}\n"
            f"State: {self.status_badge.text()}\nDetected ports:\n{ports}\n\nLogs: {log_path()}\n"
            "Dependencies: PySide6 / Qt (LGPLv3), pyserial (BSD), alphasignpy (MIT).")

    def install_desktop(self):
        from .platform_integration import install_appimage
        try:
            install_appimage()
            QMessageBox.information(self, __app_name__, "Installed for your user. You can now launch BetaBrite Controller from the application menu.")
        except (OSError, ValueError):
            logging.getLogger(__name__).exception("Desktop installation failed")
            QMessageBox.warning(self, __app_name__, "Could not install the application-menu shortcut. Check disk space and permissions for your user application folder.")

    def show_licenses(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Licenses and third-party notices")
        dialog.resize(760, 560)
        layout = QVBoxLayout(dialog)
        text = QTextBrowser()
        directory = application_icon_path().parent / "licenses"
        text.setPlainText("\n\n".join(path.name + "\n\n" + path.read_text(encoding="utf-8")
                                      for path in sorted(directory.glob("*.txt"))))
        layout.addWidget(text)
        dialog.exec()

    def closeEvent(self, event) -> None:
        if self.busy:
            self.transmit_status.setText("Please wait for the current operation before closing.")
            event.ignore()
            return
        self.connection_timer.stop()
        self.persist(replace(load_settings(), draft=asdict(self.current_draft())))
        super().closeEvent(event)


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)

    if args.smoke_test:
        return smoke_test()

    app = QApplication(sys.argv if argv is None else [sys.argv[0], *argv])
    app.setApplicationName(__app_name__)
    app.setApplicationDisplayName(__app_name__)
    app.setOrganizationName("Grubbs")
    app.setOrganizationDomain("grubbs.dev")
    app.setDesktopFileName(DESKTOP_FILE_NAME)
    app.setWindowIcon(QIcon(str(application_icon_path())))

    def report_exception(exc_type, exc, traceback):
        logging.getLogger(__name__).error("Unexpected application error", exc_info=(exc_type, exc, traceback))
        QMessageBox.warning(None, __app_name__, "The operation could not be completed. Try again or restart the application. Technical details are in the application log.")

    sys.excepthook = report_exception

    window = PortableWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
