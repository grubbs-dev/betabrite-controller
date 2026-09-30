"""Qt integration tests; optional core installs skip these, desktop CI runs them."""
import importlib.util
import os
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@unittest.skipUnless(importlib.util.find_spec("PySide6"), "Desktop extra not installed")
class DesktopRuntimeTests(unittest.TestCase):
    def setUp(self):
        from PySide6.QtWidgets import QApplication
        from betabrite_controller.desktop import PortableWindow
        self.directory = tempfile.TemporaryDirectory()
        self.environment = patch.dict(os.environ, {"BETABRITE_CONFIG_DIR": self.directory.name})
        self.environment.start()
        self.ports = patch("serial.tools.list_ports.comports", return_value=[])
        self.ports.start()
        self.app = QApplication.instance() or QApplication([])
        self.window = PortableWindow(passive=True)

    def tearDown(self):
        self.window.close()
        self.app.processEvents()
        self.ports.stop()
        self.environment.stop()
        self.directory.cleanup()

    def test_no_hardware_window_and_persistence(self):
        from betabrite_controller.settings import load_settings
        self.assertFalse(self.window.send_button.isEnabled())
        self.window.message.setText("HELLO")
        self.window.close()
        self.assertEqual(load_settings().draft["message"], "HELLO")

    def test_worker_does_not_block_events_or_allow_duplicate_sends(self):
        from betabrite_controller.connection import ConnectionDiagnostic
        release = threading.Event()
        def work():
            release.wait(3)
            return ConnectionDiagnostic(state="ready", message="Checked", port="COM7")
        self.window.start_operation(work)
        self.assertTrue(self.window.busy)
        self.window.send_current()
        self.assertFalse(self.window.send_button.isEnabled())
        self.window.message.setText("EDIT WHILE BUSY")
        self.app.processEvents()
        self.assertEqual(self.window.message.text(), "EDIT WHILE BUSY")
        release.set()
        deadline = time.monotonic() + 5
        while self.window.busy and time.monotonic() < deadline:
            self.app.processEvents()
            time.sleep(.01)
        self.assertFalse(self.window.busy)
        self.assertTrue(self.window.send_button.isEnabled())

    def test_unplugged_manual_port_clears_ready(self):
        self.window.manual_port = "/dev/nonexistent-betabrite-test"
        self.window.last_ready_port = self.window.manual_port
        self.window.connection_ready = True
        self.window.refresh_connection(active=False)
        self.assertFalse(self.window.connection_ready)
        self.assertIsNone(self.window.last_ready_port)
