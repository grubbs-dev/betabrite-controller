#!/usr/bin/env python3
"""Build and package a native BetaBrite Controller desktop application."""

from __future__ import annotations

import argparse
import configparser
import hashlib
import os
import platform
import plistlib
import shlex
import shutil
import subprocess
import sys
import sysconfig
import tarfile
import time
import zipfile
from pathlib import Path

from betabrite_controller import __version__


ROOT = Path(__file__).resolve().parents[1]
ENTRYPOINT = ROOT / "betabrite_desktop.py"
DIST = ROOT / "dist" / "native"
DEPLOY_SPEC = ROOT / "pysidedeploy.spec"
APP_NAME = "BetaBriteController"
DISPLAY_NAME = "BetaBrite Controller"
BUNDLE_IDENTIFIER = "dev.grubbs.BetaBriteController"
IGNORE_DIRS = ".git,.venv,build,dist,__pycache__"
PACKAGE_ICON = (
    ROOT / "betabrite_controller" / "assets" / "betabrite-controller.png"
)
WINDOWS_ICON = ROOT / "assets" / "betabrite-controller.ico"
MACOS_ICON = ROOT / "assets" / "betabrite-controller.icns"
LINUX_ICON = (
    ROOT / "packaging" / "linux" / "dev.grubbs.BetaBriteController.png"
)


def platform_name(system: str | None = None) -> str:
    value = (system or platform.system()).lower()
    if value == "darwin":
        return "macos"
    if value == "windows":
        return "windows"
    if value == "linux":
        return "linux"
    raise ValueError(f"Unsupported deployment platform: {system or platform.system()}")


def architecture_name(machine: str | None = None) -> str:
    value = (machine or platform.machine()).lower()
    aliases = {
        "amd64": "x86_64",
        "x86_64": "x86_64",
        "arm64": "arm64",
        "aarch64": "arm64",
    }
    return aliases.get(value, value.replace(" ", "-"))


def numeric_version(version: str) -> str:
    """Return the numeric portion accepted by native metadata tools."""
    numeric = version.split("+", 1)[0].split(".dev", 1)[0]
    parts = numeric.split(".")
    if not 2 <= len(parts) <= 4 or not all(part.isdigit() for part in parts):
        raise ValueError(f"Native build version is not numeric: {version}")
    return numeric


def run(command: list[str], *, env: dict[str, str] | None = None) -> None:
    print("+", shlex.join(command), flush=True)
    subprocess.run(command, cwd=ROOT, check=True, env=env)


def ensure_build_prerequisites(target: str) -> None:
    """Fail early with an actionable message for local build prerequisites."""
    missing_assets = [
        path
        for path in (PACKAGE_ICON, WINDOWS_ICON, MACOS_ICON, LINUX_ICON)
        if not path.is_file()
    ]
    if missing_assets:
        rendered = "\n".join(f"  {path}" for path in missing_assets)
        raise SystemExit(
            "Application icon assets are missing. Run scripts/generate-icons.py.\n"
            f"{rendered}"
        )

    if target != "linux":
        return

    if not shutil.which("patchelf"):
        raise SystemExit(
            "patchelf is required for the native Linux build.\n"
            "Fedora: sudo dnf install patchelf\n"
            "Ubuntu/Debian: sudo apt-get install patchelf"
        )

    include_dir = Path(sysconfig.get_paths()["include"])
    python_header = include_dir / "Python.h"
    if python_header.exists():
        return

    distro_hint = ""
    os_release = Path("/etc/os-release")
    if os_release.exists():
        release_text = os_release.read_text(encoding="utf-8", errors="replace")
        if "fedora" in release_text.lower():
            distro_hint = (
                "\nFedora: install the matching development headers with:\n"
                "  sudo dnf install python3-devel"
            )

    raise SystemExit(
        "Python development headers are required for the native Linux build.\n"
        f"Expected: {python_header}"
        f"{distro_hint}"
    )


def native_icon(target: str) -> Path:
    return {
        "windows": WINDOWS_ICON,
        "macos": MACOS_ICON,
        "linux": LINUX_ICON,
    }[target]


def artifact_suffix(target: str) -> str:
    """Return the explicit unsigned label used by unsigned desktop builds."""
    if target == "linux":
        return ""
    suffix = os.environ.get("BETABRITE_ARTIFACT_SUFFIX", "")
    if suffix not in {"", "-unsigned"}:
        raise ValueError(f"Unsupported artifact suffix: {suffix}")
    return suffix


def native_extra_args(target: str, *, signing_identity: str = "") -> list[str]:
    """Build the target-specific Nuitka metadata and branding arguments."""
    version = numeric_version(__version__)
    arguments = [
        "--assume-yes-for-downloads",
        "--company-name=Grubbs",
        f"--product-name={DISPLAY_NAME}",
        f"--file-version={version}",
        f"--product-version={version}",
        (
            f"--include-data-files={PACKAGE_ICON.resolve()}="
            "betabrite_controller/assets/betabrite-controller.png"
        ),
    ]

    if target == "windows":
        arguments.append("--windows-console-mode=disable")
    elif target == "macos":
        arguments.extend(
            [
                f"--macos-signed-app-name={BUNDLE_IDENTIFIER}",
                f"--macos-app-name={DISPLAY_NAME}",
                f"--macos-app-version={version}",
                "--macos-app-mode=gui",
                "--macos-app-category-type=public.app-category.utilities",
                "--macos-prohibit-multiple-instances",
            ]
        )
        if signing_identity:
            arguments.extend(
                [
                    f"--macos-sign-identity={signing_identity}",
                    "--macos-sign-notarization",
                ]
            )
    else:
        arguments.append("--linux-app-console-mode=disable")

    return arguments


def prepare_deploy_spec(deploy: str, target: str) -> Path:
    """Create a deterministic pyside6-deploy config for the current target."""
    if DEPLOY_SPEC.exists():
        DEPLOY_SPEC.unlink()

    init_command = [
        deploy,
        str(ENTRYPOINT),
        "-f",
        "--name",
        APP_NAME,
        "--extra-ignore-dirs",
        IGNORE_DIRS,
        "--init",
    ]
    run(init_command)

    if not DEPLOY_SPEC.exists():
        raise SystemExit(
            f"pyside6-deploy did not create the expected config: {DEPLOY_SPEC}"
        )

    config = configparser.ConfigParser(interpolation=None)
    config.read(DEPLOY_SPEC, encoding="utf-8")

    if "app" not in config or "nuitka" not in config:
        raise SystemExit("Generated pysidedeploy.spec is missing required sections.")

    config["app"]["icon"] = str(native_icon(target).resolve())
    config["app"]["title"] = DISPLAY_NAME

    extra_args = shlex.split(config["nuitka"].get("extra_args", ""))
    signing_identity = os.environ.get("MACOS_SIGNING_IDENTITY", "")
    for argument in native_extra_args(target, signing_identity=signing_identity):
        if argument not in extra_args:
            extra_args.append(argument)
    config["nuitka"]["extra_args"] = shlex.join(extra_args)

    with DEPLOY_SPEC.open("w", encoding="utf-8") as handle:
        config.write(handle)

    return DEPLOY_SPEC


def newest_candidate(patterns: list[str], started_at: float) -> Path:
    candidates: list[Path] = []
    for pattern in patterns:
        candidates.extend(ROOT.glob(pattern))

    candidates = [
        path
        for path in candidates
        if path.exists() and path.stat().st_mtime >= started_at - 5
    ]
    if not candidates:
        raise SystemExit(
            "pyside6-deploy completed but no expected native output was found."
        )
    return max(candidates, key=lambda path: path.stat().st_mtime)


def macos_bundle_metadata(app: Path) -> dict[str, object]:
    info_plist = app / "Contents" / "Info.plist"
    if not info_plist.is_file():
        raise ValueError(f"macOS app bundle is missing {info_plist}")
    with info_plist.open("rb") as handle:
        return plistlib.load(handle)


def macos_bundle_executable(app: Path) -> Path:
    metadata = macos_bundle_metadata(app)
    executable_name = metadata.get("CFBundleExecutable")
    if not executable_name:
        raise ValueError("macOS app Info.plist has no CFBundleExecutable value.")

    executable = app / "Contents" / "MacOS" / str(executable_name)
    if not executable.is_file():
        raise ValueError(
            "macOS app bundle executable declared by Info.plist was not found: "
            f"{executable}"
        )
    return executable


def validate_macos_bundle(app: Path) -> None:
    metadata = macos_bundle_metadata(app)
    expected = {
        "CFBundleIdentifier": BUNDLE_IDENTIFIER,
        "CFBundleName": DISPLAY_NAME,
        "CFBundleShortVersionString": numeric_version(__version__),
    }
    mismatches = [
        f"{key}={metadata.get(key)!r} (expected {value!r})"
        for key, value in expected.items()
        if metadata.get(key) != value
    ]
    macos_bundle_executable(app)
    if not metadata.get("CFBundleIconFile"):
        mismatches.append("CFBundleIconFile is missing")
    if mismatches:
        raise ValueError("Invalid macOS bundle metadata:\n  " + "\n  ".join(mismatches))


def smoke_test_native(path: Path, target: str) -> None:
    executable = macos_bundle_executable(path) if target == "macos" else path
    env = os.environ.copy()
    env.setdefault("QT_QPA_PLATFORM", "offscreen")
    run([str(executable), "--smoke-test"], env=env)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_checksums(files: list[Path], target: str) -> Path:
    checksum_file = DIST / f"SHA256SUMS-{target}"
    regular_files = sorted(
        (path for path in files if path.is_file()), key=lambda path: path.name
    )
    lines = [f"{sha256(path)}  {path.name}" for path in regular_files]
    checksum_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return checksum_file


def package_windows(source: Path, arch: str) -> list[Path]:
    suffix = artifact_suffix("windows")
    executable = DIST / (
        f"betabrite-controller-{__version__}-windows-{arch}{suffix}.exe"
    )
    shutil.copy2(source, executable)

    archive = DIST / (
        f"betabrite-controller-{__version__}-windows-{arch}{suffix}.zip"
    )
    with zipfile.ZipFile(
        archive,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as handle:
        handle.write(executable, arcname="BetaBriteController.exe")

    return [executable, archive]


def package_linux(source: Path, arch: str) -> list[Path]:
    executable = DIST / f"betabrite-controller-{__version__}-linux-{arch}.bin"
    shutil.copy2(source, executable)
    executable.chmod(0o755)

    staging_root = DIST / ".staging-linux-package"
    package_root = staging_root / APP_NAME
    if staging_root.exists():
        shutil.rmtree(staging_root)
    package_root.mkdir(parents=True)

    packaged_executable = package_root / f"{APP_NAME}.bin"
    shutil.copy2(executable, packaged_executable)
    packaged_executable.chmod(0o755)

    linux_assets = ROOT / "packaging" / "linux"
    for name in (
        "AppRun",
        "install-desktop.sh",
        "uninstall-desktop.sh",
        "betabrite-controller.desktop.in",
        "dev.grubbs.BetaBriteController.png",
    ):
        shutil.copy2(linux_assets / name, package_root / name)

    readme = package_root / "README.txt"
    readme.write_text(
        "BetaBrite Controller portable Linux build\n\n"
        "Run ./AppRun to start without installing. Run ./install-desktop.sh "
        "to add a per-user application-menu entry; no root access is required. "
        "The standalone binary includes Python and Qt.\n\n"
        "READY means the selected serial transport opened successfully. A "
        "successful send means bytes were written without a transport error; "
        "the sign does not provide an acknowledgment on this controller path.\n",
        encoding="utf-8",
    )

    archive = DIST / f"betabrite-controller-{__version__}-linux-{arch}.tar.gz"
    with tarfile.open(archive, "w:gz") as handle:
        handle.add(package_root, arcname=package_root.name)

    shutil.rmtree(staging_root)
    return [executable, archive]


def notarization_arguments() -> list[str] | None:
    values = {
        "key": os.environ.get("APPLE_NOTARY_PRIVATE_KEY_PATH", ""),
        "key_id": os.environ.get("APPLE_NOTARY_KEY_ID", ""),
        "issuer": os.environ.get("APPLE_NOTARY_ISSUER_ID", ""),
    }
    configured = [bool(value) for value in values.values()]
    if not any(configured):
        return None
    if not all(configured):
        missing = ", ".join(key for key, value in values.items() if not value)
        raise ValueError(f"Incomplete Apple notarization credentials: {missing}")
    return [
        "--key",
        values["key"],
        "--key-id",
        values["key_id"],
        "--issuer",
        values["issuer"],
    ]


def create_macos_zip(app: Path, archive: Path) -> None:
    if shutil.which("ditto"):
        run(
            [
                "ditto",
                "-c",
                "-k",
                "--sequesterRsrc",
                "--keepParent",
                str(app),
                str(archive),
            ]
        )
        return

    with zipfile.ZipFile(
        archive,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as handle:
        for path in app.rglob("*"):
            if path.is_file():
                handle.write(path, arcname=str(path.relative_to(DIST)))


def notarize_macos_app(app: Path, arguments: list[str]) -> None:
    staging = DIST / ".staging-notarization.zip"
    staging.parent.mkdir(parents=True, exist_ok=True)
    if staging.exists():
        staging.unlink()
    create_macos_zip(app, staging)
    run(["xcrun", "notarytool", "submit", str(staging), *arguments, "--wait"])
    run(["xcrun", "stapler", "staple", str(app)])
    staging.unlink()


def package_macos(source: Path, arch: str) -> list[Path]:
    app = DIST / f"{DISPLAY_NAME}.app"
    if app.exists():
        shutil.rmtree(app)
    shutil.copytree(source, app, symlinks=True)
    validate_macos_bundle(app)

    signing_identity = os.environ.get("MACOS_SIGNING_IDENTITY", "")
    notary_args = notarization_arguments()
    if notary_args and not signing_identity:
        raise ValueError("Apple notarization requires MACOS_SIGNING_IDENTITY.")
    if signing_identity:
        run(["codesign", "--verify", "--deep", "--strict", str(app)])
    if notary_args:
        notarize_macos_app(app, notary_args)

    suffix = artifact_suffix("macos")
    archive = DIST / (
        f"betabrite-controller-{__version__}-macos-{arch}{suffix}.zip"
    )
    create_macos_zip(app, archive)

    hdiutil = shutil.which("hdiutil")
    if not hdiutil:
        raise SystemExit("hdiutil is required to build the macOS DMG.")

    dmg = DIST / (
        f"betabrite-controller-{__version__}-macos-{arch}{suffix}.dmg"
    )
    staging = DIST / ".staging-dmg"
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)
    shutil.copytree(app, staging / app.name, symlinks=True)
    (staging / "Applications").symlink_to("/Applications", target_is_directory=True)
    run(
        [
            hdiutil,
            "create",
            "-volname",
            DISPLAY_NAME,
            "-srcfolder",
            str(staging),
            "-ov",
            "-format",
            "UDZO",
            str(dmg),
        ]
    )
    shutil.rmtree(staging)

    if signing_identity:
        run(
            [
                "codesign",
                "--force",
                "--timestamp",
                "--sign",
                signing_identity,
                str(dmg),
            ]
        )
    if notary_args:
        run(["xcrun", "notarytool", "submit", str(dmg), *notary_args, "--wait"])
        run(["xcrun", "stapler", "staple", str(dmg)])

    shutil.rmtree(app)
    return [archive, dmg]


def remove_path(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()


def find_deploy() -> str | None:
    """Find pyside6-deploy next to the active interpreter or on PATH."""
    executable_name = "pyside6-deploy.exe" if os.name == "nt" else "pyside6-deploy"
    adjacent = Path(sys.executable).with_name(executable_name)
    if adjacent.is_file():
        return str(adjacent)
    return shutil.which("pyside6-deploy")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print target metadata and deployment arguments without compiling.",
    )
    args = parser.parse_args()

    try:
        target = platform_name()
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    arch = architecture_name()
    DIST.mkdir(parents=True, exist_ok=True)

    deploy = find_deploy()
    if not deploy:
        raise SystemExit(
            "pyside6-deploy was not found. Install the desktop extra first."
        )

    ensure_build_prerequisites(target)

    if args.dry_run:
        print("Target:", target)
        print("Architecture:", arch)
        print("Version:", __version__)
        print("Icon:", native_icon(target).relative_to(ROOT))
        print("Bundle identifier:", BUNDLE_IDENTIFIER)
        print(
            "Nuitka arguments:",
            shlex.join(
                native_extra_args(
                    target,
                    signing_identity=os.environ.get("MACOS_SIGNING_IDENTITY", ""),
                )
            ),
        )
        return 0

    spec = prepare_deploy_spec(deploy, target)
    command = [
        deploy,
        "-c",
        str(spec),
        "-f",
        "--name",
        APP_NAME,
        "--extra-ignore-dirs",
        IGNORE_DIRS,
    ]

    for stale in (
        ROOT / f"{APP_NAME}.exe",
        ROOT / f"{APP_NAME}.bin",
        ROOT / f"{APP_NAME}.app",
    ):
        remove_path(stale)

    started_at = time.time()
    run(command)

    if target == "windows":
        source = newest_candidate([f"{APP_NAME}.exe", "*.exe"], started_at)
    elif target == "macos":
        source = newest_candidate([f"{APP_NAME}.app", "*.app"], started_at)
    else:
        source = newest_candidate([f"{APP_NAME}.bin", "*.bin"], started_at)

    smoke_test_native(source, target)

    if target == "windows":
        artifacts = package_windows(source, arch)
    elif target == "macos":
        artifacts = package_macos(source, arch)
    else:
        artifacts = package_linux(source, arch)
    remove_path(source)

    checksum_file = write_checksums(artifacts, target)
    artifacts.append(checksum_file)

    print("\nNative artifacts:")
    for artifact in artifacts:
        print(f"  {artifact.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
