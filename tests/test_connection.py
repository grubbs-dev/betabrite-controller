import errno
import unittest
from unittest.mock import Mock, patch

import serial

from betabrite_controller.connection import (
    BetaBriteTransportError,
    classify_transport_exception,
    probe_connection,
)
from betabrite_controller.devices import (
    DeviceNotFoundError,
    DeviceSelection,
    DeviceSelectionError,
)


class FakeSerial:
    def __init__(self, *, error=None):
        self.error = error
        self.port = None
        self.baudrate = None
        self.bytesize = None
        self.parity = None
        self.stopbits = None
        self.timeout = None
        self.write_timeout = None
        self.dtr = None
        self.is_open = False
        self.closed = False

    def open(self):
        if self.error is not None:
            raise self.error
        self.is_open = True

    def close(self):
        self.is_open = False
        self.closed = True


class ConnectionTests(unittest.TestCase):

    @patch("betabrite_controller.connection.resolve_device")
    @patch("betabrite_controller.connection.serial.Serial")
    def test_probe_ready_opens_and_closes_port(self, serial_class, resolve_device):
        handle = FakeSerial()
        serial_class.return_value = handle
        resolve_device.return_value = DeviceSelection(
            port="COM7",
            source="remembered",
        )

        diagnostic = probe_connection()

        self.assertTrue(diagnostic.ready)
        self.assertEqual(diagnostic.state, "ready")
        self.assertEqual(diagnostic.port, "COM7")
        self.assertEqual(handle.port, "COM7")
        self.assertEqual(handle.baudrate, 9600)
        self.assertEqual(handle.bytesize, serial.SEVENBITS)
        self.assertEqual(handle.parity, serial.PARITY_EVEN)
        self.assertEqual(handle.stopbits, serial.STOPBITS_ONE)
        self.assertTrue(handle.closed)

    @patch("betabrite_controller.connection.resolve_device")
    def test_probe_reports_no_adapter(self, resolve_device):
        resolve_device.side_effect = DeviceNotFoundError("No adapter")

        diagnostic = probe_connection()

        self.assertEqual(diagnostic.state, "no-adapter")
        self.assertFalse(diagnostic.ready)

    @patch("betabrite_controller.connection.resolve_device")
    def test_probe_reports_selection_required(self, resolve_device):
        resolve_device.side_effect = DeviceSelectionError("Choose one")

        diagnostic = probe_connection()

        self.assertEqual(diagnostic.state, "selection-required")
        self.assertFalse(diagnostic.ready)

    def test_permission_denied_is_friendly(self):
        diagnostic = classify_transport_exception(
            PermissionError(errno.EACCES, "Permission denied"),
            "/dev/ttyUSB0",
        )

        self.assertEqual(diagnostic.state, "permission-denied")
        self.assertIn("permission", diagnostic.message.casefold())

    def test_busy_port_is_friendly(self):
        diagnostic = classify_transport_exception(
            serial.SerialException("Device or resource busy"),
            "/dev/ttyUSB0",
        )

        self.assertEqual(diagnostic.state, "port-busy")
        self.assertIn("another application", diagnostic.message.casefold())

    def test_missing_port_is_friendly(self):
        diagnostic = classify_transport_exception(
            FileNotFoundError(errno.ENOENT, "No such file or directory"),
            "/dev/ttyUSB9",
        )

        self.assertEqual(diagnostic.state, "port-not-found")
        self.assertIn("reconnect", diagnostic.message.casefold())

    def test_generic_serial_error_is_open_failed(self):
        diagnostic = classify_transport_exception(
            serial.SerialException("driver failure"),
            "COM4",
        )

        self.assertEqual(diagnostic.state, "open-failed")
        self.assertIn("driver failure", diagnostic.message)

    def test_transport_error_from_diagnostic(self):
        diagnostic = classify_transport_exception(
            serial.SerialException("Device or resource busy"),
            "COM4",
        )

        error = BetaBriteTransportError.from_diagnostic(diagnostic)

        self.assertEqual(error.state, "port-busy")
        self.assertEqual(error.port, "COM4")


if __name__ == "__main__":
    unittest.main()
