#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

if [[ -n "${BETABRITE_PYTHON:-}" ]]; then
    PYTHON="$BETABRITE_PYTHON"
elif [[ -x "$ROOT/.venv/bin/python" ]]; then
    PYTHON="$ROOT/.venv/bin/python"
else
    PYTHON=python3
fi

cd "$ROOT"

PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}" \
    "$PYTHON" -m unittest discover \
    -s tests \
    -p 'test_*.py' \
    -v
