#!/usr/bin/env bash
# ==============================================================================
# Script: stop-server.sh
# Purpose: Stops all running background services for Network Installer
# ==============================================================================

set -euo pipefail

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_DIR="${BASE_DIR}/.run"

echo "================================================================="
echo "        Stopping Windows PXE Network Installer Server            "
echo "================================================================="

if [ -f "${PID_DIR}/dnsmasq.pid" ]; then
    PID=$(cat "${PID_DIR}/dnsmasq.pid")
    echo "[*] Stopping dnsmasq (PID: ${PID})..."
    sudo kill -9 "${PID}" 2>/dev/null || true
    rm -f "${PID_DIR}/dnsmasq.pid"
fi

if [ -f "${PID_DIR}/http.pid" ]; then
    PID=$(cat "${PID_DIR}/http.pid")
    echo "[*] Stopping HTTP Server (PID: ${PID})..."
    kill -9 "${PID}" 2>/dev/null || true
    rm -f "${PID_DIR}/http.pid"
fi

echo "[✓] All Network Installer background services have been stopped."
