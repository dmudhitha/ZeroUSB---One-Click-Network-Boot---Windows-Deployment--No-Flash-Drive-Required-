#!/usr/bin/env bash
# ==============================================================================
# Script: test-server.sh
# Purpose: Comprehensive Pre-flight Diagnostics for Windows Network Installer
# ==============================================================================

set -euo pipefail

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRV_TFTP="${BASE_DIR}/srv/tftp"
SRV_HTTP="${BASE_DIR}/srv/http"
SRV_SAMBA="${BASE_DIR}/srv/samba/windows"

PASS=0
FAIL=0

check_item() {
    local name="$1"
    local condition="$2"
    if eval "${condition}"; then
        echo -e "  [\033[32mPASS\033[0m] ${name}"
        PASS=$((PASS + 1))
    else
        echo -e "  [\033[31mFAIL\033[0m] ${name}"
        FAIL=$((FAIL + 1))
    fi
}

echo "================================================================="
echo "   Windows Network PXE Installer - Pre-Flight Diagnostics        "
echo "================================================================="

echo ""
echo "[1] Checking Network Interface & IP Configuration..."
SERVER_IP=$(ip -4 route get 8.8.8.8 2>/dev/null | awk '{print $7; exit}' || echo "192.168.1.41")
INTERFACE=$(ip -4 route get 8.8.8.8 2>/dev/null | awk '{print $5; exit}' || echo "enp3s0")
check_item "Server IP detected (${SERVER_IP})" "[ -n '${SERVER_IP}' ]"
check_item "Network interface UP (${INTERFACE})" "ip link show ${INTERFACE} | grep -q 'state UP'"

echo ""
echo "[2] Checking TFTP Network Bootloaders..."
check_item "ipxe.efi (UEFI x64 Bootloader)" "[ -s '${SRV_TFTP}/ipxe.efi' ]"
check_item "undionly.kpxe (Legacy BIOS Bootloader)" "[ -s '${SRV_TFTP}/undionly.kpxe' ]"
check_item "boot.ipxe (iPXE Boot Script)" "[ -s '${SRV_TFTP}/boot.ipxe' ]"

echo ""
echo "[3] Checking HTTP Stream Assets (wimboot & WinPE)..."
check_item "wimboot (Fast WIM Kernel)" "[ -s '${SRV_HTTP}/boot/wimboot' ]"
check_item "BCD (Boot Configuration Data)" "[ -s '${SRV_HTTP}/boot/BCD' ]"
check_item "boot.sdi (RAMDisk Descriptor)" "[ -s '${SRV_HTTP}/boot/boot.sdi' ]"
check_item "boot.wim (Windows PE Image)" "[ -s '${SRV_HTTP}/boot/boot.wim' ]"

echo ""
echo "[4] Checking WinPE Auto-Mount Script Injection..."
if command -v wimlib-imagex &>/dev/null && [ -f "${SRV_HTTP}/boot/boot.wim" ]; then
    HAS_STARTNET=$(wimlib-imagex dir "${SRV_HTTP}/boot/boot.wim" 2 --path=/Windows/System32 2>/dev/null | grep -i "startnet.cmd" || true)
    check_item "startnet.cmd present in boot.wim (Index 2)" "[ -n '${HAS_STARTNET}' ]"
else
    check_item "startnet.cmd present in boot.wim" "false"
fi

echo ""
echo "[5] Checking Samba Windows Setup Share Media..."
check_item "setup.exe accessible" "[ -s '${SRV_SAMBA}/setup.exe' ]"
check_item "sources directory accessible" "[ -d '${SRV_SAMBA}/sources' ]"

echo ""
echo "[6] Validating Service Configurations..."
check_item "dnsmasq.conf syntax" "dnsmasq --test --conf-file='${BASE_DIR}/config/dnsmasq.conf' &>/dev/null"
check_item "smb.conf syntax" "testparm -s '${BASE_DIR}/config/smb.conf' &>/dev/null"

echo ""
echo "================================================================="
if [ $FAIL -eq 0 ]; then
    echo -e "  \033[32m✔ ALL $PASS CHECKS PASSED!\033[0m Your server is 100% ready for PXE boot."
else
    echo -e "  \033[31m✖ $FAIL CHECKS FAILED!\033[0m Please review the missing items above."
fi
echo "================================================================="
