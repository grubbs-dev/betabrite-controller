import unittest

from betabrite_controller.branding import application_icon_path


class BrandingTests(unittest.TestCase):
    def test_packaged_application_icon_is_a_png(self):
        icon = application_icon_path()
        self.assertTrue(icon.is_file())
        self.assertEqual(icon.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")


if __name__ == "__main__":
    unittest.main()
