import unittest
from unittest.mock import patch

from betabrite_controller.controller import (
    BetaBriteController,
    COLORS,
    MODES,
    SPECIALS,
)


class ControllerTests(unittest.TestCase):

    def setUp(self):
        self.controller = BetaBriteController(
            port="/dev/does-not-exist"
        )

    def test_default_port_can_be_overridden(self):
        self.assertEqual(
            self.controller.port,
            "/dev/does-not-exist",
        )

    def test_missing_device_reports_disconnected(self):
        self.assertFalse(
            self.controller.connected
        )

    @patch("betabrite_controller.controller.probe_connection")
    def test_check_connection_uses_active_probe(self, probe_connection):
        sentinel = object()
        probe_connection.return_value = sentinel

        result = self.controller.check_connection()

        self.assertIs(result, sentinel)
        probe_connection.assert_called_once_with("/dev/does-not-exist")

    def test_all_colors_exist(self):
        self.assertIn("red", COLORS)
        self.assertIn("green", COLORS)
        self.assertIn("auto", COLORS)

    def test_modes_exist(self):
        self.assertIn("rotate", MODES)
        self.assertIn("hold", MODES)
        self.assertIn("scroll", MODES)

    def test_specials_exist(self):
        self.assertIn("fireworks", SPECIALS)
        self.assertIn("snow", SPECIALS)

    def test_ascii_message(self):
        content = self.controller.build_content(
            "TEST",
            color_name="green",
            speed_level=3,
        )

        self.assertIn(b"TEST", content)

    def test_non_ascii_is_safe(self):
        content = self.controller.build_content(
            "CAFÉ",
            color_name="red",
        )

        self.assertIn(b"CAF?", content)

    def test_invalid_speed(self):
        with self.assertRaises(ValueError):
            self.controller.build_content(
                "TEST",
                speed_level=9,
            )

    def test_invalid_color(self):
        with self.assertRaises(ValueError):
            self.controller.build_content(
                "TEST",
                color_name="purple",
            )


if __name__ == "__main__":
    unittest.main()
