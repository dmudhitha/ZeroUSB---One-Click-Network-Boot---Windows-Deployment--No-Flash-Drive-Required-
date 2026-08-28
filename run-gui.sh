#!/usr/bin/env bash
# ==============================================================================
# Script: run-gui.sh
# Purpose: Launches ZeroUSB Desktop GUI Cleanly (X11/Wayland Compatible)
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

export DISPLAY="${DISPLAY:-:0}"
if [ -n "${XAUTHORITY:-}" ]; then
    export XAUTHORITY="${XAUTHORITY}"
fi

python3 "${SCRIPT_DIR}/app.py" "$@"
