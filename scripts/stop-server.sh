#!/usr/bin/env bash
# ==============================================================================
# Script: stop-server.sh
# Purpose: Stops all running background services for ZeroUSB Multi-OS Deployer
# ==============================================================================

set -euo pipefail

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_DIR="${BASE_DIR}/.run"

echo "================================================================="
echo "        Stopping ZeroUSB PXE Network Deployment Server           "
echo "================================================================="

echo "[*] Terminating ZeroUSB dnsmasq process..."
if [ -f "${PID_DIR}/dnsmasq.pid" ]; then
    PID=$(cat "${PID_DIR}/dnsmasq.pid")
    sudo kill -9 "${PID}" 2>/dev/null || true
    rm -f "${PID_DIR}/dnsmasq.pid"
fi
for p in $(pgrep -x dnsmasq 2>/dev/null || true); do
    if grep -q "dnsmasq_gui_runtime.conf" "/proc/${p}/cmdline" 2>/dev/null; then
        sudo kill -9 "${p}" 2>/dev/null || true
    fi
done
# Ensure system DNS resolver is untouched
if command -v systemctl &>/dev/null; then
    systemctl is-active dnsmasq &>/dev/null || sudo systemctl start dnsmasq 2>/dev/null || true
fi

echo "[*] Terminating HTTP Server processes..."
if [ -f "${PID_DIR}/http.pid" ]; then
    PID=$(cat "${PID_DIR}/http.pid")
    kill -9 "${PID}" 2>/dev/null || true
    rm -f "${PID_DIR}/http.pid"
fi
pkill -f "http.server 8080" 2>/dev/null || true
pkill -f "python3 -m http.server 8080" 2>/dev/null || true

echo "[✓] All ZeroUSB background services have been successfully stopped."
