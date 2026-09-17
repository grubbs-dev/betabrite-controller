import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from betabrite_controller.settings import (
    AppSettings,
    DevicePreference,
    config_dir,
    forget_device,
    load_settings,
    remember_device,
    save_settings,
)


class FakeDevice:
    device = "COM7"
    vid = 0x067B
    pid = 0x23A3
    serial_number = "SERIAL-7"
    manufacturer = "Prolific"
    product = "PL2303GT"


class SettingsTests(unittest.TestCase):

    def test_linux_config_path_uses_xdg(self):
        path = config_dir(
            platform_name="linux",
            environ={"XDG_CONFIG_HOME": "/tmp/config"},
            home=Path("/home/tester"),
        )
        self.assertEqual(path, Path("/tmp/config/betabrite-controller"))

    def test_windows_config_path_uses_appdata(self):
        path = config_dir(
            platform_name="win32",
            environ={"APPDATA": "C:/Users/Test/AppData/Roaming"},
            home=Path("C:/Users/Test"),
        )
        self.assertEqual(
            path,
            Path("C:/Users/Test/AppData/Roaming/BetaBrite Controller"),
        )

    def test_macos_config_path(self):
        path = config_dir(
            platform_name="darwin",
            environ={},
            home=Path("/Users/tester"),
        )
        self.assertEqual(
            path,
            Path("/Users/tester/Library/Application Support/BetaBrite Controller"),
        )

    def test_settings_round_trip(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            settings = AppSettings(
                preferred_device=DevicePreference(
                    device="COM7",
                    vid=0x067B,
                    pid=0x23A3,
                    serial_number="SERIAL-7",
                    product="PL2303GT",
                )
            )
            save_settings(settings, path)
            loaded = load_settings(path)
            self.assertEqual(loaded, settings)

    def test_invalid_json_falls_back_to_defaults(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            path.write_text("{not json", encoding="utf-8")
            self.assertEqual(load_settings(path), AppSettings())

    def test_remember_and_forget_device(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            remember_device(FakeDevice(), path)
            loaded = load_settings(path)
            self.assertEqual(loaded.preferred_device.device, "COM7")
            self.assertEqual(loaded.preferred_device.serial_number, "SERIAL-7")

            forget_device(path)
            self.assertIsNone(load_settings(path).preferred_device)

    def test_saved_json_has_schema_version(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            save_settings(AppSettings(), path)
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload["schema_version"], 1)


if __name__ == "__main__":
    unittest.main()
