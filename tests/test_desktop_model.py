import unittest

from betabrite_controller.desktop_model import (
    adapter_options,
    default_adapter_index,
)
from betabrite_controller.devices import SerialDevice
from betabrite_controller.settings import AppSettings, DevicePreference


class DesktopModelTests(unittest.TestCase):

    def test_options_include_customer_facing_usb_identity(self):
        devices = [
            SerialDevice(
                device="COM4",
                vid=0x067B,
                pid=0x23A3,
                product="PL2303GT",
            ),
        ]

        options = adapter_options(
            devices=devices,
            settings=AppSettings(),
        )

        self.assertEqual(len(options), 1)
        self.assertEqual(options[0].port, "COM4")
        self.assertIn("[067b:23a3]", options[0].label)
        self.assertIn("TESTED", options[0].label)

    def test_remembered_adapter_is_labeled_saved(self):
        devices = [
            SerialDevice(
                device="/dev/ttyUSB2",
                vid=0x067B,
                pid=0x23A3,
                serial_number="ABC123",
                product="PL2303GT",
            ),
        ]
        settings = AppSettings(
            preferred_device=DevicePreference(
                device="/dev/ttyUSB0",
                vid=0x067B,
                pid=0x23A3,
                serial_number="ABC123",
            )
        )

        options = adapter_options(devices=devices, settings=settings)

        self.assertTrue(options[0].remembered)
        self.assertIn("SAVED", options[0].label)

    def test_default_index_prefers_remembered_adapter(self):
        devices = [
            SerialDevice(
                device="COM4",
                vid=0x067B,
                pid=0x23A3,
                serial_number="FIRST",
            ),
            SerialDevice(
                device="COM8",
                vid=0x067B,
                pid=0x23A3,
                serial_number="SECOND",
            ),
        ]
        settings = AppSettings(
            preferred_device=DevicePreference(
                device="COM8",
                vid=0x067B,
                pid=0x23A3,
                serial_number="SECOND",
            )
        )

        options = adapter_options(devices=devices, settings=settings)

        self.assertEqual(default_adapter_index(options), 1)

    def test_default_index_falls_back_to_first_option(self):
        devices = [
            SerialDevice(
                device="COM9",
                vid=0x1111,
                pid=0x2222,
                product="Generic USB Serial",
            ),
        ]

        options = adapter_options(
            devices=devices,
            settings=AppSettings(),
        )

        self.assertEqual(default_adapter_index(options), 0)
        self.assertFalse(options[0].remembered)

    def test_default_index_is_negative_without_devices(self):
        self.assertEqual(default_adapter_index([]), -1)


if __name__ == "__main__":
    unittest.main()
