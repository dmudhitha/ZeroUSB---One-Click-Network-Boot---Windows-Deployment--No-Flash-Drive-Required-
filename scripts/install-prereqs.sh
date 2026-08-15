#!/usr/bin/env bash
# ==============================================================================
# Script: install-prereqs.sh
# Purpose: Installs dependencies and downloads iPXE and wimboot binaries
# ==============================================================================

set -euo pipefail

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRV_TFTP="${BASE_DIR}/srv/tftp"
SRV_HTTP_BOOT="${BASE_DIR}/srv/http/boot"
SRV_SAMBA="${BASE_DIR}/srv/samba/windows"

echo "================================================================="
echo "   Windows Network Installer - Dependency & Bootloader Setup    "
echo "================================================================="

# Create required directories
mkdir -p "${SRV_TFTP}" "${SRV_HTTP_BOOT}" "${SRV_SAMBA}"

# Check for apt and install packages
if command -v apt-get &>/dev/null; then
    echo "[+] Installing system dependencies (dnsmasq, samba, wimtools, 7zip, ipxe)..."
    sudo apt-get update -y
    sudo apt-get install -y dnsmasq samba wimtools 7zip curl ipxe ipxe-qemu
else
    echo "[!] Non-Debian/Ubuntu system detected. Please ensure dnsmasq, samba, wimtools, and curl are installed."
fi

# Copy system ipxe binaries if available, or download
echo "[+] Setting up iPXE binaries in TFTP root (${SRV_TFTP})..."
if [ -f "/usr/lib/ipxe/ipxe.efi" ]; then
    cp -v "/usr/lib/ipxe/ipxe.efi" "${SRV_TFTP}/"
fi
if [ -f "/usr/lib/ipxe/undionly.kpxe" ]; then
    cp -v "/usr/lib/ipxe/undionly.kpxe" "${SRV_TFTP}/"
fi
if [ -f "/usr/lib/ipxe/ipxe32.efi" ]; then
    cp -v "/usr/lib/ipxe/ipxe32.efi" "${SRV_TFTP}/"
fi

# Download latest wimboot binary
echo "[+] Downloading latest wimboot to ${SRV_HTTP_BOOT}/wimboot..."
curl -sSL -o "${SRV_HTTP_BOOT}/wimboot" "https://github.com/ipxe/wimboot/releases/latest/download/wimboot"
chmod 644 "${SRV_HTTP_BOOT}/wimboot"

echo "[✓] Bootloaders and tools installed successfully!"
echo "    TFTP Directory: ${SRV_TFTP}"
echo "    HTTP Boot Dir:  ${SRV_HTTP_BOOT}"
echo "    Samba Share:    ${SRV_SAMBA}"
