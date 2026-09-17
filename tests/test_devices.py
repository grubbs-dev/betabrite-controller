import unittest
from types import SimpleNamespace
from unittest.mock import patch

from betabrite_controller.devices import (
    DeviceNotFoundError,
    DeviceSelectionError,
    list_serial_devices,
    port_is_available,
    resolve_port,
)


def fake_port(
    device,
    *,
    description="USB Serial Port",
    vid=None,
    pid=None,
    product=None,
):
    return SimpleNamespace(
        device=device,
        description=description,
        hwid="TEST",
        vid=vid,
        pid=pid,
        serial_number=None,
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
        self.assertEqual(resolve_port(), "COM4")

    @patch("betabrite_controller.devices.list_ports.comports")
    def test_single_generic_usb_adapter_can_auto_select(self, comports):
        comports.return_value = [
            fake_port("/dev/ttyUSB0", vid=0x1111, pid=0x2222)
        ]

        self.assertEqual(resolve_port(), "/dev/ttyUSB0")

    @patch("betabrite_controller.devices.list_ports.comports")
    def test_multiple_usb_adapters_require_selection(self, comports):
        comports.return_value = [
            fake_port("COM4", vid=0x1111, pid=0x2222),
            fake_port("COM5", vid=0x3333, pid=0x4444),
        ]

        with self.assertRaises(DeviceSelectionError):
            resolve_port()

    @patch("betabrite_controller.devices.list_ports.comports")
    def test_no_usb_adapter_reports_not_found(self, comports):
        comports.return_value = []

        with self.assertRaises(DeviceNotFoundError):
            resolve_port()

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


if __name__ == "__main__":
    unittest.main()
