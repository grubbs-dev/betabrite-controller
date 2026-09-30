"""Regression gates for persisted state, protocol safety and service behavior."""
from dataclasses import asdict, replace
import importlib.metadata
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from betabrite_controller import __version__
from betabrite_controller.controller import BetaBriteController
from betabrite_controller.desktop_controls import MessageDraft
from betabrite_controller.devices import resolve_device, SerialDevice, DeviceNotFoundError
from betabrite_controller.settings import AppSettings, DevicePreference, save_settings, load_settings, remember_device, forget_device
from betabrite_controller.service import transmit


class ReleaseBehaviorTests(unittest.TestCase):
    def test_saved_messages_survive_device_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            draft = asdict(MessageDraft(message="HELLO"))
            state = AppSettings(draft=draft, saved_messages={"Welcome": draft}, recent_messages=[draft],
                                signs={"Front desk": DevicePreference(device="COM7")})
            save_settings(state, path)
            remember_device(SerialDevice(device="COM8"), path)
            forget_device(path)
            self.assertEqual(load_settings(path), state)
            self.assertFalse(list(Path(directory).glob(".settings-*")))

    def test_malformed_fields_recover(self):
        for payload in (None, [], {"preferred_device": {"device": [], "serial_number": 9}},
                        {"draft": {"message": []}, "saved_messages": [], "recent_messages": 42},
                        {"draft": {"color_name": []}, "signs": []}):
            settings = AppSettings.from_mapping(payload)
            self.assertIsInstance(settings, AppSettings)

    def test_failed_atomic_save_preserves_existing_preferences(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            original = AppSettings(preferred_device=DevicePreference(device="COM7"))
            save_settings(original, path)
            with patch("betabrite_controller.settings.os.replace", side_effect=OSError("disk error")):
                with self.assertRaises(OSError):
                    save_settings(AppSettings(), path)
            self.assertEqual(load_settings(path), original)
            self.assertFalse(list(Path(directory).glob(".settings-*")))

    def test_missing_saved_identity_never_falls_back_to_other_sign(self):
        state = AppSettings(preferred_device=DevicePreference(vid=1, pid=2, serial_number="one"))
        with self.assertRaises(DeviceNotFoundError):
            resolve_device(settings=state, devices=[SerialDevice("COM9", vid=1, pid=2, serial_number="two")])

    def test_protocol_control_bytes_are_rejected(self):
        for message in ("hello\x04", "\x1b", "hello\x00"):
            with self.assertRaises(ValueError):
                BetaBriteController().build_content(message)
            with self.assertRaises(ValueError):
                MessageDraft(message=message).validate()

    @patch("betabrite_controller.controller.Sign")
    def test_transmit_preserves_serial_settings_and_packet(self, sign_class):
        result = transmit("COM7", MessageDraft(message="HELLO", color_name="green"))
        handle = sign_class.return_value
        handle.open.assert_called_once_with("COM7", baudrate=9600, bytesize=7, parity="E", stopbits=1, timeout=1, dtr=False)
        self.assertEqual(handle._ser.write_timeout, 5)
        payload = handle.send.call_args.args[0].to_bytes()
        self.assertIn(b"HELLO", payload)
        self.assertTrue(payload.endswith(b"\x04"))
        handle.close.assert_called_once()
        self.assertTrue(result.ready)
        self.assertIn("does not acknowledge", result.message)

    @patch("betabrite_controller.controller.Sign")
    def test_transport_is_closed_on_failure(self, sign_class):
        sign_class.return_value.send.side_effect = OSError("adapter failed")
        with self.assertRaises(RuntimeError):
            transmit("COM7", MessageDraft())
        sign_class.return_value.close.assert_called_once()

    @patch("betabrite_controller.controller.Sign")
    def test_packet_bytes_remain_compatible_with_established_protocol(self, sign_class):
        BetaBriteController(port="COM7").send("HELLO", color_name="green", mode_name="hold",
                                            speed_level=3, flash=True, wide=True)
        payload = sign_class.return_value.send.call_args.args[0].to_bytes()
        self.assertEqual(payload, bytes.fromhex(
            "0000000000015a303002ff41411b26621c321712073148454c4c4f073011033033393504"))

    def test_bundled_project_license_and_notices_match_sources(self):
        root = Path(__file__).resolve().parents[1]
        licenses = root / "betabrite_controller" / "assets" / "licenses"
        self.assertEqual((root / "LICENSE").read_text(), (licenses / "BetaBrite-Controller.txt").read_text())
        self.assertEqual((root / "THIRD_PARTY_NOTICES.md").read_text(), (licenses / "THIRD-PARTY.txt").read_text())

    def test_version_matches_installed_metadata(self):
        self.assertEqual(importlib.metadata.version("betabrite-controller"), __version__)
