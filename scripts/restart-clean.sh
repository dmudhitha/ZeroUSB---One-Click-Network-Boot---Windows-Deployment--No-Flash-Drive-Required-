#!/usr/bin/env bash
# ==============================================================================
# Script: restart-clean.sh
# Purpose: Forcefully kills all orphaned dnsmasq/http processes and starts fresh
# ==============================================================================

set -euo pipefail

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "================================================================="
echo "   ZeroUSB - Clean Restart & PXE-E53 Fix                         "
echo "================================================================="

echo "[1] Forcefully killing all old dnsmasq instances..."
sudo killall -9 dnsmasq 2>/dev/null || true
sudo systemctl stop dnsmasq 2>/dev/null || true
sleep 1

echo "[2] Ensuring firewall allows all PXE broadcast ports..."
sudo ufw allow 67/udp &>/dev/null || true
sudo ufw allow 68/udp &>/dev/null || true
sudo ufw allow 69/udp &>/dev/null || true
sudo ufw allow 4011/udp &>/dev/null || true
sudo ufw allow 8080/tcp &>/dev/null || true
sudo ufw allow 445/tcp &>/dev/null || true
sudo ufw allow 139/tcp &>/dev/null || true
sudo ufw allow 137/udp &>/dev/null || true
sudo ufw allow 138/udp &>/dev/null || true

echo "[3] Starting fresh ZeroUSB Network Server..."
bash "${BASE_DIR}/scripts/start-server.sh"
