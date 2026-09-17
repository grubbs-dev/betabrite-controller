#!/usr/bin/env python3
"""Build a native BetaBrite Controller desktop artifact for the current OS."""

from __future__ import annotations

import argparse
import hashlib
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import time
import zipfile
from pathlib import Path

from betabrite_controller import __version__


ROOT = Path(__file__).resolve().parents[1]
ENTRYPOINT = ROOT / "betabrite_desktop.py"
DIST = ROOT / "dist" / "native"
APP_NAME = "BetaBriteController"
DISPLAY_NAME = "BetaBrite Controller"


def platform_name() -> str:
    value = platform.system().lower()
    if value == "darwin":
        return "macos"
    if value == "windows":
        return "windows"
    if value == "linux":
        return "linux"
    raise SystemExit(f"Unsupported deployment platform: {platform.system()}")


def architecture_name() -> str:
    machine = platform.machine().lower()
    aliases = {
        "amd64": "x86_64",
        "x86_64": "x86_64",
        "arm64": "arm64",
        "aarch64": "arm64",
    }
    return aliases.get(machine, machine.replace(" ", "-"))


def run(command: list[str], *, env: dict[str, str] | None = None) -> None:
    print("+", " ".join(command), flush=True)
    subprocess.run(command, cwd=ROOT, check=True, env=env)


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


def smoke_test_native(path: Path, target: str) -> None:
    if target == "macos":
        binaries = list((path / "Contents" / "MacOS").iterdir())
        binaries = [candidate for candidate in binaries if candidate.is_file()]
        if not binaries:
            raise SystemExit("macOS app bundle contains no executable.")
        executable = binaries[0]
    else:
        executable = path

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
    lines = [f"{sha256(path)}  {path.name}" for path in files if path.is_file()]
    checksum_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return checksum_file


def package_windows(source: Path, arch: str) -> list[Path]:
    executable = DIST / (
        f"betabrite-controller-{__version__}-windows-{arch}.exe"
    )
    shutil.copy2(source, executable)

    archive = DIST / (
        f"betabrite-controller-{__version__}-windows-{arch}.zip"
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
    executable = DIST / (
        f"betabrite-controller-{__version__}-linux-{arch}.bin"
    )
    shutil.copy2(source, executable)
    executable.chmod(0o755)

    readme = DIST / "README-linux-portable.txt"
    readme.write_text(
        "BetaBrite Controller portable Linux build\n\n"
        "This binary includes its Python and Qt runtime. Mark it executable if "
        "your archive tool does not preserve permissions, then launch it from "
        "your desktop file manager or terminal.\n",
        encoding="utf-8",
    )

    archive = DIST / (
        f"betabrite-controller-{__version__}-linux-{arch}.tar.gz"
    )
    with tarfile.open(archive, "w:gz") as handle:
        handle.add(executable, arcname=executable.name)
        handle.add(readme, arcname=readme.name)

    readme.unlink()
    return [executable, archive]


def package_macos(source: Path, arch: str) -> list[Path]:
    app = DIST / f"{DISPLAY_NAME}.app"
    if app.exists():
        shutil.rmtree(app)
    shutil.copytree(source, app, symlinks=True)

    archive = DIST / (
        f"betabrite-controller-{__version__}-macos-{arch}.zip"
    )
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
    else:
        with zipfile.ZipFile(
            archive,
            "w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=9,
        ) as handle:
            for path in app.rglob("*"):
                if path.is_file():
                    handle.write(path, arcname=str(path.relative_to(DIST)))

    dmg = DIST / (
        f"betabrite-controller-{__version__}-macos-{arch}.dmg"
    )
    if shutil.which("hdiutil"):
        staging = ROOT / "build" / "native-dmg"
        if staging.exists():
            shutil.rmtree(staging)
        staging.mkdir(parents=True)
        shutil.copytree(app, staging / app.name, symlinks=True)
        run(
            [
                "hdiutil",
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
        shutil.rmtree(app)
        return [archive, dmg]

    shutil.rmtree(app)
    return [archive]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the deployment command without compiling.",
    )
    args = parser.parse_args()

    target = platform_name()
    arch = architecture_name()
    DIST.mkdir(parents=True, exist_ok=True)

    deploy = shutil.which("pyside6-deploy")
    if not deploy:
        raise SystemExit(
            "pyside6-deploy was not found. Install the desktop extra first."
        )

    command = [
        deploy,
        str(ENTRYPOINT),
        "-f",
        "--name",
        APP_NAME,
        "--extra-ignore-dirs",
        ".git,.venv,build,dist,__pycache__",
    ]

    if args.dry_run:
        print("Target:", target)
        print("Architecture:", arch)
        print("Version:", __version__)
        print("+", " ".join(command))
        return 0

    for stale in [
        ROOT / f"{APP_NAME}.exe",
        ROOT / f"{APP_NAME}.bin",
        ROOT / f"{APP_NAME}.app",
    ]:
        if stale.is_dir():
            shutil.rmtree(stale)
        elif stale.exists():
            stale.unlink()

    started_at = time.time()
    run(command)

    if target == "windows":
        source = newest_candidate(
            [f"{APP_NAME}.exe", "*.exe"],
            started_at,
        )
    elif target == "macos":
        source = newest_candidate(
            [f"{APP_NAME}.app", "*.app"],
            started_at,
        )
    else:
        source = newest_candidate(
            [f"{APP_NAME}.bin", "*.bin"],
            started_at,
        )

    smoke_test_native(source, target)

    if target == "windows":
        artifacts = package_windows(source, arch)
    elif target == "macos":
        artifacts = package_macos(source, arch)
    else:
        artifacts = package_linux(source, arch)

    checksum_file = write_checksums(artifacts, target)
    artifacts.append(checksum_file)

    print("\nNative artifacts:")
    for artifact in artifacts:
        print(f"  {artifact.relative_to(ROOT)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
