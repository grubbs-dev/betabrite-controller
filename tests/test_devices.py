import unittest
from types import SimpleNamespace
from unittest.mock import patch

from betabrite_controller.devices import (
    DeviceNotFoundError,
    DeviceSelectionError,
    SerialDevice,
    diagnose_device,
    list_candidate_devices,
    list_serial_devices,
    port_is_available,
    resolve_port,
)
from betabrite_controller.settings import AppSettings, DevicePreference


def fake_port(
    device,
    *,
    description="USB Serial Port",
    vid=None,
    pid=None,
    product=None,
    serial_number=None,
):
    return SimpleNamespace(
        device=device,
        description=description,
        hwid="TEST",
        vid=vid,
        pid=pid,
        serial_number=serial_number,
        manufacturer=None,
        product=product,
    )


class DeviceDiscoveryTests(unittest.TestCase):

    @patch("betabrite_controller.devices.list_ports.comports")
    def test_tested_adapter_is_preferred(self, comports):
        comports.return_value = [
            fake_port("COM8", vid=0x1234, pid=0x5678),
            fake_port(
                "COM4",
                vid=0x067B,
                pid=0x23A3,
                product="PL2303GT",
            ),
        ]

        devices = list_serial_devices()

        self.assertEqual(devices[0].device, "COM4")
        self.assertTrue(devices[0].preferred)
        self.assertEqual(resolve_port(settings=AppSettings()), "COM4")

    @patch("betabrite_controller.devices.list_ports.comports")
    def test_single_generic_usb_adapter_can_auto_select(self, comports):
        comports.return_value = [
            fake_port("/dev/ttyUSB0", vid=0x1111, pid=0x2222)
        ]

        self.assertEqual(
            resolve_port(settings=AppSettings()),
            "/dev/ttyUSB0",
        )

    @patch("betabrite_controller.devices.list_ports.comports")
    def test_multiple_usb_adapters_require_selection(self, comports):
        comports.return_value = [
            fake_port("COM4", vid=0x1111, pid=0x2222),
            fake_port("COM5", vid=0x3333, pid=0x4444),
        ]

        with self.assertRaises(DeviceSelectionError):
            resolve_port(settings=AppSettings())

    @patch("betabrite_controller.devices.list_ports.comports")
    def test_no_usb_adapter_reports_not_found(self, comports):
        comports.return_value = []

        with self.assertRaises(DeviceNotFoundError):
            resolve_port(settings=AppSettings())

    @patch("betabrite_controller.devices.list_ports.comports")
    def test_explicit_port_always_wins(self, comports):
        comports.return_value = []

        self.assertEqual(resolve_port("COM9"), "COM9")

    @patch("betabrite_controller.devices.list_ports.comports")
    def test_enumerated_port_is_available(self, comports):
        comports.return_value = [
            fake_port("COM7", vid=0x1111, pid=0x2222)
        ]

        self.assertTrue(port_is_available("COM7"))

    @patch("betabrite_controller.devices.list_ports.comports")
    def test_candidate_list_hides_legacy_ports(self, comports):
        comports.return_value = [
            fake_port("/dev/ttyS0", description="n/a"),
            fake_port("/dev/ttyUSB0", vid=0x1111, pid=0x2222),
        ]

        self.assertEqual(
            [device.device for device in list_candidate_devices()],
            ["/dev/ttyUSB0"],
        )

    def test_remembered_serial_number_follows_port_renumbering(self):
        settings = AppSettings(
            preferred_device=DevicePreference(
                device="COM4",
                vid=0x067B,
                pid=0x23A3,
                serial_number="ABC123",
            )
        )
        devices = [
            SerialDevice(
                device="COM9",
                vid=0x067B,
                pid=0x23A3,
                serial_number="ABC123",
                product="PL2303GT",
            ),
            SerialDevice(
                device="COM10",
                vid=0x067B,
                pid=0x23A3,
                serial_number="OTHER",
                product="PL2303GT",
            ),
        ]

        self.assertEqual(
            resolve_port(settings=settings, devices=devices),
            "COM9",
        )

    def test_remembered_port_breaks_tie_without_serial_number(self):
        settings = AppSettings(
            preferred_device=DevicePreference(
                device="COM5",
                vid=0x067B,
                pid=0x23A3,
            )
        )
        devices = [
            SerialDevice(device="COM4", vid=0x067B, pid=0x23A3),
            SerialDevice(device="COM5", vid=0x067B, pid=0x23A3),
        ]

        self.assertEqual(
            resolve_port(settings=settings, devices=devices),
            "COM5",
        )

    def test_diagnostic_reports_selection_required(self):
        devices = [
            SerialDevice(device="COM4", vid=0x1111, pid=0x2222),
            SerialDevice(device="COM5", vid=0x3333, pid=0x4444),
        ]

        diagnostic = diagnose_device(
            settings=AppSettings(),
            devices=devices,
        )

        self.assertEqual(diagnostic.state, "selection-required")
        self.assertFalse(diagnostic.ready)


if __name__ == "__main__":
    unittest.main()
