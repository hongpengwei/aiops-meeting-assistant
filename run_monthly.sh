#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "============================================================"
echo " AIOps 每月課會智能監控與類別歸因 (Monthly Meeting)"
echo "============================================================"

PYTHON_EXE="python3"
if [ -d "$SCRIPT_DIR/venv" ]; then
    PYTHON_EXE="$SCRIPT_DIR/venv/bin/python"
elif [ -d "$SCRIPT_DIR/.venv" ]; then
    PYTHON_EXE="$SCRIPT_DIR/.venv/bin/python"
fi

"$PYTHON_EXE" main.py --mode monthly "$@"
