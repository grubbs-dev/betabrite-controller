#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="${1:-v1.0.0}"
NAME="betabrite-controller-${VERSION}"
DIST="$ROOT/dist"
STAGE="$DIST/$NAME"

rm -rf "$DIST"
mkdir -p "$STAGE"

copy_file() {
    install -Dm644 "$ROOT/$1" "$STAGE/$1"
}

copy_exec() {
    install -Dm755 "$ROOT/$1" "$STAGE/$1"
}

copy_file README.md
copy_file CHANGELOG.md
copy_file requirements.txt
copy_file INSTALL-BETABRITE.desktop
copy_exec install.sh
copy_exec uninstall.sh
copy_exec betabrite
copy_exec betabrite-gui

cp -a "$ROOT/betabrite_controller" "$STAGE/"
cp -a "$ROOT/packaging" "$STAGE/"
cp -a "$ROOT/docs" "$STAGE/"

find "$STAGE" -type d -name __pycache__ -prune -exec rm -rf {} +
find "$STAGE" -type f -name '*.pyc' -delete

(
    cd "$DIST"
    tar -czf "$NAME.tar.gz" "$NAME"

    python3 - "$NAME" "$NAME.zip" <<'PY'
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile
import sys

root = Path(sys.argv[1])
archive = Path(sys.argv[2])

with ZipFile(archive, "w", ZIP_DEFLATED) as zf:
    for path in sorted(root.rglob("*")):
        if path.is_file():
            zf.write(path, path)
PY

    sha256sum "$NAME.tar.gz" "$NAME.zip" > SHA256SUMS
)

printf 'Built release artifacts in %s\n' "$DIST"
