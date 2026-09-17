#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ $# -gt 1 ]]; then
    echo "Usage: $0 [vVERSION]" >&2
    exit 2
fi

if [[ $# -eq 1 ]]; then
    VERSION="$1"
else
    PACKAGE_VERSION="$(
        cd "$ROOT"
        python3 -c 'from betabrite_controller import __version__; print(__version__)'
    )"
    VERSION="v${PACKAGE_VERSION}"
fi

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
copy_file pyproject.toml
copy_file INSTALL-BETABRITE.desktop
copy_exec install.sh
copy_exec uninstall.sh
copy_exec betabrite
copy_exec betabrite-gui

cp -a "$ROOT/betabrite_controller" "$STAGE/"
cp -a "$ROOT/packaging" "$STAGE/"
cp -a "$ROOT/docs" "$STAGE/"

find "$STAGE" -type d \( -name __pycache__ -o -name '*.egg-info' \) -prune -exec rm -rf {} +
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

printf 'Built source release artifacts in %s\n' "$DIST"
