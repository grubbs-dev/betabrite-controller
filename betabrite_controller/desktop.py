"""Portable PySide6 desktop controller for BetaBrite signs."""

from __future__ import annotations

import logging
import os
import platform
import sys
from dataclasses import asdict, replace

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, QTimer
from PySide6.QtGui import QAction, QColor, QFont, QFontMetrics, QIcon, QPainter, QPen
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenuBar,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QSpinBox,
    QSplitter,
    QStackedWidget,
    QStatusBar,
    QTextBrowser,
    QToolBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from . import __app_name__, __version__
from .branding import application_icon_path
from .connection import ConnectionDiagnostic, probe_connection
from .controller import COLORS, MODES, SPECIALS
from .benchmark import physical_live_benchmark_blocked_report, run_virtual_benchmark_suite
from .desktop_controls import MessageDraft, can_transmit, display_name
from .desktop_launcher import build_parser
from .desktop_model import adapter_options, default_adapter_index
from .desktop_worker import Operation
from .devices import AUTO_PORT, diagnose_device, forget_port, remember_port
from .dino import DinoRunnerSource
from .live import LiveScheduler
from .diagnostics import log_path
from .presentation import connection_view
from .pixel_model import (
    DEFAULT_HEIGHT,
    DEFAULT_WIDTH,
    PixelColor,
    PixelDocument,
    PixelDocumentError,
)
from .service import clear_sign, transmit, transmit_graphic
from .settings import DevicePreference, load_settings, save_settings


DESKTOP_FILE_NAME = "betabrite-controller"


def smoke_test() -> int:
    from .desktop_launcher import smoke_test as run_smoke_test

    return run_smoke_test()


def section_label(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("section")
    return label


class BetaBritePreview(QFrame):
    """Paint a compact physical sign preview without protocol responsibilities."""

    COLOR_MAP = {
        "auto": "#f3a21a",
        "red": "#ee3b2f",
        "green": "#36b24a",
        "amber": "#f3a21a",
        "yellow": "#efc33a",
        "orange": "#e87722",
        "brown": "#a85f2d",
        "dim-red": "#9d2a24",
        "dim-green": "#247a35",
        "rainbow1": "#ee3b2f",
        "rainbow2": "#36b24a",
        "mix": "#f3a21a",
    }
    MIX_SEQUENCE = ("#ee3b2f", "#36b24a", "#f3a21a")

    def __init__(self, parent=None):
        super().__init__(parent)
        self.message = "BRIEF IN PROGRESS"
        self.color_name = "auto"
        self.alignment = "center"
        self.font_mode = "normal"
        self.setObjectName("signPreview")
        self.setMinimumHeight(96)
        self.setMaximumHeight(112)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def set_preview(
        self,
        *,
        message: str,
        color_name: str,
        alignment: str,
        font_mode: str,
    ) -> None:
        self.message = message or " "
        self.color_name = color_name
        self.alignment = alignment
        self.font_mode = font_mode
        self.update()

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        bounds = QRectF(self.rect()).adjusted(8, 8, -8, -8)
        painter.setPen(QPen(QColor("#20252a"), 1))
        painter.setBrush(QColor("#202326"))
        painter.drawRoundedRect(bounds, 4, 4)

        display = bounds.adjusted(26, 18, -26, -36)
        painter.setPen(QPen(QColor("#141a18"), 1))
        painter.setBrush(QColor("#050807"))
        painter.drawRect(display)

        self._draw_matrix(painter, display)
        self._draw_message(painter, display)
        self._draw_bezel_labels(painter, bounds)

    def _draw_matrix(self, painter: QPainter, display: QRectF) -> None:
        painter.setPen(QPen(QColor("#17201b"), 1))
        step = 8
        x = display.left() + 8
        while x < display.right() - 4:
            y = display.top() + 8
            while y < display.bottom() - 4:
                painter.drawPoint(QPointF(x, y))
                y += step
            x += step

    def _font(self, display: QRectF) -> QFont:
        font = QFont("DejaVu Sans Mono")
        font.setBold(True)
        font.setStyleHint(QFont.StyleHint.Monospace)
        size = max(14, min(28, int(display.height() * 0.36)))
        if self.font_mode == "small":
            size = max(12, int(size * 0.74))
        elif self.font_mode == "large":
            size = int(size * 1.16)
        elif self.font_mode in {"wide", "double-wide"}:
            size = int(size * 1.05)
        font.setPointSize(size)
        return font

    def _draw_message(self, painter: QPainter, display: QRectF) -> None:
        text = self.message.strip() or " "
        font = self._font(display)
        painter.setFont(font)
        metrics = QFontMetrics(font)
        spacing = 2 if self.font_mode in {"wide", "double-wide"} else 0
        text_width = sum(metrics.horizontalAdvance(char) + spacing for char in text)
        if self.alignment == "left":
            x = display.left() + 18
        elif self.alignment == "right":
            x = display.right() - text_width - 18
        else:
            x = display.center().x() - text_width / 2
        baseline = display.center().y() + metrics.ascent() / 2 - 3

        for index, char in enumerate(text):
            painter.setPen(QPen(QColor(self._character_color(index)), 1))
            painter.drawText(QPointF(x, baseline), char)
            x += metrics.horizontalAdvance(char) + spacing

    def _character_color(self, index: int) -> str:
        if self.color_name in {"mix", "rainbow1", "rainbow2"}:
            return self.MIX_SEQUENCE[index % len(self.MIX_SEQUENCE)]
        return self.COLOR_MAP.get(self.color_name, self.COLOR_MAP["auto"])

    def _draw_bezel_labels(self, painter: QPainter, bounds: QRectF) -> None:
        label_font = QFont("DejaVu Sans Mono")
        label_font.setPointSize(6)
        label_font.setBold(True)
        painter.setFont(label_font)
        painter.setPen(QColor("#8f9692"))
        painter.drawText(QPointF(bounds.left() + 28, bounds.bottom() - 20), "BETABRITE PRISM")
        painter.setPen(QColor("#4fb35d"))
        painter.drawEllipse(QPointF(bounds.right() - 88, bounds.bottom() - 22), 2, 2)
        painter.drawText(QPointF(bounds.right() - 80, bounds.bottom() - 19), "POWER")
        painter.setPen(QColor("#f3a21a"))
        painter.drawEllipse(QPointF(bounds.right() - 42, bounds.bottom() - 22), 2, 2)
        painter.drawText(QPointF(bounds.right() - 34, bounds.bottom() - 19), "DATA")


class PixelCanvasWidget(QFrame):
    """Clickable one-cell-per-pixel framebuffer editor."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.frame = None
        self.onion_frame = None
        self.cell_size = 14
        self.selected_color = PixelColor.RED
        self.tool = "pencil"
        self.on_change = None
        self.last_coordinate = None
        self.setMouseTracking(True)
        self.setObjectName("pixelCanvas")

    def set_frame(self, frame, *, onion_frame=None) -> None:
        self.frame = frame
        self.onion_frame = onion_frame
        self.last_coordinate = None
        self._sync_size()
        self.update()

    def set_zoom(self, value: int) -> None:
        self.cell_size = max(8, min(28, int(value)))
        self._sync_size()
        self.update()

    def _sync_size(self) -> None:
        if not self.frame:
            return
        width = self.frame.width * self.cell_size + 1
        height = self.frame.height * self.cell_size + 1
        self.setMinimumSize(width, height)
        self.setMaximumSize(width, height)

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        if not self.frame:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        painter.fillRect(self.rect(), QColor("#101417"))

        if self.onion_frame is not None:
            for y in range(self.onion_frame.height):
                for x in range(self.onion_frame.width):
                    color = self.onion_frame.get_pixel(x, y)
                    if color is not PixelColor.OFF:
                        rect = QRectF(x * self.cell_size + 1, y * self.cell_size + 1, self.cell_size - 1, self.cell_size - 1)
                        onion = QColor(color.hex_color)
                        onion.setAlpha(68)
                        painter.fillRect(rect, onion)

        for y in range(self.frame.height):
            for x in range(self.frame.width):
                color = self.frame.get_pixel(x, y)
                rect = QRectF(x * self.cell_size + 1, y * self.cell_size + 1, self.cell_size - 1, self.cell_size - 1)
                fill = QColor("#151b20") if color is PixelColor.OFF else QColor(color.hex_color)
                painter.fillRect(rect, fill)

        painter.setPen(QPen(QColor("#2b343b"), 1))
        for x in range(self.frame.width + 1):
            xpos = x * self.cell_size
            painter.drawLine(xpos, 0, xpos, self.frame.height * self.cell_size)
        for y in range(self.frame.height + 1):
            ypos = y * self.cell_size
            painter.drawLine(0, ypos, self.frame.width * self.cell_size, ypos)

    def mousePressEvent(self, event) -> None:
        self._draw_from_event(event)

    def mouseMoveEvent(self, event) -> None:
        if event.buttons() & Qt.MouseButton.LeftButton:
            self._draw_from_event(event)

    def mouseReleaseEvent(self, event) -> None:
        self.last_coordinate = None

    def _draw_from_event(self, event) -> None:
        if not self.frame:
            return
        position = event.position()
        x = int(position.x() // self.cell_size)
        y = int(position.y() // self.cell_size)
        if x < 0 or y < 0 or x >= self.frame.width or y >= self.frame.height:
            return
        if self.last_coordinate == (x, y):
            return
        self.last_coordinate = (x, y)
        color = PixelColor.OFF if self.tool == "eraser" else self.selected_color
        self.frame.set_pixel(x, y, color)
        if self.on_change is not None:
            self.on_change(x, y)
        self.update()


class PixelPreviewWidget(QFrame):
    """Sign-style preview for the current pixel frame."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.frame = None
        self.setObjectName("pixelPreview")
        self.setMinimumHeight(92)
        self.setMaximumHeight(118)

    def set_frame(self, frame) -> None:
        self.frame = frame
        self.update()

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        bounds = QRectF(self.rect()).adjusted(8, 8, -8, -8)
        painter.setPen(QPen(QColor("#20252a"), 1))
        painter.setBrush(QColor("#202326"))
        painter.drawRoundedRect(bounds, 4, 4)
        display = bounds.adjusted(24, 18, -24, -28)
        painter.setBrush(QColor("#050807"))
        painter.setPen(QPen(QColor("#141a18"), 1))
        painter.drawRect(display)
        if not self.frame:
            return
        cell = min(display.width() / self.frame.width, display.height() / self.frame.height)
        size = max(2.0, cell * 0.72)
        origin_x = display.center().x() - (self.frame.width * cell) / 2
        origin_y = display.center().y() - (self.frame.height * cell) / 2
        for y in range(self.frame.height):
            for x in range(self.frame.width):
                color = self.frame.get_pixel(x, y)
                if color is PixelColor.OFF:
                    painter.setPen(QPen(QColor("#17201b"), 1))
                    painter.drawPoint(QPointF(origin_x + x * cell + cell / 2, origin_y + y * cell + cell / 2))
                else:
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.setBrush(QColor(color.hex_color))
                    painter.drawEllipse(QPointF(origin_x + x * cell + cell / 2, origin_y + y * cell + cell / 2), size / 2, size / 2)


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
        self.selected_alignment = "center"
        self.selected_font_mode = "normal"
        self.color_buttons: dict[str, QRadioButton] = {}
        self.mode_buttons: dict[str, QToolButton] = {}
        self.pixel_document = PixelDocument.new()
        self.pixel_document_path = None
        self.pixel_frame_index = 0
        self.pixel_tool = "pencil"
        self.pixel_color = PixelColor.RED
        self.pixel_playing = False
        self.pixel_dirty = False
        self.live_source = DinoRunnerSource()
        self.live_scheduler: LiveScheduler | None = None
        self.live_report = None
        self.live_mode_status = "Virtual preview only."

        self.setWindowTitle(__app_name__)
        self.setWindowIcon(QIcon(str(application_icon_path())))
        self.setMinimumSize(1024, 700)
        self.resize(1280, 820)

        self._build_actions()
        self._build_menus()
        self._build_toolbar()
        self._build_central_area()
        self._build_status_bar()
        self._apply_style()

        self.restore_draft(self.settings.draft)
        self.refresh_library()
        self.populate_adapters()
        self.refresh_connection(active=not passive)
        self.update_preview()

        self.connection_timer = QTimer(self)
        self.connection_timer.setInterval(2000)
        self.connection_timer.timeout.connect(self.connection_tick)
        self.connection_timer.start()

        self.pixel_timer = QTimer(self)
        self.pixel_timer.timeout.connect(self.pixel_playback_tick)

        self.live_timer = QTimer(self)
        self.live_timer.setInterval(33)
        self.live_timer.timeout.connect(self.live_tick)

    def _build_actions(self) -> None:
        style = self.style()
        self.connect_action = QAction(
            style.standardIcon(style.StandardPixmap.SP_DialogApplyButton),
            "Connect",
            self,
        )
        self.connect_action.triggered.connect(self.connect_selected)

        self.disconnect_action = QAction(
            style.standardIcon(style.StandardPixmap.SP_DialogCancelButton),
            "Disconnect",
            self,
        )
        self.disconnect_action.triggered.connect(self.disconnect_selected)

        self.refresh_action = QAction(
            style.standardIcon(style.StandardPixmap.SP_BrowserReload),
            "Refresh Devices",
            self,
        )
        self.refresh_action.triggered.connect(self.refresh_devices)

        self.remember_adapter_action = QAction("Use Selected Adapter", self)
        self.remember_adapter_action.triggered.connect(self.remember_selected)

        self.forget_adapter_action = QAction("Forget Saved Adapter", self)
        self.forget_adapter_action.triggered.connect(self.forget_saved)

        self.send_action = QAction(
            style.standardIcon(style.StandardPixmap.SP_ArrowForward),
            "Send Message",
            self,
        )
        self.send_action.setShortcut("Ctrl+Return")
        self.send_action.triggered.connect(self.send_current)

        self.clear_action = QAction(
            style.standardIcon(style.StandardPixmap.SP_DialogResetButton),
            "Clear Sign",
            self,
        )
        self.clear_action.triggered.connect(self.clear_current_sign)

        self.save_action = QAction(
            style.standardIcon(style.StandardPixmap.SP_DialogSaveButton),
            "Save Message",
            self,
        )
        self.save_action.setShortcut("Ctrl+S")
        self.save_action.triggered.connect(self.save_message)

        self.load_action = QAction(
            style.standardIcon(style.StandardPixmap.SP_DialogOpenButton),
            "Load Message",
            self,
        )
        self.load_action.triggered.connect(self.load_message)

        self.diagnostics_action = QAction("Diagnostics", self)
        self.diagnostics_action.triggered.connect(self.show_diagnostics)

        self.licenses_action = QAction("Licenses", self)
        self.licenses_action.triggered.connect(self.show_licenses)

        self.quit_action = QAction("Quit", self)
        self.quit_action.setShortcut("Ctrl+Q")
        self.quit_action.triggered.connect(self.close)

    def _build_menus(self) -> None:
        menubar = QMenuBar(self)
        self.setMenuBar(menubar)

        file_menu = menubar.addMenu("File")
        file_menu.addAction(self.save_action)
        file_menu.addAction(self.load_action)
        file_menu.addSeparator()
        file_menu.addAction(self.quit_action)

        device_menu = menubar.addMenu("Device")
        device_menu.addAction(self.connect_action)
        device_menu.addAction(self.disconnect_action)
        device_menu.addAction(self.refresh_action)
        device_menu.addSeparator()
        device_menu.addAction(self.remember_adapter_action)
        device_menu.addAction(self.forget_adapter_action)
        device_menu.addSeparator()
        manual = device_menu.addAction("Manual Port...")
        manual.triggered.connect(self.choose_manual_port)
        save_sign = device_menu.addAction("Save Sign As...")
        save_sign.triggered.connect(self.save_sign)

        sign_menu = menubar.addMenu("Sign")
        sign_menu.addAction(self.send_action)
        sign_menu.addAction(self.clear_action)
        sign_menu.addSeparator()
        preview = sign_menu.addAction("Preview")
        preview.triggered.connect(self.update_preview)

        tools_menu = menubar.addMenu("Tools")
        tools_menu.addAction(self.diagnostics_action)
        tools_menu.addAction(self.licenses_action)

        help_menu = menubar.addMenu("Help")
        about = help_menu.addAction("About")
        about.triggered.connect(self.show_diagnostics)

    def _build_toolbar(self) -> None:
        toolbar = QToolBar("Main", self)
        toolbar.setObjectName("mainToolbar")
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(16, 16))
        toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        toolbar.addAction(self.connect_action)
        toolbar.addAction(self.disconnect_action)
        toolbar.addAction(self.refresh_action)
        toolbar.addSeparator()
        toolbar.addAction(self.send_action)
        toolbar.addAction(self.clear_action)
        toolbar.addSeparator()
        toolbar.addAction(self.save_action)
        toolbar.addAction(self.load_action)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, toolbar)

    def _build_central_area(self) -> None:
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setObjectName("mainSplitter")
        splitter.addWidget(self._build_sidebar())
        splitter.addWidget(self._build_workspace())
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([238, 980])
        self.setCentralWidget(splitter)
        self.navigation.setCurrentRow(0)

    def _build_sidebar(self) -> QWidget:
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setMinimumWidth(220)
        sidebar.setMaximumWidth(300)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(12, 12, 12, 10)
        layout.setSpacing(8)

        title = QLabel("Device")
        title.setObjectName("panelTitle")
        layout.addWidget(title)

        device_card = QFrame()
        device_card.setObjectName("deviceCard")
        device_layout = QVBoxLayout(device_card)
        device_layout.setContentsMargins(10, 9, 10, 10)
        device_layout.setSpacing(6)

        self.status_badge = QLabel("Checking")
        self.status_badge.setObjectName("connectionBadge")
        self.device_name_label = QLabel("BetaBrite Prism")
        self.device_name_label.setObjectName("deviceName")
        self.status_detail = QLabel("Checking the serial adapter...")
        self.status_detail.setWordWrap(True)
        self.status_detail.setObjectName("muted")
        self.status_detail.setMaximumHeight(42)
        device_layout.addWidget(self.status_badge)
        device_layout.addWidget(self.device_name_label)
        device_layout.addWidget(self.status_detail)
        layout.addWidget(device_card)

        grid = QGridLayout()
        grid.setHorizontalSpacing(6)
        grid.setVerticalSpacing(5)
        grid.addWidget(QLabel("Serial / COM port"), 0, 0)
        grid.addWidget(QLabel("Baud rate"), 0, 1)
        self.adapter_combo = QComboBox()
        self.adapter_combo.currentIndexChanged.connect(self.on_adapter_changed)
        grid.addWidget(self.adapter_combo, 1, 0)
        self.baud_field = QLineEdit("9600")
        self.baud_field.setReadOnly(True)
        self.baud_field.setToolTip("Fixed by the supported BetaBrite serial protocol: 9600 baud.")
        grid.addWidget(self.baud_field, 1, 1)
        grid.addWidget(QLabel("Sign address"), 2, 0, 1, 2)
        self.address_field = QLineEdit("00")
        self.address_field.setReadOnly(True)
        self.address_field.setToolTip("Fixed by the supported controller path: sign address 00.")
        grid.addWidget(self.address_field, 3, 0, 1, 2)
        layout.addLayout(grid)

        action_grid = QGridLayout()
        action_grid.setHorizontalSpacing(6)
        action_grid.setVerticalSpacing(6)
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.refresh_devices)
        self.remember_button = QPushButton("Connect")
        self.remember_button.clicked.connect(self.connect_selected)
        self.forget_button = QPushButton("Disconnect")
        self.forget_button.clicked.connect(self.disconnect_selected)
        settings_button = QPushButton("Settings")
        settings_button.clicked.connect(lambda: self.navigation.setCurrentRow(7))
        action_grid.addWidget(self.remember_button, 0, 0)
        action_grid.addWidget(self.forget_button, 0, 1)
        action_grid.addWidget(self.refresh_button, 1, 0)
        action_grid.addWidget(settings_button, 1, 1)
        layout.addLayout(action_grid)

        self.sign_combo = QComboBox()
        self.sign_combo.addItem("Saved signs", None)
        for name in self.settings.signs:
            self.sign_combo.addItem(name, name)
        self.sign_combo.activated.connect(self.select_saved_sign)
        layout.addWidget(self.sign_combo)

        layout.addWidget(section_label("Navigation"))
        self.navigation = QListWidget()
        self.navigation.setObjectName("navigation")
        self.navigation.setFixedHeight(158)
        for text in (
            "Message Editor",
            "Pixel Studio",
            "Live Mode",
            "Sign Controls",
            "Scheduling",
            "Diagnostics",
            "Hardware Setup",
            "Application Settings",
        ):
            QListWidgetItem(text, self.navigation)
        self.navigation.currentRowChanged.connect(self._show_page)
        layout.addWidget(self.navigation, 1)

        self.status_meta = QLabel("")
        self.status_meta.setObjectName("muted")
        self.status_meta.setWordWrap(True)
        layout.addWidget(self.status_meta)
        return sidebar

    def _build_workspace(self) -> QWidget:
        self.pages = QStackedWidget()
        self.pages.addWidget(self._build_message_page())
        self.pages.addWidget(self._build_pixel_page())
        self.pages.addWidget(self._build_live_page())
        self.pages.addWidget(self._placeholder_page("Sign Controls", "Display mode, color, and timing controls are available in Message Editor."))
        self.pages.addWidget(self._placeholder_page("Scheduling", "Scheduling is not active for this sign session."))
        self.pages.addWidget(self._diagnostics_page())
        self.pages.addWidget(self._hardware_page())
        self.pages.addWidget(self._settings_page())
        return self.pages

    def _build_message_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(18, 10, 18, 8)
        layout.setSpacing(8)

        heading = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("Message Editor")
        title.setObjectName("pageTitle")
        subtitle = QLabel("Compose and transmit a message to the connected sign.")
        subtitle.setObjectName("muted")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        heading.addLayout(title_box, 1)
        self.character_count = QLabel("0 / 80 characters")
        self.character_count.setObjectName("muted")
        heading.addWidget(self.character_count)
        layout.addLayout(heading)

        self.preview = BetaBritePreview()
        layout.addWidget(self.preview)

        editor = QFrame()
        editor.setObjectName("editorPanel")
        editor_layout = QVBoxLayout(editor)
        editor_layout.setContentsMargins(12, 8, 12, 8)
        editor_layout.setSpacing(5)

        meta_row = QHBoxLayout()
        meta_row.addWidget(section_label("Message"))
        meta_row.addStretch(1)
        self.profile_label = QLabel("Default display profile - Address 00")
        self.profile_label.setObjectName("muted")
        meta_row.addWidget(self.profile_label)
        editor_layout.addLayout(meta_row)

        self.message = QLineEdit("BRIEF IN PROGRESS")
        self.message.setObjectName("messageEntry")
        self.message.setPlaceholderText("Type a message for the sign...")
        self.message.returnPressed.connect(self.send_current)
        self.message.textChanged.connect(self.update_send_enabled)
        self.message.textChanged.connect(self.update_preview)
        editor_layout.addWidget(self.message)

        controls = QHBoxLayout()
        controls.setSpacing(18)
        controls.addLayout(self._font_controls(), 2)
        controls.addLayout(self._alignment_controls(), 1)
        editor_layout.addLayout(controls)

        color_layout = QVBoxLayout()
        color_layout.setSpacing(5)
        color_layout.addWidget(section_label("Color"))
        color_row = QHBoxLayout()
        color_row.setSpacing(10)
        self.color_group = QButtonGroup(self)
        self.color_group.setExclusive(True)
        primary_colors = ("auto", "red", "green", "amber", "rainbow1", "mix")
        for name in primary_colors:
            label = "Rainbow" if name == "rainbow1" else ("Mixed" if name == "mix" else display_name(name))
            button = QRadioButton(label)
            button.clicked.connect(lambda checked=False, color_name=name: self.select_color(color_name))
            self.color_group.addButton(button)
            self.color_buttons[name] = button
            color_row.addWidget(button)
        for name in COLORS:
            if name not in self.color_buttons:
                button = QRadioButton(display_name(name))
                button.setVisible(False)
                self.color_group.addButton(button)
                self.color_buttons[name] = button
        self.more_color_combo = QComboBox()
        self.more_color_combo.addItem("More colors", None)
        for name in COLORS:
            self.more_color_combo.addItem(display_name(name), name)
        self.more_color_combo.currentIndexChanged.connect(self._select_more_color)
        color_row.addWidget(self.more_color_combo)
        color_row.addStretch(1)
        color_layout.addLayout(color_row)
        editor_layout.addLayout(color_layout)

        effect_layout = QVBoxLayout()
        effect_layout.setSpacing(5)
        effect_layout.addWidget(section_label("Effect"))
        effect_row = QHBoxLayout()
        effect_row.setSpacing(6)
        self.mode_combo = QComboBox()
        for name in MODES:
            self.mode_combo.addItem(display_name(name), name)
        self.mode_combo.currentIndexChanged.connect(self._sync_mode_buttons)
        self.mode_combo.currentIndexChanged.connect(self.update_send_enabled)
        self.mode_combo.currentIndexChanged.connect(self.update_preview)

        self.mode_group = QButtonGroup(self)
        self.mode_group.setExclusive(True)
        common_modes = ("hold", "rotate", "roll-left", "roll-right", "wipe", "scroll", "flash")
        for name in common_modes:
            mode_name = "wipe-left" if name == "wipe" else name
            button = QToolButton()
            button.setText(display_name(name))
            button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
            button.setMinimumHeight(26)
            button.setMinimumWidth(68)
            button.setCheckable(True)
            button.clicked.connect(lambda checked=False, selected=mode_name: self.select_mode(selected))
            self.mode_group.addButton(button)
            self.mode_buttons[mode_name] = button
            effect_row.addWidget(button)
        effect_row.addWidget(QLabel("More"))
        self.mode_combo.setMinimumWidth(150)
        effect_row.addWidget(self.mode_combo, 1)
        effect_layout.addLayout(effect_row)

        special_row = QHBoxLayout()
        special_row.addWidget(QLabel("Special"))
        self.special_combo = QComboBox()
        self.special_combo.addItem("None", None)
        for name in SPECIALS:
            self.special_combo.addItem(display_name(name), name)
        self.special_combo.currentIndexChanged.connect(self.on_special_changed)
        special_row.addWidget(self.special_combo, 1)
        self.flash = QCheckBox("Flash text")
        self.flash.stateChanged.connect(self.update_send_enabled)
        self.flash.stateChanged.connect(self.update_preview)
        special_row.addWidget(self.flash)
        effect_layout.addLayout(special_row)
        editor_layout.addLayout(effect_layout)

        speed_row = QHBoxLayout()
        speed_row.addWidget(section_label("Speed"))
        speed_row.addWidget(QLabel("Slow"))
        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setRange(1, 5)
        self.speed_slider.setValue(3)
        self.speed_slider.valueChanged.connect(self.select_speed)
        speed_row.addWidget(self.speed_slider, 1)
        speed_row.addWidget(QLabel("Fast"))
        self.speed_value = QLabel("3 of 5")
        self.speed_value.setObjectName("muted")
        speed_row.addWidget(self.speed_value)
        editor_layout.addLayout(speed_row)

        library = QHBoxLayout()
        self.library_combo = QComboBox()
        self.library_combo.activated.connect(self.load_message)
        self.library_combo.currentIndexChanged.connect(self.update_library_actions)
        library.addWidget(self.library_combo, 1)
        save_library = QPushButton("Save Message")
        save_library.clicked.connect(self.save_message)
        library.addWidget(save_library)
        self.delete_library_button = QPushButton("Delete Saved")
        self.delete_library_button.clicked.connect(self.delete_message)
        library.addWidget(self.delete_library_button)
        editor_layout.addLayout(library)

        self.message_hint = QLabel()
        self.message_hint.setObjectName("muted")
        self.message_hint.hide()

        layout.addWidget(editor, 1)

        footer = QHBoxLayout()
        self.transmit_status = QLabel("Controller ready.")
        self.transmit_status.setObjectName("transmitStatus")
        footer.addWidget(self.transmit_status, 1)
        preview_button = QPushButton("Preview")
        preview_button.clicked.connect(self.update_preview)
        footer.addWidget(preview_button)
        save_button = QPushButton("Save Message")
        save_button.clicked.connect(self.save_message)
        footer.addWidget(save_button)
        self.clear_button = QPushButton("Clear Sign")
        self.clear_button.setObjectName("clearButton")
        self.clear_button.clicked.connect(self.clear_current_sign)
        footer.addWidget(self.clear_button)
        self.send_button = QPushButton("Send to Sign")
        self.send_button.setObjectName("sendButton")
        self.send_button.clicked.connect(self.send_current)
        footer.addWidget(self.send_button)
        layout.addLayout(footer)

        self.color_buttons["auto"].setChecked(True)
        self._sync_mode_buttons()
        return page

    def _build_pixel_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(18, 10, 18, 8)
        layout.setSpacing(8)

        heading = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("Pixel Studio")
        title.setObjectName("pageTitle")
        subtitle = QLabel("Create 7-pixel-high SMALL DOTS artwork for compatible Alpha/BetaBrite signs.")
        subtitle.setObjectName("muted")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        heading.addLayout(title_box, 1)
        self.pixel_coordinate = QLabel("x -, y -")
        self.pixel_coordinate.setObjectName("muted")
        heading.addWidget(self.pixel_coordinate)
        layout.addLayout(heading)

        self.pixel_preview = PixelPreviewWidget()
        layout.addWidget(self.pixel_preview)

        body = QSplitter(Qt.Orientation.Horizontal)
        body.setObjectName("pixelSplitter")

        editor_panel = QFrame()
        editor_panel.setObjectName("editorPanel")
        editor_layout = QVBoxLayout(editor_panel)
        editor_layout.setContentsMargins(12, 8, 12, 8)
        editor_layout.setSpacing(7)

        tools = QHBoxLayout()
        self.pixel_pencil = QToolButton()
        self.pixel_pencil.setText("Pencil")
        self.pixel_pencil.setCheckable(True)
        self.pixel_pencil.setChecked(True)
        self.pixel_pencil.clicked.connect(lambda: self.select_pixel_tool("pencil"))
        tools.addWidget(self.pixel_pencil)
        self.pixel_eraser = QToolButton()
        self.pixel_eraser.setText("Eraser")
        self.pixel_eraser.setCheckable(True)
        self.pixel_eraser.clicked.connect(lambda: self.select_pixel_tool("eraser"))
        tools.addWidget(self.pixel_eraser)
        clear_button = QPushButton("Clear")
        clear_button.clicked.connect(self.pixel_clear_frame)
        tools.addWidget(clear_button)
        fill_button = QPushButton("Fill")
        fill_button.clicked.connect(self.pixel_fill_frame)
        tools.addWidget(fill_button)
        invert_button = QPushButton("Invert")
        invert_button.clicked.connect(self.pixel_invert_frame)
        tools.addWidget(invert_button)
        flip_h = QPushButton("Flip H")
        flip_h.clicked.connect(self.pixel_flip_horizontal)
        tools.addWidget(flip_h)
        flip_v = QPushButton("Flip V")
        flip_v.clicked.connect(self.pixel_flip_vertical)
        tools.addWidget(flip_v)
        tools.addStretch(1)
        tools.addWidget(QLabel("Zoom"))
        self.pixel_zoom = QSlider(Qt.Orientation.Horizontal)
        self.pixel_zoom.setRange(8, 28)
        self.pixel_zoom.setValue(14)
        self.pixel_zoom.setFixedWidth(130)
        self.pixel_zoom.valueChanged.connect(self.pixel_zoom_changed)
        tools.addWidget(self.pixel_zoom)
        editor_layout.addLayout(tools)

        palette = QHBoxLayout()
        palette.addWidget(section_label("Palette"))
        self.pixel_color_buttons = {}
        for color in PixelColor:
            button = QToolButton()
            button.setToolTip(color.display_name)
            button.setCheckable(True)
            button.setFixedSize(26, 24)
            button.setStyleSheet(f"QToolButton {{ background: {color.hex_color}; border: 1px solid #7d878f; }}")
            button.clicked.connect(lambda checked=False, selected=color: self.select_pixel_color(selected))
            self.pixel_color_buttons[color] = button
            palette.addWidget(button)
        self.pixel_color_buttons[PixelColor.RED].setChecked(True)
        palette.addStretch(1)
        self.onion_skin = QCheckBox("Onion skin")
        self.onion_skin.stateChanged.connect(self.refresh_pixel_canvas)
        palette.addWidget(self.onion_skin)
        editor_layout.addLayout(palette)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        canvas_holder = QWidget()
        canvas_layout = QHBoxLayout(canvas_holder)
        canvas_layout.setContentsMargins(0, 0, 0, 0)
        canvas_layout.addStretch(1)
        self.pixel_canvas = PixelCanvasWidget()
        self.pixel_canvas.on_change = self.pixel_canvas_changed
        canvas_layout.addWidget(self.pixel_canvas)
        canvas_layout.addStretch(1)
        scroll.setWidget(canvas_holder)
        editor_layout.addWidget(scroll, 1)

        body.addWidget(editor_panel)

        timeline_panel = QFrame()
        timeline_panel.setObjectName("editorPanel")
        timeline_layout = QVBoxLayout(timeline_panel)
        timeline_layout.setContentsMargins(10, 8, 10, 8)
        timeline_layout.setSpacing(7)
        timeline_layout.addWidget(section_label("Frames"))
        self.pixel_timeline = QListWidget()
        self.pixel_timeline.currentRowChanged.connect(self.select_pixel_frame)
        timeline_layout.addWidget(self.pixel_timeline, 1)

        frame_actions = QGridLayout()
        add_frame = QPushButton("Add")
        add_frame.clicked.connect(self.pixel_add_frame)
        duplicate_frame = QPushButton("Duplicate")
        duplicate_frame.clicked.connect(self.pixel_duplicate_frame)
        delete_frame = QPushButton("Delete")
        delete_frame.clicked.connect(self.pixel_delete_frame)
        previous_frame = QPushButton("Previous")
        previous_frame.clicked.connect(self.pixel_previous_frame)
        next_frame = QPushButton("Next")
        next_frame.clicked.connect(self.pixel_next_frame)
        frame_actions.addWidget(add_frame, 0, 0)
        frame_actions.addWidget(duplicate_frame, 0, 1)
        frame_actions.addWidget(delete_frame, 1, 0)
        frame_actions.addWidget(previous_frame, 2, 0)
        frame_actions.addWidget(next_frame, 2, 1)
        timeline_layout.addLayout(frame_actions)

        duration_row = QHBoxLayout()
        duration_row.addWidget(QLabel("Duration"))
        self.pixel_duration = QSpinBox()
        self.pixel_duration.setRange(50, 10000)
        self.pixel_duration.setSingleStep(50)
        self.pixel_duration.setSuffix(" ms")
        self.pixel_duration.valueChanged.connect(self.pixel_duration_changed)
        duration_row.addWidget(self.pixel_duration, 1)
        timeline_layout.addLayout(duration_row)

        play_row = QHBoxLayout()
        play = QPushButton("Play")
        play.clicked.connect(self.pixel_play)
        pause = QPushButton("Pause")
        pause.clicked.connect(self.pixel_pause)
        stop = QPushButton("Stop")
        stop.clicked.connect(self.pixel_stop)
        play_row.addWidget(play)
        play_row.addWidget(pause)
        play_row.addWidget(stop)
        timeline_layout.addLayout(play_row)

        file_grid = QGridLayout()
        new_button = QPushButton("New")
        new_button.clicked.connect(self.pixel_new_document)
        open_button = QPushButton("Open")
        open_button.clicked.connect(self.pixel_open_dialog)
        save_button = QPushButton("Save")
        save_button.clicked.connect(self.pixel_save)
        save_as_button = QPushButton("Save As")
        save_as_button.clicked.connect(self.pixel_save_as_dialog)
        file_grid.addWidget(new_button, 0, 0)
        file_grid.addWidget(open_button, 0, 1)
        file_grid.addWidget(save_button, 1, 0)
        file_grid.addWidget(save_as_button, 1, 1)
        timeline_layout.addLayout(file_grid)

        self.pixel_send_button = QPushButton("Send to Sign")
        self.pixel_send_button.setObjectName("sendButton")
        self.pixel_send_button.clicked.connect(self.pixel_send_to_sign)
        timeline_layout.addWidget(self.pixel_send_button)
        self.pixel_status = QLabel("Pixel Studio ready.")
        self.pixel_status.setObjectName("transmitStatus")
        self.pixel_status.setWordWrap(True)
        timeline_layout.addWidget(self.pixel_status)

        body.addWidget(timeline_panel)
        body.setStretchFactor(0, 1)
        body.setStretchFactor(1, 0)
        body.setSizes([760, 250])
        layout.addWidget(body, 1)

        self.refresh_pixel_timeline()
        self.refresh_pixel_canvas()
        return page

    def _build_live_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(18, 10, 18, 8)
        layout.setSpacing(8)

        heading = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("Live Mode")
        title.setObjectName("pageTitle")
        subtitle = QLabel("Run generated framebuffer sources locally, with hardware streaming gated by protocol safety.")
        subtitle.setObjectName("muted")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        heading.addLayout(title_box, 1)
        self.live_output_badge = QLabel("VIRTUAL PREVIEW ONLY")
        self.live_output_badge.setObjectName("connectionBadge")
        heading.addWidget(self.live_output_badge)
        layout.addLayout(heading)

        self.live_preview = PixelPreviewWidget()
        layout.addWidget(self.live_preview)

        body = QSplitter(Qt.Orientation.Horizontal)
        controls_panel = QFrame()
        controls_panel.setObjectName("editorPanel")
        controls = QVBoxLayout(controls_panel)
        controls.setContentsMargins(12, 8, 12, 8)
        controls.setSpacing(7)

        source_row = QHBoxLayout()
        source_row.addWidget(QLabel("Source"))
        self.live_source_combo = QComboBox()
        self.live_source_combo.addItem("Original tiny runner", "dino")
        source_row.addWidget(self.live_source_combo, 1)
        controls.addLayout(source_row)

        preset_row = QHBoxLayout()
        preset_row.addWidget(QLabel("Preset"))
        self.live_preset_combo = QComboBox()
        self.live_preset_combo.addItem("Virtual", "virtual")
        self.live_preset_combo.addItem("Safe Hardware", "safe-hardware")
        self.live_preset_combo.addItem("Benchmarked", "benchmarked")
        self.live_preset_combo.currentIndexChanged.connect(self.live_preset_changed)
        preset_row.addWidget(self.live_preset_combo, 1)
        controls.addLayout(preset_row)

        fps_row = QHBoxLayout()
        fps_row.addWidget(QLabel("Target sign FPS"))
        self.live_fps = QSpinBox()
        self.live_fps.setRange(1, 10)
        self.live_fps.setValue(2)
        fps_row.addWidget(self.live_fps, 1)
        controls.addLayout(fps_row)

        button_row = QHBoxLayout()
        self.live_start_button = QPushButton("Start")
        self.live_start_button.clicked.connect(self.live_start)
        self.live_pause_button = QPushButton("Pause")
        self.live_pause_button.clicked.connect(self.live_pause_resume)
        self.live_stop_button = QPushButton("Stop")
        self.live_stop_button.clicked.connect(self.live_stop)
        button_row.addWidget(self.live_start_button)
        button_row.addWidget(self.live_pause_button)
        button_row.addWidget(self.live_stop_button)
        controls.addLayout(button_row)

        benchmark_row = QHBoxLayout()
        self.live_virtual_benchmark_button = QPushButton("Run Virtual Benchmark")
        self.live_virtual_benchmark_button.clicked.connect(self.live_run_virtual_benchmark)
        self.live_physical_benchmark_button = QPushButton("Check Hardware Benchmark")
        self.live_physical_benchmark_button.clicked.connect(self.live_check_physical_benchmark)
        benchmark_row.addWidget(self.live_virtual_benchmark_button)
        benchmark_row.addWidget(self.live_physical_benchmark_button)
        controls.addLayout(benchmark_row)

        self.live_status = QLabel("Live Mode ready. Hardware streaming is disabled until a safe volatile update path is proven.")
        self.live_status.setObjectName("transmitStatus")
        self.live_status.setWordWrap(True)
        controls.addWidget(self.live_status)
        controls.addStretch(1)
        body.addWidget(controls_panel)

        metrics_panel = QFrame()
        metrics_panel.setObjectName("editorPanel")
        metrics_layout = QGridLayout(metrics_panel)
        metrics_layout.setContentsMargins(12, 8, 12, 8)
        metrics_layout.setHorizontalSpacing(12)
        metrics_layout.setVerticalSpacing(7)
        self.live_metric_labels = {}
        for row, key in enumerate(
            (
                "state",
                "connection",
                "actual_fps",
                "rendered",
                "transmitted",
                "dropped",
                "coalesced",
                "avg_latency",
                "latest_latency",
                "errors",
            )
        ):
            metrics_layout.addWidget(QLabel(display_name(key)), row, 0)
            value = QLabel("-")
            value.setObjectName("muted")
            self.live_metric_labels[key] = value
            metrics_layout.addWidget(value, row, 1)
        body.addWidget(metrics_panel)
        body.setStretchFactor(0, 1)
        body.setStretchFactor(1, 1)
        layout.addWidget(body, 1)

        self.live_reset_source()
        self.live_update_controls()
        return page

    def current_pixel_animation_frame(self):
        return self.pixel_document.frames[self.pixel_frame_index]

    def current_pixel_frame(self):
        return self.current_pixel_animation_frame().frame

    def pixel_mark_dirty(self, dirty: bool = True) -> None:
        self.pixel_dirty = dirty
        self.update_pixel_status()

    def update_pixel_status(self, message: str | None = None) -> None:
        if not hasattr(self, "pixel_status"):
            return
        path = str(self.pixel_document_path) if self.pixel_document_path else "Unsaved .bbpixel"
        dirty = "modified" if self.pixel_dirty else "saved"
        default = f"{self.pixel_document.title} - {self.pixel_document.width}x{self.pixel_document.height} - {dirty} - {path}"
        self.pixel_status.setText(message or default)
        if hasattr(self, "pixel_send_button"):
            self.pixel_send_button.setEnabled(not self.busy and self.connection_ready)

    def refresh_pixel_timeline(self) -> None:
        if not hasattr(self, "pixel_timeline"):
            return
        self.pixel_timeline.blockSignals(True)
        self.pixel_timeline.clear()
        for index, animation_frame in enumerate(self.pixel_document.frames):
            self.pixel_timeline.addItem(f"Frame {index + 1} - {animation_frame.duration_ms} ms")
        self.pixel_frame_index = min(self.pixel_frame_index, len(self.pixel_document.frames) - 1)
        self.pixel_timeline.setCurrentRow(self.pixel_frame_index)
        self.pixel_timeline.blockSignals(False)
        self.refresh_pixel_canvas()

    def refresh_pixel_canvas(self) -> None:
        if not hasattr(self, "pixel_canvas"):
            return
        onion_frame = None
        if self.onion_skin.isChecked() and self.pixel_frame_index > 0:
            onion_frame = self.pixel_document.frames[self.pixel_frame_index - 1].frame
        frame = self.current_pixel_frame()
        self.pixel_canvas.selected_color = self.pixel_color
        self.pixel_canvas.tool = self.pixel_tool
        self.pixel_canvas.set_frame(frame, onion_frame=onion_frame)
        self.pixel_preview.set_frame(frame)
        self.pixel_duration.blockSignals(True)
        self.pixel_duration.setValue(self.current_pixel_animation_frame().duration_ms)
        self.pixel_duration.blockSignals(False)
        self.pixel_coordinate.setText(f"{frame.width} x {frame.height} pixels")
        self.update_pixel_status()

    def pixel_canvas_changed(self, x: int, y: int) -> None:
        self.pixel_coordinate.setText(f"x {x}, y {y}")
        self.pixel_preview.set_frame(self.current_pixel_frame())
        self.pixel_mark_dirty()

    def select_pixel_tool(self, tool: str) -> None:
        self.pixel_tool = tool
        self.pixel_pencil.setChecked(tool == "pencil")
        self.pixel_eraser.setChecked(tool == "eraser")
        self.pixel_canvas.tool = tool

    def select_pixel_color(self, color: PixelColor) -> None:
        self.pixel_color = color
        for candidate, button in self.pixel_color_buttons.items():
            button.setChecked(candidate is color)
        self.pixel_canvas.selected_color = color
        if color is PixelColor.OFF:
            self.select_pixel_tool("eraser")
        else:
            self.select_pixel_tool("pencil")

    def pixel_zoom_changed(self, value: int) -> None:
        self.pixel_canvas.set_zoom(value)

    def pixel_clear_frame(self) -> None:
        self.current_pixel_frame().clear()
        self.pixel_mark_dirty()
        self.refresh_pixel_canvas()

    def pixel_fill_frame(self) -> None:
        self.current_pixel_frame().fill(self.pixel_color)
        self.pixel_mark_dirty()
        self.refresh_pixel_canvas()

    def pixel_invert_frame(self) -> None:
        self.current_pixel_frame().invert(self.pixel_color if self.pixel_color is not PixelColor.OFF else PixelColor.RED)
        self.pixel_mark_dirty()
        self.refresh_pixel_canvas()

    def pixel_flip_horizontal(self) -> None:
        self.current_pixel_frame().flip_horizontal()
        self.pixel_mark_dirty()
        self.refresh_pixel_canvas()

    def pixel_flip_vertical(self) -> None:
        self.current_pixel_frame().flip_vertical()
        self.pixel_mark_dirty()
        self.refresh_pixel_canvas()

    def select_pixel_frame(self, index: int) -> None:
        if index < 0 or index >= len(self.pixel_document.frames):
            return
        self.pixel_frame_index = index
        self.refresh_pixel_canvas()

    def pixel_add_frame(self) -> None:
        self.pixel_frame_index = self.pixel_document.animation.add_frame()
        self.pixel_mark_dirty()
        self.refresh_pixel_timeline()

    def pixel_duplicate_frame(self) -> None:
        self.pixel_frame_index = self.pixel_document.animation.duplicate_frame(self.pixel_frame_index)
        self.pixel_mark_dirty()
        self.refresh_pixel_timeline()

    def pixel_delete_frame(self) -> None:
        try:
            self.pixel_document.animation.delete_frame(self.pixel_frame_index)
        except PixelDocumentError as exc:
            self.update_pixel_status(str(exc))
            return
        self.pixel_frame_index = max(0, min(self.pixel_frame_index, len(self.pixel_document.frames) - 1))
        self.pixel_mark_dirty()
        self.refresh_pixel_timeline()

    def pixel_previous_frame(self) -> None:
        self.pixel_timeline.setCurrentRow(max(0, self.pixel_frame_index - 1))

    def pixel_next_frame(self) -> None:
        self.pixel_timeline.setCurrentRow(min(len(self.pixel_document.frames) - 1, self.pixel_frame_index + 1))

    def pixel_duration_changed(self, value: int) -> None:
        self.current_pixel_animation_frame().duration_ms = int(value)
        self.pixel_mark_dirty()
        self.refresh_pixel_timeline()

    def pixel_play(self) -> None:
        self.pixel_playing = True
        self.pixel_timer.start(self.current_pixel_animation_frame().duration_ms)
        self.update_pixel_status("Pixel animation preview playing.")

    def pixel_pause(self) -> None:
        self.pixel_playing = False
        self.pixel_timer.stop()
        self.update_pixel_status("Pixel animation preview paused.")

    def pixel_stop(self) -> None:
        self.pixel_playing = False
        self.pixel_timer.stop()
        self.pixel_timeline.setCurrentRow(0)
        self.update_pixel_status("Pixel animation preview stopped.")

    def pixel_playback_tick(self) -> None:
        next_index = self.pixel_document.animation.next_index(self.pixel_frame_index)
        if next_index == self.pixel_frame_index and not self.pixel_document.animation.loop:
            self.pixel_pause()
            return
        self.pixel_frame_index = next_index
        self.pixel_timeline.blockSignals(True)
        self.pixel_timeline.setCurrentRow(next_index)
        self.pixel_timeline.blockSignals(False)
        self.refresh_pixel_canvas()
        self.pixel_timer.start(self.current_pixel_animation_frame().duration_ms)

    def pixel_new_document(self) -> None:
        self.pixel_pause()
        self.pixel_document = PixelDocument.new(width=DEFAULT_WIDTH, height=DEFAULT_HEIGHT)
        self.pixel_document_path = None
        self.pixel_frame_index = 0
        self.pixel_dirty = False
        self.refresh_pixel_timeline()
        self.update_pixel_status("New pixel document created.")

    def pixel_open_document(self, path) -> None:
        try:
            self.pixel_document = PixelDocument.load(path)
        except (OSError, PixelDocumentError) as exc:
            self.update_pixel_status(f"Could not open pixel document: {exc}")
            return
        self.pixel_pause()
        self.pixel_document_path = path
        self.pixel_frame_index = 0
        self.pixel_dirty = False
        self.refresh_pixel_timeline()
        self.update_pixel_status(f"Opened {path}.")

    def pixel_save_document(self, path) -> None:
        try:
            self.pixel_document.save(path)
        except OSError as exc:
            self.update_pixel_status(f"Could not save pixel document: {exc}")
            return
        self.pixel_document_path = path
        self.pixel_dirty = False
        self.update_pixel_status(f"Saved {path}.")

    def pixel_open_dialog(self) -> None:
        path, _filter = QFileDialog.getOpenFileName(self, "Open pixel document", "", "BetaBrite Pixel Art (*.bbpixel);;JSON (*.json)")
        if path:
            self.pixel_open_document(path)

    def pixel_save(self) -> None:
        if self.pixel_document_path:
            self.pixel_save_document(self.pixel_document_path)
        else:
            self.pixel_save_as_dialog()

    def pixel_save_as_dialog(self) -> None:
        path, _filter = QFileDialog.getSaveFileName(self, "Save pixel document", "", "BetaBrite Pixel Art (*.bbpixel)")
        if path:
            if not str(path).lower().endswith(".bbpixel"):
                path = f"{path}.bbpixel"
            if os.path.exists(path):
                answer = QMessageBox.question(
                    self,
                    "Replace pixel document?",
                    "A pixel document already exists at this location. Replace it?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No,
                )
                if answer != QMessageBox.StandardButton.Yes:
                    self.update_pixel_status("Save As canceled; existing file was not replaced.")
                    return
            self.pixel_save_document(path)

    def pixel_send_to_sign(self) -> None:
        if self.busy:
            return
        if not self.connection_ready:
            self.update_pixel_status("Connect to a serial adapter before sending pixel art.")
            self.update_send_enabled()
            return
        frame = self.current_pixel_frame().duplicate()
        port = self.selected_port() or AUTO_PORT
        self.start_operation(lambda: transmit_graphic(port, frame))

    def live_reset_source(self) -> None:
        self.live_source = DinoRunnerSource()
        frame = self.live_source.render()
        if hasattr(self, "live_preview"):
            self.live_preview.set_frame(frame)

    def live_preset_changed(self, *_args) -> None:
        preset = self.live_preset_combo.currentData()
        if preset == "virtual":
            self.live_fps.setValue(2)
            self.live_status.setText("Virtual preset selected. Preview runs locally without sign output.")
        elif preset == "safe-hardware":
            self.live_fps.setValue(2)
            self.live_status.setText("Safe Hardware preset is blocked: no volatile live pixel update path is proven.")
        elif preset == "benchmarked":
            recommended = int(getattr(self.live_report, "recommended_fps", 0) or 0)
            if recommended > 0:
                self.live_fps.setValue(max(1, min(10, recommended)))
                self.live_status.setText(f"Benchmarked preset loaded: {recommended} FPS.")
            else:
                self.live_status.setText("Run a benchmark before using the Benchmarked preset.")
        self.live_update_controls()

    def live_start(self) -> None:
        if self.live_scheduler and self.live_scheduler.running:
            return
        self.live_reset_source()
        self.live_scheduler = LiveScheduler(
            self.live_source,
            preview_fps=30,
            target_fps=self.live_fps.value(),
        )
        frame = self.live_scheduler.start()
        self.live_preview.set_frame(frame)
        self.live_timer.start()
        self.live_status.setText("Dino running in virtual preview. Space or Up jumps; R restarts; Escape stops.")
        self.live_update_controls()

    def live_pause_resume(self) -> None:
        if not self.live_scheduler or not self.live_scheduler.running:
            return
        if self.live_scheduler.paused:
            self.live_scheduler.resume()
            self.live_status.setText("Live Mode resumed.")
        else:
            self.live_scheduler.pause()
            self.live_status.setText("Live Mode paused.")
        self.live_update_controls()

    def live_stop(self) -> None:
        if self.live_scheduler:
            self.live_scheduler.stop()
        self.live_timer.stop()
        self.live_status.setText("Live Mode stopped.")
        self.live_update_controls()

    def live_tick(self) -> None:
        if not self.live_scheduler:
            return
        frame = self.live_scheduler.tick()
        if frame:
            self.live_preview.set_frame(frame)
        if not self.live_scheduler.running:
            self.live_timer.stop()
        self.live_update_controls()

    def live_handle_input(self, action: str) -> None:
        if self.live_scheduler and self.live_scheduler.running:
            self.live_scheduler.handle_input(action)
            if action == "restart":
                self.live_status.setText("Dino restarted.")

    def live_run_virtual_benchmark(self) -> None:
        self.live_report = run_virtual_benchmark_suite(duration_seconds=0.5)
        self.live_status.setText(
            f"Virtual benchmark complete. Recommended simulated rate: {self.live_report.recommended_fps:.1f} FPS."
        )
        self.live_update_controls()

    def live_check_physical_benchmark(self) -> None:
        port = self.selected_port() or "not connected"
        self.live_report = physical_live_benchmark_blocked_report(port)
        self.live_status.setText(self.live_report.safety_note)
        self.live_update_controls()

    def live_update_controls(self) -> None:
        if not hasattr(self, "live_start_button"):
            return
        scheduler = self.live_scheduler
        running = bool(scheduler and scheduler.running)
        paused = bool(scheduler and scheduler.paused)
        self.live_start_button.setEnabled(not running)
        self.live_pause_button.setEnabled(running)
        self.live_pause_button.setText("Resume" if paused else "Pause")
        self.live_stop_button.setEnabled(running)
        self.live_fps.setEnabled(not running)
        self.live_source_combo.setEnabled(not running)
        self.live_output_badge.setText("STREAMING TO SIGN" if scheduler and scheduler.streaming_to_sign else "VIRTUAL PREVIEW ONLY")
        self.live_output_badge.setStyleSheet(
            "QLabel#connectionBadge { color: #a97014; background: #fff6de; }"
            if not (scheduler and scheduler.streaming_to_sign)
            else "QLabel#connectionBadge { color: #1f8d4d; background: #e9f6ee; }"
        )
        stats = scheduler.statistics if scheduler else None
        self.live_metric_labels["state"].setText("Paused" if paused else ("Running" if running else "Stopped"))
        blocked_report = bool(
            self.live_report
            and getattr(self.live_report, "results", None)
            and self.live_report.results[0].status == "blocked"
        )
        self.live_metric_labels["connection"].setText(
            "Hardware blocked" if blocked_report else ("Ready" if self.connection_ready else "No ready sign")
        )
        elapsed_frames = stats.frames_rendered if stats else 0
        self.live_metric_labels["actual_fps"].setText("30 preview / 0 sign" if running else "-")
        self.live_metric_labels["rendered"].setText(str(elapsed_frames))
        self.live_metric_labels["transmitted"].setText(str(stats.frames_transmitted if stats else 0))
        self.live_metric_labels["dropped"].setText(str(stats.frames_dropped if stats else 0))
        self.live_metric_labels["coalesced"].setText(str(stats.frames_coalesced if stats else 0))
        self.live_metric_labels["avg_latency"].setText(f"{stats.average_transport_ms:.2f} ms" if stats else "0.00 ms")
        self.live_metric_labels["latest_latency"].setText(f"{stats.latest_transport_ms:.2f} ms" if stats else "0.00 ms")
        self.live_metric_labels["errors"].setText(str(stats.errors if stats else 0))

    def _font_controls(self) -> QVBoxLayout:
        layout = QVBoxLayout()
        layout.setSpacing(5)
        layout.addWidget(section_label("Font"))
        row = QHBoxLayout()
        row.setSpacing(10)
        self.font_group = QButtonGroup(self)
        self.font_group.setExclusive(True)
        for value, label in (
            ("normal", "Normal"),
            ("wide", "Wide"),
            ("double-wide", "Double Wide"),
            ("small", "Small"),
            ("large", "Large"),
        ):
            button = QRadioButton(label)
            button.clicked.connect(lambda checked=False, mode=value: self.select_font_mode(mode))
            self.font_group.addButton(button)
            row.addWidget(button)
            if value == "normal":
                button.setChecked(True)
                self.normal_font_button = button
            if value == "wide":
                self.wide = button
        row.addStretch(1)
        layout.addLayout(row)
        return layout

    def _alignment_controls(self) -> QVBoxLayout:
        layout = QVBoxLayout()
        layout.setSpacing(5)
        layout.addWidget(section_label("Alignment"))
        row = QHBoxLayout()
        row.setSpacing(0)
        self.alignment_group = QButtonGroup(self)
        self.alignment_group.setExclusive(True)
        for value, label in (("left", "Left"), ("center", "Center"), ("right", "Right")):
            button = QToolButton()
            button.setText(label)
            button.setCheckable(True)
            button.clicked.connect(lambda checked=False, alignment=value: self.select_alignment(alignment))
            self.alignment_group.addButton(button)
            row.addWidget(button)
            if value == "center":
                button.setChecked(True)
        layout.addLayout(row)
        return layout

    def _placeholder_page(self, title: str, text: str) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(18, 14, 18, 12)
        heading = QLabel(title)
        heading.setObjectName("pageTitle")
        body = QLabel(text)
        body.setObjectName("muted")
        body.setWordWrap(True)
        layout.addWidget(heading)
        layout.addWidget(body)
        layout.addStretch(1)
        return page

    def _diagnostics_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(18, 14, 18, 12)
        title = QLabel("Diagnostics")
        title.setObjectName("pageTitle")
        self.diagnostics_text = QPlainTextEdit()
        self.diagnostics_text.setReadOnly(True)
        self.diagnostics_text.setPlainText("Diagnostics appear here after device checks. Logs: " + str(log_path()))
        layout.addWidget(title)
        layout.addWidget(self.diagnostics_text, 1)
        return page

    def _hardware_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(18, 14, 18, 12)
        title = QLabel("Hardware Setup")
        title.setObjectName("pageTitle")
        body = QLabel(
            "Serial settings: 9600 baud, 7 data bits, even parity, 1 stop bit, DTR disabled. "
            "Use Refresh Devices after connecting the USB serial adapter."
        )
        body.setWordWrap(True)
        body.setObjectName("muted")
        manual = QPushButton("Manual Port...")
        manual.clicked.connect(self.choose_manual_port)
        remember = QPushButton("Use Selected Adapter")
        remember.clicked.connect(self.remember_selected)
        save = QPushButton("Save Sign As...")
        save.clicked.connect(self.save_sign)
        layout.addWidget(title)
        layout.addWidget(body)
        layout.addWidget(manual)
        layout.addWidget(remember)
        layout.addWidget(save)
        layout.addStretch(1)
        return page

    def _settings_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(18, 14, 18, 12)
        title = QLabel("Application Settings")
        title.setObjectName("pageTitle")
        install_text = QLabel("Saved adapter, signs, drafts, and messages are stored in your user configuration folder.")
        install_text.setWordWrap(True)
        install_text.setObjectName("muted")
        layout.addWidget(title)
        layout.addWidget(install_text)
        if sys.platform.startswith("linux") and os.environ.get("APPIMAGE"):
            install_button = QPushButton("Install in application menu")
            install_button.clicked.connect(self.install_desktop)
            layout.addWidget(install_button)
        layout.addStretch(1)
        return page

    def _build_status_bar(self) -> None:
        status = QStatusBar()
        self.setStatusBar(status)
        self.footer_connection = QLabel("Disconnected")
        self.footer_port = QLabel("No port")
        self.footer_address = QLabel("Address 00")
        self.footer_ready = QLabel("Ready")
        status.addWidget(self.footer_connection)
        status.addWidget(self.footer_port)
        status.addWidget(self.footer_address)
        status.addPermanentWidget(self.footer_ready)

    def _apply_style(self) -> None:
        self.setStyleSheet(
            """
            QMainWindow, QWidget {
                background: #f3f4f5;
                color: #32383d;
                font-size: 12px;
            }
            QMenuBar {
                background: #f9fafb;
                border-bottom: 1px solid #d5d9dd;
            }
            QMenuBar::item {
                padding: 4px 10px;
            }
            QToolBar#mainToolbar {
                background: #f4f6f7;
                border-bottom: 1px solid #cfd5da;
                spacing: 4px;
                padding: 3px 7px;
            }
            QFrame#sidebar {
                background: #e6eaee;
                border-right: 1px solid #cbd2d8;
            }
            QFrame#deviceCard, QFrame#editorPanel {
                background: #fbfcfd;
                border: 1px solid #cfd5da;
            }
            QLabel#pageTitle {
                font-size: 17px;
                font-weight: 600;
            }
            QLabel#panelTitle {
                font-size: 15px;
                font-weight: 600;
            }
            QLabel#section {
                color: #4f5962;
                font-weight: 600;
            }
            QLabel#muted, QLabel#transmitStatus {
                color: #6d767f;
            }
            QLabel#deviceName {
                font-weight: 600;
            }
            QLabel#connectionBadge {
                font-weight: 600;
                padding: 2px 0;
            }
            QListWidget#navigation {
                background: #e6eaee;
                border: 0;
                outline: 0;
            }
            QListWidget#navigation::item {
                padding: 4px 7px;
            }
            QListWidget#navigation::item:selected {
                color: #1f6fb2;
                background: #d6e9fa;
            }
            QLineEdit, QComboBox, QPlainTextEdit {
                background: #ffffff;
                border: 1px solid #bfc8d0;
                padding: 5px 7px;
                selection-background-color: #2d82c7;
            }
            QLineEdit#messageEntry {
                min-height: 42px;
                font-size: 13px;
            }
            QPushButton, QToolButton {
                background: #f8fafb;
                border: 1px solid #bfc8d0;
                padding: 5px 10px;
            }
            QPushButton:hover, QToolButton:hover {
                background: #eef4fa;
            }
            QPushButton:disabled, QToolButton:disabled {
                color: #9aa3aa;
                background: #edf0f2;
            }
            QToolButton:checked {
                background: #d9ebfb;
                border-color: #7aaed8;
                color: #195f98;
            }
            QPushButton#sendButton {
                background: #1f6fb2;
                color: #ffffff;
                border-color: #185d96;
                font-weight: 600;
                min-width: 118px;
            }
            QPushButton#sendButton:disabled {
                background: #b8c6d1;
                border-color: #aeb8c1;
                color: #f5f7f8;
            }
            QPushButton#clearButton {
                color: #b12a2a;
            }
            QFrame#signPreview {
                background: #f3f4f5;
                border: 1px solid #cfd5da;
            }
            QStatusBar {
                background: #eef1f3;
                border-top: 1px solid #cbd2d8;
                color: #59636b;
            }
            """
        )

    def _show_page(self, row: int) -> None:
        self.pages.setCurrentIndex(max(0, row))
        if row == 5:
            self._refresh_diagnostics_page()

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
            self.adapter_combo.addItem("No adapters")
            self.adapter_combo.setEnabled(False)
            self.remember_button.setEnabled(False)
        else:
            for option in self.options:
                self.adapter_combo.addItem(option.port)

            index = default_adapter_index(self.options)
            if previous_port is None:
                from .devices import DeviceDiscoveryError, resolve_device

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
            wide=self.selected_font_mode in {"wide", "double-wide"},
        )

    def set_connection_view(self, diagnostic) -> None:
        view = connection_view(diagnostic)
        self.connection_ready = view.can_send
        self.status_badge.setText(view.headline.replace("● ", ""))
        self.status_detail.setText(self._sidebar_detail(view.detail))

        pieces = []
        if view.port:
            pieces.append(view.port)
        source = getattr(diagnostic, "source", None)
        if source:
            pieces.append(source)
        self.status_meta.setText(" / ".join(pieces))

        colors = {
            "online": ("#1f8d4d", "#e9f6ee"),
            "selected": ("#a97014", "#fff6de"),
            "offline": ("#b23c3c", "#fae9e9"),
        }
        foreground, background = colors[view.tone]
        self.status_badge.setStyleSheet(
            f"QLabel#connectionBadge {{ color: {foreground}; background: {background}; }}"
        )

        self.footer_connection.setText(view.headline.replace("● ", ""))
        self.footer_port.setText(view.port or "No port")
        self.footer_ready.setText("Ready" if view.can_send else "Not ready")
        self.update_send_enabled()
        self._refresh_diagnostics_page()

    def _sidebar_detail(self, detail: str) -> str:
        if ". " in detail:
            return detail.split(". ", 1)[0] + "."
        return detail

    def update_send_enabled(self, *_args) -> None:
        if not hasattr(self, "send_button"):
            return
        enabled = not self.busy and can_transmit(self.connection_ready, self.current_draft())
        self.send_button.setEnabled(enabled)
        self.send_action.setEnabled(enabled)
        clear_enabled = not self.busy and self.connection_ready
        self.clear_button.setEnabled(clear_enabled)
        self.clear_action.setEnabled(clear_enabled)
        if hasattr(self, "connect_action"):
            self.connect_action.setEnabled(not self.busy)
            self.refresh_action.setEnabled(not self.busy)
            self.disconnect_action.setEnabled(not self.busy)
            self.remember_adapter_action.setEnabled(not self.busy and bool(self.selected_port()))
            self.forget_adapter_action.setEnabled(not self.busy)
        if hasattr(self, "pixel_send_button"):
            self.pixel_send_button.setEnabled(not self.busy and self.connection_ready)
        if hasattr(self, "live_start_button"):
            self.live_update_controls()
        text = self.message.text()
        suffix = " - Non-ASCII characters display as ?" if not text.isascii() else ""
        self.message_hint.setText(f"{len(text)} characters{suffix}")
        self.character_count.setText(f"{len(text)} / 80 characters")

    def update_preview(self, *_args) -> None:
        if not hasattr(self, "preview"):
            return
        self.preview.set_preview(
            message=self.message.text(),
            color_name=self.selected_color,
            alignment=self.selected_alignment,
            font_mode=self.selected_font_mode,
        )

    def refresh_connection(self, *, active: bool = False, quiet: bool = False) -> None:
        if self.busy:
            return
        if self.active_sign:
            from .devices import DeviceDiscoveryError, resolve_device

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
            diagnostic = ConnectionDiagnostic(
                state="port-not-found",
                message="The adapter is disconnected. Reconnect it and click Refresh Devices.",
                port=diagnostic.port,
            )

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
                f"{port_label} / {display_diagnostic.state.upper()} / {display_diagnostic.message}"
            )

    def refresh_devices(self) -> None:
        if self.busy:
            return
        previous_port = self.selected_port()
        self.populate_adapters()
        current_port = self.selected_port()
        if previous_port and current_port != previous_port:
            self.last_ready_port = None
        self.refresh_connection(active=False)

    def connect_selected(self) -> None:
        if self.busy:
            return
        self.refresh_connection(active=True)

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
        if hasattr(self, "more_color_combo"):
            self.more_color_combo.blockSignals(True)
            self.more_color_combo.setCurrentIndex(self.more_color_combo.findData(name))
            self.more_color_combo.blockSignals(False)
        self.update_send_enabled()
        self.update_preview()

    def _select_more_color(self, *_args) -> None:
        color_name = self.more_color_combo.currentData()
        if color_name:
            self.select_color(color_name)

    def select_speed(self, level: int) -> None:
        self.selected_speed = int(level)
        self.speed_value.setText(f"{self.selected_speed} of 5")
        self.update_send_enabled()

    def select_alignment(self, alignment: str) -> None:
        self.selected_alignment = alignment
        self.update_preview()
        self.transmit_status.setText(
            "Preview alignment updated. The sign transmission uses the established fill positioning."
        )

    def select_font_mode(self, mode: str) -> None:
        self.selected_font_mode = mode
        self.update_send_enabled()
        self.update_preview()
        if mode in {"small", "large"}:
            self.transmit_status.setText(
                f"{display_name(mode)} is preview-only; transmitted text uses the supported BetaBrite font."
            )
        elif mode == "double-wide":
            self.transmit_status.setText(
                "Double Wide previews wider text; transmission uses the supported wide-text command."
            )

    def select_mode(self, mode: str) -> None:
        index = self.mode_combo.findData(mode)
        if index >= 0:
            self.mode_combo.setCurrentIndex(index)
        self._sync_mode_buttons()

    def _sync_mode_buttons(self, *_args) -> None:
        mode = self.mode_combo.currentData()
        for name, button in self.mode_buttons.items():
            button.setChecked(name == mode)

    def on_special_changed(self, *_args) -> None:
        special_selected = self.special_combo.currentData() is not None
        self.mode_combo.setEnabled(not special_selected)
        for button in self.mode_buttons.values():
            button.setEnabled(not special_selected)
        self.update_send_enabled()
        self.update_preview()

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

    def disconnect_selected(self) -> None:
        self.last_ready_port = None
        port = self.selected_port()
        state = "selected" if port else "no-adapter"
        message = "Adapter selected. Click Connect before sending." if port else "No serial adapter is selected."
        self.set_connection_view(ConnectionDiagnostic(state=state, message=message, port=port))
        self.transmit_status.setText("Disconnected from the selected adapter.")

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

    def clear_current_sign(self) -> None:
        if self.busy or not self.connection_ready:
            return
        port = self.selected_port() or AUTO_PORT
        self.start_operation(lambda: clear_sign(port))

    def start_operation(self, callback):
        if self.busy:
            return
        self.busy = True
        self.update_send_enabled()
        for widget in (self.adapter_combo, self.refresh_button, self.remember_button, self.forget_button, self.sign_combo):
            widget.setEnabled(False)
        self.transmit_status.setText("Working...")
        self.operation = Operation(callback, self)
        self.operation.finished.connect(self.operation_finished)
        self.operation.start()

    def operation_finished(self):
        result = self.operation.result
        self.operation.deleteLater()
        self.operation = None
        self.busy = False
        for widget in (self.adapter_combo, self.refresh_button, self.remember_button, self.forget_button, self.sign_combo):
            widget.setEnabled(True)
        self.last_ready_port = result.port if result.ready else None
        self.set_connection_view(result)
        self.transmit_status.setText(result.message)
        if result.source == "graphics" and hasattr(self, "pixel_status"):
            self.pixel_status.setText(result.message)
        self.update_library_actions()
        if result.ready and result.source == "transmit":
            current = load_settings()
            recent = [self.sent_draft] + [item for item in current.recent_messages if item != self.sent_draft]
            self.persist(replace(current, draft=self.sent_draft, recent_messages=recent[:20]))
            self.refresh_library()

    def settings_error(self):
        logging.getLogger(__name__).exception("Could not save preferences")
        self.transmit_status.setText(
            "Could not save preferences. Check free disk space and access to your configuration folder. See Diagnostics."
        )

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
        self.more_color_combo.setCurrentIndex(self.more_color_combo.findData(draft.color_name))
        self.selected_speed = draft.speed_level
        self.speed_slider.setValue(draft.speed_level)
        self.mode_combo.setCurrentIndex(self.mode_combo.findData(draft.mode_name))
        self.special_combo.setCurrentIndex(self.special_combo.findData(draft.special_name))
        self.flash.setChecked(draft.flash)
        if draft.wide:
            self.wide.setChecked(True)
            self.selected_font_mode = "wide"
        else:
            self.normal_font_button.setChecked(True)
            self.selected_font_mode = "normal"
        self.update_send_enabled()
        self.update_preview()

    def refresh_library(self):
        current = load_settings()
        self.library_combo.clear()
        self.library_combo.addItem("Saved and recent messages...", None)
        for name, draft in current.saved_messages.items():
            self.library_combo.addItem(f"Saved: {name}", (name, draft))
        for draft in current.recent_messages:
            self.library_combo.addItem(f"Recent: {draft['message'][:50] or draft.get('special_name')}", (None, draft))
        self.update_library_actions()

    def update_library_actions(self, *_args) -> None:
        if not hasattr(self, "library_combo"):
            return
        value = self.library_combo.currentData()
        can_load = bool(value)
        can_delete = bool(value and value[0])
        if hasattr(self, "load_action"):
            self.load_action.setEnabled(can_load)
        if hasattr(self, "delete_library_button"):
            self.delete_library_button.setEnabled(can_delete)
            self.delete_library_button.setToolTip(
                "" if can_delete else "Only named saved messages can be deleted; recent messages are kept automatically."
            )

    def load_message(self):
        value = self.library_combo.currentData()
        if value:
            self.restore_draft(value[1])
        else:
            self.transmit_status.setText("Choose a saved or recent message to load.")

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
        else:
            self.transmit_status.setText("Only named saved messages can be deleted.")

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
                    self.sign_combo.addItem("Saved signs", None)
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
        QMessageBox.information(
            self,
            "About / Diagnostics",
            f"{__app_name__} {__version__}\nMIT License - Copyright 2026 Grubbs\n"
            "https://github.com/grubbs-dev/betabrite-controller\n\n"
            f"OS: {platform.system()} {platform.release()}\n"
            f"Selected: {self.selected_port() or 'Automatic'}\n"
            f"State: {self.status_badge.text()}\nDetected ports:\n{ports}\n\nLogs: {log_path()}\n"
            "Dependencies: PySide6 / Qt (LGPLv3), pyserial (BSD), alphasignpy (MIT).",
        )

    def _refresh_diagnostics_page(self) -> None:
        if not hasattr(self, "diagnostics_text"):
            return
        ports = "\n".join(f"- {option.port}: {option.label}" for option in self.options) or "- No USB adapters detected"
        self.diagnostics_text.setPlainText(
            f"{__app_name__} {__version__}\n"
            f"OS: {platform.system()} {platform.release()}\n"
            f"Selected port: {self.selected_port() or 'Automatic'}\n"
            f"Connection: {self.footer_connection.text()}\n"
            f"Log path: {log_path()}\n\nDetected ports:\n{ports}"
        )

    def install_desktop(self):
        from .platform_integration import install_appimage

        try:
            install_appimage()
            QMessageBox.information(
                self,
                __app_name__,
                "Installed for your user. You can now launch BetaBrite Controller from the application menu.",
            )
        except (OSError, ValueError):
            logging.getLogger(__name__).exception("Desktop installation failed")
            QMessageBox.warning(
                self,
                __app_name__,
                "Could not install the application-menu shortcut. Check disk space and permissions for your user application folder.",
            )

    def show_licenses(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Licenses and third-party notices")
        dialog.resize(760, 560)
        layout = QVBoxLayout(dialog)
        text = QTextBrowser()
        directory = application_icon_path().parent / "licenses"
        text.setPlainText(
            "\n\n".join(path.name + "\n\n" + path.read_text(encoding="utf-8") for path in sorted(directory.glob("*.txt")))
        )
        layout.addWidget(text)
        dialog.exec()

    def keyPressEvent(self, event) -> None:
        if self.pages.currentIndex() == 2 or (self.live_scheduler and self.live_scheduler.running):
            if event.key() in {Qt.Key.Key_Space, Qt.Key.Key_Up}:
                self.live_handle_input("jump")
                event.accept()
                return
            if event.key() == Qt.Key.Key_R:
                self.live_handle_input("restart")
                event.accept()
                return
            if event.key() == Qt.Key.Key_Escape:
                self.live_stop()
                event.accept()
                return
        super().keyPressEvent(event)

    def closeEvent(self, event) -> None:
        if self.busy:
            self.transmit_status.setText("Please wait for the current operation before closing.")
            event.ignore()
            return
        self.connection_timer.stop()
        if hasattr(self, "pixel_timer"):
            self.pixel_timer.stop()
        if hasattr(self, "live_timer"):
            self.live_timer.stop()
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
        QMessageBox.warning(
            None,
            __app_name__,
            "The operation could not be completed. Try again or restart the application. Technical details are in the application log.",
        )

    sys.excepthook = report_exception

    window = PortableWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
