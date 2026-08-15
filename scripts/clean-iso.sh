#!/usr/bin/env bash
# ==============================================================================
# Script: clean-iso.sh
# Purpose: Purges extracted Windows ISO media and boot assets to free disk space
# ==============================================================================

set -euo pipefail

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRV_HTTP_BOOT="${BASE_DIR}/srv/http/boot"
SRV_SAMBA="${BASE_DIR}/srv/samba/windows"

echo "================================================================="
echo "   ZeroUSB - Purge Extracted Windows ISO Media & Staged Assets   "
echo "================================================================="

read -p "Are you sure you want to delete all extracted Windows files? (y/N): " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "[*] Operation cancelled."
    exit 0
fi

echo "[+] Deleting extracted Samba installation files in ${SRV_SAMBA}..."
rm -rf "${SRV_SAMBA}"/*
mkdir -p "${SRV_SAMBA}"

echo "[+] Deleting staged boot assets in ${SRV_HTTP_BOOT} (preserving wimboot)..."
rm -f "${SRV_HTTP_BOOT}/BCD" "${SRV_HTTP_BOOT}/bcd" "${SRV_HTTP_BOOT}/boot.sdi" "${SRV_HTTP_BOOT}/boot.wim"

echo "[✓] Extracted Windows ISO files purged successfully! Disk space freed."
echo "================================================================="
