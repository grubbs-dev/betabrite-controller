"""Build AppImages using versioned, SHA-256 verified upstream tools."""
import hashlib
import os
from pathlib import Path
import subprocess
import urllib.request


TOOLS = {
    "appimagetool": (
        "https://github.com/AppImage/appimagetool/releases/download/1.9.1/appimagetool-x86_64.AppImage",
        "ed4ce84f0d9caff66f50bcca6ff6f35aae54ce8135408b3fa33abfc3cb384eb0",
    ),
    "runtime": (
        "https://github.com/AppImage/type2-runtime/releases/download/20251108/runtime-x86_64",
        "2fca8b443c92510f1483a883f60061ad09b46b978b2631c807cd873a47ec260d",
    ),
}


def build_appimage(appdir: Path, output: Path, cache: Path):
    cache.mkdir(parents=True, exist_ok=True)
    for name, (url, digest) in TOOLS.items():
        target = cache / name
        if not target.exists():
            with urllib.request.urlopen(url, timeout=120) as response:
                data = response.read()
            if hashlib.sha256(data).hexdigest() != digest:
                raise ValueError(f"Checksum mismatch for {name}")
            target.write_bytes(data)
        if hashlib.sha256(target.read_bytes()).hexdigest() != digest:
            raise ValueError(f"Checksum mismatch for cached {name}")
        target.chmod(0o755)
    env = {**os.environ, "ARCH": "x86_64", "APPIMAGE_EXTRACT_AND_RUN": "1"}
    subprocess.run([str(cache / "appimagetool"), "--runtime-file", str(cache / "runtime"),
                    str(appdir), str(output)], env=env, check=True)
    output.chmod(0o755)
    subprocess.run([str(output), "--smoke-test"], check=True,
                   env={**env, "QT_QPA_PLATFORM": "offscreen"}, timeout=120)
