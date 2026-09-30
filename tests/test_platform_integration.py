import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from betabrite_controller.platform_integration import install_appimage


class PlatformIntegrationTests(unittest.TestCase):
    def test_appimage_install_is_per_user_and_handles_spaces(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            source = base / "download.AppImage"
            source.write_bytes(b"test executable")
            data = base / "user data"
            with patch.dict(os.environ, {"APPIMAGE": str(source), "XDG_DATA_HOME": str(data)}):
                installed = install_appimage()
            self.assertEqual(installed.read_bytes(), source.read_bytes())
            desktop = (data / "applications" / "dev.grubbs.BetaBriteController.desktop").read_text()
            self.assertIn(f'Exec="{installed}"', desktop)
            self.assertIn("Terminal=false", desktop)

    def test_source_launch_cannot_install_arbitrary_file(self):
        with patch.dict(os.environ, {"APPIMAGE": ""}):
            with self.assertRaises(ValueError):
                install_appimage()
