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

    def test_connect_button_probes_without_remembering_adapter(self):
        from betabrite_controller.connection import ConnectionDiagnostic
        from betabrite_controller.devices import SerialDevice
        from betabrite_controller.settings import load_settings

        self.ports.stop()
        fake_port = SerialDevice(
            device="COM7",
            description="USB Serial Port",
            vid=0x067B,
            pid=0x23A3,
            product="PL2303GT",
        )
        with (
            patch("betabrite_controller.desktop.adapter_options") as adapter_options,
            patch("betabrite_controller.desktop.probe_connection") as probe_connection,
            patch("betabrite_controller.devices.list_serial_devices", return_value=[fake_port]),
            patch("betabrite_controller.devices.list_candidate_devices", return_value=[fake_port]),
        ):
            adapter_options.return_value = [
                type("Option", (), {"port": "COM7", "label": "COM7", "preferred": True, "remembered": False})()
            ]
            probe_connection.return_value = ConnectionDiagnostic(
                state="ready",
                message="Checked",
                port="COM7",
                source="explicit",
            )

            self.window.populate_adapters()
            self.window.remember_button.click()
            self._wait_until_idle()

        probe_connection.assert_called_once_with("COM7")
        self.assertIsNone(load_settings().preferred_device)
        self.assertTrue(self.window.connection_ready)

    def test_current_draft_tracks_visible_format_controls(self):
        self.window.message.setText("FORMATTED")
        self.window.select_color("green")
        self.window.select_mode("hold")
        self.window.special_combo.setCurrentIndex(self.window.special_combo.findData("fireworks"))
        self.window.speed_slider.setValue(5)
        self.window.flash.setChecked(True)
        self.window.select_font_mode("wide")

        draft = self.window.current_draft()

        self.assertEqual(draft.message, "FORMATTED")
        self.assertEqual(draft.color_name, "green")
        self.assertEqual(draft.mode_name, "hold")
        self.assertEqual(draft.special_name, "fireworks")
        self.assertEqual(draft.speed_level, 5)
        self.assertTrue(draft.flash)
        self.assertTrue(draft.wide)

    def test_saved_message_delete_only_enabled_for_named_messages(self):
        from dataclasses import asdict, replace

        from betabrite_controller.desktop_controls import MessageDraft
        from betabrite_controller.settings import load_settings

        draft = asdict(MessageDraft(message="SAVED"))
        self.window.persist(
            replace(
                load_settings(),
                saved_messages={"Favorite": draft},
                recent_messages=[asdict(MessageDraft(message="RECENT"))],
            )
        )
        self.window.refresh_library()

        self.window.library_combo.setCurrentIndex(0)
        self.assertFalse(self.window.delete_library_button.isEnabled())

        self.window.library_combo.setCurrentIndex(1)
        self.assertTrue(self.window.delete_library_button.isEnabled())

        self.window.library_combo.setCurrentIndex(2)
        self.assertFalse(self.window.delete_library_button.isEnabled())

    def test_clear_sign_runs_in_worker_without_persisting_recent_message(self):
        from betabrite_controller.connection import ConnectionDiagnostic
        from betabrite_controller.settings import load_settings

        self.window.manual_port = "COM7"
        self.window.set_connection_view(
            ConnectionDiagnostic(state="ready", message="Ready", port="COM7")
        )
        with patch("betabrite_controller.desktop.clear_sign") as clear_sign:
            clear_sign.return_value = ConnectionDiagnostic(
                state="ready",
                message="Cleared",
                port="COM7",
                source="clear",
            )
            self.window.clear_button.click()
            self._wait_until_idle()

        clear_sign.assert_called_once_with("COM7")
        self.assertEqual(load_settings().recent_messages, [])

    def test_pixel_studio_navigation_and_editing(self):
        from betabrite_controller.pixel_model import PixelColor

        self.window.navigation.setCurrentRow(1)
        self.assertEqual(self.window.pages.currentIndex(), 1)

        self.window.select_pixel_color(PixelColor.GREEN)
        self.window.pixel_canvas.frame.set_pixel(1, 2, self.window.pixel_color)
        self.window.pixel_canvas_changed(1, 2)
        self.assertEqual(self.window.current_pixel_frame().get_pixel(1, 2), PixelColor.GREEN)
        self.assertTrue(self.window.pixel_dirty)

        self.window.select_pixel_tool("eraser")
        self.window.pixel_canvas.frame.unset_pixel(1, 2)
        self.window.pixel_canvas_changed(1, 2)
        self.assertEqual(self.window.current_pixel_frame().get_pixel(1, 2), PixelColor.OFF)

        self.window.select_pixel_color(PixelColor.RED)
        self.window.pixel_fill_frame()
        self.assertEqual(self.window.current_pixel_frame().get_pixel(0, 0), PixelColor.RED)
        self.window.pixel_invert_frame()
        self.assertEqual(self.window.current_pixel_frame().get_pixel(0, 0), PixelColor.OFF)
        self.window.pixel_clear_frame()
        self.assertEqual(self.window.current_pixel_frame().get_pixel(0, 0), PixelColor.OFF)

    def test_pixel_frame_timeline_duration_and_playback(self):
        self.assertEqual(len(self.window.pixel_document.frames), 1)
        self.window.pixel_add_frame()
        self.assertEqual(len(self.window.pixel_document.frames), 2)
        self.assertEqual(self.window.pixel_frame_index, 1)

        self.window.pixel_duplicate_frame()
        self.assertEqual(len(self.window.pixel_document.frames), 3)
        self.assertEqual(self.window.pixel_frame_index, 2)

        self.window.pixel_duration.setValue(500)
        self.assertEqual(self.window.current_pixel_animation_frame().duration_ms, 500)
        self.window.pixel_previous_frame()
        self.assertEqual(self.window.pixel_frame_index, 1)
        self.window.pixel_next_frame()
        self.assertEqual(self.window.pixel_frame_index, 2)

        self.window.pixel_play()
        self.assertTrue(self.window.pixel_playing)
        self.assertTrue(self.window.pixel_timer.isActive())
        self.window.pixel_playback_tick()
        self.assertEqual(self.window.pixel_frame_index, 0)
        self.window.pixel_pause()
        self.assertFalse(self.window.pixel_playing)
        self.window.pixel_stop()
        self.assertEqual(self.window.pixel_frame_index, 0)

        self.window.pixel_delete_frame()
        self.assertEqual(len(self.window.pixel_document.frames), 2)

    def test_pixel_save_open_helpers_without_dialogs(self):
        from betabrite_controller.pixel_model import PixelColor

        path = os.path.join(self.directory.name, "art.bbpixel")
        self.window.current_pixel_frame().set_pixel(0, 0, PixelColor.YELLOW)
        self.window.pixel_mark_dirty()
        self.window.pixel_save_document(path)
        self.assertFalse(self.window.pixel_dirty)

        self.window.pixel_new_document()
        self.assertEqual(self.window.current_pixel_frame().get_pixel(0, 0), PixelColor.OFF)
        self.window.pixel_open_document(path)
        self.assertEqual(self.window.current_pixel_frame().get_pixel(0, 0), PixelColor.YELLOW)
        self.assertFalse(self.window.pixel_dirty)

    def test_pixel_send_uses_worker_and_ready_state(self):
        from betabrite_controller.connection import ConnectionDiagnostic

        self.assertFalse(self.window.pixel_send_button.isEnabled())
        self.window.manual_port = "COM7"
        self.window.set_connection_view(ConnectionDiagnostic(state="ready", message="Ready", port="COM7"))
        self.assertTrue(self.window.pixel_send_button.isEnabled())

        with patch("betabrite_controller.desktop.transmit_graphic") as transmit_graphic:
            transmit_graphic.return_value = ConnectionDiagnostic(
                state="ready",
                message="Graphic sent",
                port="COM7",
                source="graphics",
            )
            self.window.pixel_send_button.click()
            self._wait_until_idle()

        transmit_graphic.assert_called_once()
        self.assertEqual(transmit_graphic.call_args.args[0], "COM7")
        self.assertIn("Graphic sent", self.window.pixel_status.text())

    def test_live_mode_navigation_virtual_run_and_benchmark(self):
        self.window.navigation.setCurrentRow(2)
        self.assertEqual(self.window.pages.currentIndex(), 2)
        self.assertIn("VIRTUAL", self.window.live_output_badge.text())

        self.window.live_start()
        self.assertTrue(self.window.live_scheduler.running)
        self.assertTrue(self.window.live_timer.isActive())
        self.window.live_handle_input("jump")
        self.assertFalse(self.window.live_source.on_ground)
        self.window.live_tick()
        self.assertGreater(int(self.window.live_metric_labels["rendered"].text()), 0)

        self.window.live_pause_resume()
        self.assertTrue(self.window.live_scheduler.paused)
        self.window.live_pause_resume()
        self.assertFalse(self.window.live_scheduler.paused)
        self.window.live_stop()
        self.assertFalse(self.window.live_scheduler.running)
        self.assertFalse(self.window.live_timer.isActive())

        self.window.live_run_virtual_benchmark()
        self.assertIsNotNone(self.window.live_report)
        self.assertGreater(self.window.live_report.recommended_fps, 0)
        self.assertIn("Virtual benchmark complete", self.window.live_status.text())

    def test_live_physical_benchmark_is_safety_blocked(self):
        self.window.manual_port = "COM7"
        self.window.live_check_physical_benchmark()

        self.assertEqual(self.window.live_report.results[0].status, "blocked")
        self.assertIn("disabled", self.window.live_status.text())
        self.assertIn("Hardware blocked", self.window.live_metric_labels["connection"].text())

    def test_unplugged_manual_port_clears_ready(self):
        self.window.manual_port = "/dev/nonexistent-betabrite-test"
        self.window.last_ready_port = self.window.manual_port
        self.window.connection_ready = True
        self.window.refresh_connection(active=False)
        self.assertFalse(self.window.connection_ready)
        self.assertIsNone(self.window.last_ready_port)

    def _wait_until_idle(self):
        deadline = time.monotonic() + 5
        while self.window.busy and time.monotonic() < deadline:
            self.app.processEvents()
            time.sleep(.01)
        self.app.processEvents()
        self.assertFalse(self.window.busy)
