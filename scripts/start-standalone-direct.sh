#!/usr/bin/env bash
# ==============================================================================
# Script: start-standalone-direct.sh
# Purpose: Starts ZeroUSB in Standalone Full Authoritative DHCP Mode
# (Supports CSM / Legacy BIOS Mode & Native UEFI Mode over Direct Cable)
# ==============================================================================

set -euo pipefail

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG_DIR="${BASE_DIR}/config"
SRV_DIR="${BASE_DIR}/srv"
LOGS_DIR="${BASE_DIR}/logs"
PID_DIR="${BASE_DIR}/.run"

mkdir -p "${LOGS_DIR}" "${PID_DIR}" "${SRV_DIR}/tftp" "${SRV_DIR}/http/boot" "${SRV_DIR}/samba"

echo "================================================================="
echo "   ⚡ ZeroUSB - Direct PC-to-PC Server (CSM & UEFI Supported)   "
echo "================================================================="

INTERFACE="enp3s0"
SERVER_IP="192.168.42.1"
IP_PREFIX="192.168.42"

# 1. Bring interface UP and assign static IP 192.168.42.1
echo "[+] Configuring ${INTERFACE} with static IP ${SERVER_IP}/24 for Direct Link..."
sudo ip link set "${INTERFACE}" up
sudo ip addr flush dev "${INTERFACE}" 2>/dev/null || true
sudo ip addr add "${SERVER_IP}/24" dev "${INTERFACE}" 2>/dev/null || true

echo "[*] Network Interface:  ${INTERFACE}"
echo "[*] Host Static IP:     ${SERVER_IP}"
echo "[*] DHCP Leases Pool:   ${IP_PREFIX}.150 - ${IP_PREFIX}.199"

# 2. Allow all deployment traffic and TFTP dynamic ports on interface
sudo modprobe nf_conntrack_tftp 2>/dev/null || true
if command -v ufw &>/dev/null; then
    if sudo ufw status | grep -q "active"; then
        echo "[+] Configuring firewall rules for ${INTERFACE}..."
        sudo ufw allow in on "${INTERFACE}" to any &>/dev/null || true
        sudo ufw allow 67/udp &>/dev/null || true
        sudo ufw allow 68/udp &>/dev/null || true
        sudo ufw allow 69/udp &>/dev/null || true
        sudo ufw allow 4011/udp &>/dev/null || true
        sudo ufw allow 8080/tcp &>/dev/null || true
        sudo ufw allow 445/tcp &>/dev/null || true
        sudo ufw allow 139/tcp &>/dev/null || true
        sudo ufw allow 137/udp &>/dev/null || true
        sudo ufw allow 138/udp &>/dev/null || true
    fi
fi

# 3. Synchronize boot assets
echo "[+] Synchronizing boot assets for CSM and UEFI..."
python3 -c "
from pathlib import Path
import sys
sys.path.insert(0, '${BASE_DIR}')
from backend.os_manager import OSManager
mgr = OSManager(Path('${BASE_DIR}'))
mgr.generate_ipxe_menu('${SERVER_IP}', 8080)
" 2>/dev/null || true

cp -v "${SRV_DIR}/http/boot.ipxe" "${SRV_DIR}/tftp/boot.ipxe" 2>/dev/null || true

# 4. Clean any existing dnsmasq
sudo killall -9 dnsmasq 2>/dev/null || true
sudo systemctl stop dnsmasq 2>/dev/null || true
sleep 0.5

# 5. Configure Dnsmasq as Primary Authoritative DHCP Server
RUNTIME_DNSMASQ="/tmp/dnsmasq_standalone_installer.conf"
cat << EOF > "${RUNTIME_DNSMASQ}"
port=0
log-dhcp
user=root
interface=${INTERFACE}

# Primary Authoritative DHCP Server for Direct Cable
dhcp-authoritative
dhcp-range=${IP_PREFIX}.150,${IP_PREFIX}.199,255.255.255.0,1h
dhcp-option=option:router,${SERVER_IP}
dhcp-option=option:dns-server,${SERVER_IP}

# High-Performance TFTP Server
enable-tftp
tftp-root=${SRV_DIR}/tftp
tftp-max=1000

# Client Architecture Detection
dhcp-match=set:bios,option:client-arch,0
dhcp-match=set:efi-x86,option:client-arch,6
dhcp-match=set:efi-x64,option:client-arch,7
dhcp-match=set:efi-x64,option:client-arch,9
dhcp-match=set:efi-arm64,option:client-arch,11

# Match iPXE via Option 175 and User-Class
dhcp-match=set:ipxe,175
dhcp-userclass=set:ipxe,iPXE

# TFTP Server Option 66
dhcp-option=66,${SERVER_IP}

# Boot file mapping (Direct & Fast Chaining):
# 1. When iPXE boots (tag:ipxe), chainload boot.ipxe directly
dhcp-boot=tag:ipxe,boot.ipxe,${SERVER_IP},${SERVER_IP}
dhcp-option=tag:ipxe,67,http://${SERVER_IP}:8080/boot.ipxe

# 2. When CSM / Legacy BIOS PXE ROM boots (tag:!ipxe, tag:bios), deliver undionly.kpxe
dhcp-boot=tag:!ipxe,tag:bios,undionly.kpxe,${SERVER_IP},${SERVER_IP}
dhcp-option=tag:!ipxe,tag:bios,67,undionly.kpxe

# 3. When Native UEFI PXE ROM boots (tag:!ipxe, tag:efi-x64), deliver ipxe.efi
dhcp-boot=tag:!ipxe,tag:efi-x64,ipxe.efi,${SERVER_IP},${SERVER_IP}
dhcp-option=tag:!ipxe,tag:efi-x64,67,ipxe.efi
EOF

echo "[+] Starting Standalone Authoritative DHCP + TFTP..."
sudo dnsmasq --conf-file="${RUNTIME_DNSMASQ}" --no-daemon --log-dhcp > "${LOGS_DIR}/dnsmasq.log" 2>&1 &
DNSMASQ_PID=$!
echo "${DNSMASQ_PID}" | sudo tee "${PID_DIR}/dnsmasq.pid" >/dev/null

# 6. Start HTTP Server
if [ -f "${PID_DIR}/http.pid" ]; then
    kill -9 "$(cat "${PID_DIR}/http.pid")" 2>/dev/null || true
    rm -f "${PID_DIR}/http.pid"
fi
echo "[+] Starting High-Speed HTTP Streaming Server on port 8080..."
python3 "${SCRIPT_DIR}/http_server.py" 8080 > "${LOGS_DIR}/http.log" 2>&1 &
HTTP_PID=$!
echo "${HTTP_PID}" > "${PID_DIR}/http.pid"

# 7. Ensure Samba is running
sudo systemctl restart smbd

echo ""
echo "================================================================="
echo "   🎉 ZeroUSB Server is LIVE with Full CSM + UEFI Support!       "
echo "================================================================="
echo " Mode:            Direct Cable Authoritative Server"
echo " Host IP:         ${SERVER_IP}"
echo " CSM / BIOS:      Supported (undionly.kpxe / wimboot.i386)"
echo " UEFI 64-bit:     Supported (ipxe.efi / wimboot.x86_64)"
echo " Wire Speed:      Gigabit (1000 Mbps / ~110 MB/s)"
echo " HTTP Endpoint:   http://${SERVER_IP}:8080"
echo " Samba Share:     \\\\${SERVER_IP}\\win7"
echo "================================================================="
