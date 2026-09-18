import importlib.util
import os
import plistlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "build_native", ROOT / "scripts" / "build-native.py"
)
build_native = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(build_native)


class NativeBuildHelperTests(unittest.TestCase):
    def test_platform_names(self):
        self.assertEqual(build_native.platform_name("Linux"), "linux")
        self.assertEqual(build_native.platform_name("Darwin"), "macos")
        self.assertEqual(build_native.platform_name("Windows"), "windows")
        with self.assertRaisesRegex(ValueError, "Unsupported"):
            build_native.platform_name("Plan9")

    def test_architecture_aliases(self):
        self.assertEqual(build_native.architecture_name("AMD64"), "x86_64")
        self.assertEqual(build_native.architecture_name("aarch64"), "arm64")
        self.assertEqual(build_native.architecture_name("risc v"), "risc-v")

    def test_numeric_version(self):
        self.assertEqual(build_native.numeric_version("1.2.0"), "1.2.0")
        self.assertEqual(build_native.numeric_version("1.2.0.dev3"), "1.2.0")
        with self.assertRaisesRegex(ValueError, "not numeric"):
            build_native.numeric_version("release-candidate")

    def test_native_arguments_include_target_branding(self):
        windows = build_native.native_extra_args("windows")
        macos = build_native.native_extra_args(
            "macos", signing_identity="Developer ID Application: Example"
        )
        linux = build_native.native_extra_args("linux")

        self.assertIn("--windows-console-mode=disable", windows)
        self.assertIn(
            "--macos-signed-app-name=dev.grubbs.BetaBriteController", macos
        )
        self.assertIn(
            "--macos-sign-identity=Developer ID Application: Example", macos
        )
        self.assertIn("--macos-sign-notarization", macos)
        self.assertIn("--linux-app-console-mode=disable", linux)
        self.assertTrue(
            any(argument.startswith("--include-data-files=") for argument in linux)
        )

    def test_artifact_suffix_is_limited_and_linux_is_never_labeled(self):
        with patch.dict(
            os.environ, {"BETABRITE_ARTIFACT_SUFFIX": "-unsigned"}, clear=False
        ):
            self.assertEqual(build_native.artifact_suffix("windows"), "-unsigned")
            self.assertEqual(build_native.artifact_suffix("macos"), "-unsigned")
            self.assertEqual(build_native.artifact_suffix("linux"), "")

        with patch.dict(
            os.environ, {"BETABRITE_ARTIFACT_SUFFIX": "-unexpected"}, clear=False
        ):
            with self.assertRaisesRegex(ValueError, "Unsupported"):
                build_native.artifact_suffix("windows")

    def test_checksum_manifest_is_sorted(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            first = directory / "a.txt"
            second = directory / "z.txt"
            first.write_text("first", encoding="utf-8")
            second.write_text("second", encoding="utf-8")
            with patch.object(build_native, "DIST", directory):
                manifest = build_native.write_checksums([second, first], "test")

            names = [line.split("  ", 1)[1] for line in manifest.read_text().splitlines()]
            self.assertEqual(names, ["a.txt", "z.txt"])

    def test_macos_bundle_validation(self):
        with tempfile.TemporaryDirectory() as temporary:
            app = Path(temporary) / "BetaBrite Controller.app"
            executable = app / "Contents" / "MacOS" / "BetaBriteController"
            executable.parent.mkdir(parents=True)
            executable.write_bytes(b"native-placeholder")
            metadata = {
                "CFBundleExecutable": executable.name,
                "CFBundleIdentifier": build_native.BUNDLE_IDENTIFIER,
                "CFBundleName": build_native.DISPLAY_NAME,
                "CFBundleShortVersionString": "1.2.0",
                "CFBundleIconFile": "betabrite-controller.icns",
            }
            with (app / "Contents" / "Info.plist").open("wb") as handle:
                plistlib.dump(metadata, handle)

            build_native.validate_macos_bundle(app)

    def test_macos_bundle_validation_rejects_wrong_identifier(self):
        with tempfile.TemporaryDirectory() as temporary:
            app = Path(temporary) / "Broken.app"
            executable = app / "Contents" / "MacOS" / "Broken"
            executable.parent.mkdir(parents=True)
            executable.write_bytes(b"native-placeholder")
            metadata = {
                "CFBundleExecutable": executable.name,
                "CFBundleIdentifier": "invalid.example",
                "CFBundleName": build_native.DISPLAY_NAME,
                "CFBundleShortVersionString": "1.2.0",
                "CFBundleIconFile": "icon.icns",
            }
            with (app / "Contents" / "Info.plist").open("wb") as handle:
                plistlib.dump(metadata, handle)

            with self.assertRaisesRegex(ValueError, "CFBundleIdentifier"):
                build_native.validate_macos_bundle(app)

    def test_notarization_credentials_are_all_or_nothing(self):
        keys = {
            "APPLE_NOTARY_PRIVATE_KEY_PATH": "",
            "APPLE_NOTARY_KEY_ID": "",
            "APPLE_NOTARY_ISSUER_ID": "",
        }
        with patch.dict(os.environ, keys, clear=False):
            self.assertIsNone(build_native.notarization_arguments())

        keys["APPLE_NOTARY_KEY_ID"] = "KEY123"
        with patch.dict(os.environ, keys, clear=False):
            with self.assertRaisesRegex(ValueError, "Incomplete"):
                build_native.notarization_arguments()

        keys.update(
            {
                "APPLE_NOTARY_PRIVATE_KEY_PATH": "/tmp/AuthKey.p8",
                "APPLE_NOTARY_ISSUER_ID": "issuer-id",
            }
        )
        with patch.dict(os.environ, keys, clear=False):
            arguments = build_native.notarization_arguments()
        self.assertEqual(
            arguments,
            [
                "--key",
                "/tmp/AuthKey.p8",
                "--key-id",
                "KEY123",
                "--issuer",
                "issuer-id",
            ],
        )


if __name__ == "__main__":
    unittest.main()
