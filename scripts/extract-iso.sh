#!/usr/bin/env bash
# ==============================================================================
# Script: extract-iso.sh
# Purpose: Extracts Windows ISO, copies boot assets, and injects network auto-mount
# Usage: ./extract-iso.sh /path/to/windows_installation.iso [SERVER_IP]
# ==============================================================================

set -euo pipefail

if [ "$#" -lt 1 ]; then
    echo "Usage: $0 <path_to_windows_iso> [server_ip]"
    echo "Example: $0 /home/user/Downloads/Win11_23H2_English_x64.iso 192.168.1.41"
    exit 1
fi

ISO_PATH="$1"
BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRV_HTTP_BOOT="${BASE_DIR}/srv/http/boot"
SRV_SAMBA="${BASE_DIR}/srv/samba/windows"

# Detect Server IP if not passed
if [ "$#" -ge 2 ]; then
    SERVER_IP="$2"
else
    SERVER_IP="$(ip -4 route get 8.8.8.8 2>/dev/null | awk '{print $7; exit}' || echo "192.168.1.41")"
fi

if [ ! -f "${ISO_PATH}" ]; then
    echo "[ERROR] ISO file not found: ${ISO_PATH}"
    exit 1
fi

echo "================================================================="
echo "   Windows ISO Network Installer Extraction & Preparation       "
echo "================================================================="
echo "ISO File:   ${ISO_PATH}"
echo "Server IP:  ${SERVER_IP}"
echo "Destination: ${SRV_SAMBA}"
echo "================================================================="

mkdir -p "${SRV_HTTP_BOOT}" "${SRV_SAMBA}"

TEMP_MOUNT="/tmp/win_iso_mount_$$"
mkdir -p "${TEMP_MOUNT}"

cleanup() {
    if mountpoint -q "${TEMP_MOUNT}"; then
        echo "[*] Unmounting temporary mount point..."
        sudo umount "${TEMP_MOUNT}" || true
    fi
    rm -rf "${TEMP_MOUNT}" "/tmp/startnet_$$.cmd" "/tmp/wim_update_$$.txt" 2>/dev/null || true
}
trap cleanup EXIT

echo "[+] Mounting ISO file..."
sudo mount -o loop,ro "${ISO_PATH}" "${TEMP_MOUNT}"

echo "[+] Copying full Windows installation files to Samba share..."
echo "    (This might take a couple of minutes depending on disk speed)..."
sudo cp -r "${TEMP_MOUNT}"/* "${SRV_SAMBA}/"
sudo chmod -R 755 "${SRV_SAMBA}"

echo "[+] Extracting WIM boot assets to ${SRV_HTTP_BOOT}..."

# Case-insensitive copy helper
find_and_copy() {
    local search_name="$1"
    local dest="$2"
    local found
    found=$(find "${TEMP_MOUNT}" -maxdepth 3 -iname "${search_name}" | head -n 1)
    if [ -n "${found}" ] && [ -f "${found}" ]; then
        echo "    Copying $(basename "${found}") -> ${dest}"
        sudo cp -v "${found}" "${dest}"
        sudo chmod 644 "${dest}"
    else
        echo "[!] Warning: Could not find ${search_name} in ISO."
    fi
}

find_and_copy "bcd" "${SRV_HTTP_BOOT}/BCD"
find_and_copy "boot.sdi" "${SRV_HTTP_BOOT}/boot.sdi"
find_and_copy "boot.wim" "${SRV_HTTP_BOOT}/boot.wim"

# Patch startnet.cmd inside boot.wim using wimlib-imagex
if command -v wimlib-imagex &>/dev/null; then
    echo "[+] Customizing Windows PE (startnet.cmd) for automatic network setup..."
    
    cat << EOF > "/tmp/startnet_$$.cmd"
@echo off
title Windows Network Setup (via ${SERVER_IP})
wpeinit

echo.
echo =================================================================
echo   Initializing Network Connection to Installer Server...
echo =================================================================
echo Waiting for DHCP / Network adapter initialization...
ping 127.0.0.1 -n 6 > nul

echo Connecting to SMB Share: \\\\${SERVER_IP}\\windows ...
net use Z: \\\\${SERVER_IP}\\windows /user:nobody ""

if exist Z:\setup.exe (
    echo.
    echo [✓] Connected successfully! Launching Windows Setup...
    echo =================================================================
    Z:\setup.exe
) else (
    echo.
    echo [!] ERROR: Z:\setup.exe was not found.
    echo Opening WinPE Command Prompt for manual troubleshooting...
    cmd.exe
)
EOF

    echo "add /tmp/startnet_$$.cmd /Windows/System32/startnet.cmd" > "/tmp/wim_update_$$.txt"

    # In standard Windows ISOs:
    # Index 1 = Microsoft Windows PE (Recovery/Tools)
    # Index 2 = Microsoft Windows Setup (WinPE with Setup)
    # We update Index 2 (or Index 1 if only 1 exists)
    NUM_IMAGES=$(wiminfo "${SRV_HTTP_BOOT}/boot.wim" | grep -i "Image Count" | awk '{print $3}' || echo "2")
    TARGET_INDEX=2
    if [ "${NUM_IMAGES}" -eq 1 ]; then
        TARGET_INDEX=1
    fi

    echo "[+] Updating startnet.cmd in boot.wim (Image Index: ${TARGET_INDEX})..."
    sudo wimlib-imagex update "${SRV_HTTP_BOOT}/boot.wim" "${TARGET_INDEX}" < "/tmp/wim_update_$$.txt"
    sudo chmod 644 "${SRV_HTTP_BOOT}/boot.wim"
    echo "[✓] boot.wim successfully patched with auto-installer script!"
else
    echo "[!] wimlib-imagex not found. Skipping startnet.cmd patch."
    echo "    (You will need to manually run 'net use Z: \\\\${SERVER_IP}\\windows /user:nobody \"\"' in WinPE)"
fi

echo "================================================================="
echo "[✓] Extraction and boot environment preparation complete!"
echo "================================================================="
