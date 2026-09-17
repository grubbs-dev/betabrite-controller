#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

if [[ -x /opt/betabrite-controller/venv/bin/python ]]; then
    PYTHON=/opt/betabrite-controller/venv/bin/python
elif [[ -x /opt/betabrite/venv/bin/python ]]; then
    PYTHON=/opt/betabrite/venv/bin/python
else
    PYTHON=python3
fi

cd "$ROOT"

PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}" \
    "$PYTHON" -m unittest discover \
    -s tests \
    -p 'test_*.py' \
    -v
