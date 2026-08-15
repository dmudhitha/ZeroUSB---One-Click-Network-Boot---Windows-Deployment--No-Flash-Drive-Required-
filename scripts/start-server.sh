#!/usr/bin/env bash
# ==============================================================================
# Script: start-server.sh
# Purpose: Starts all Network Installer services (ProxyDHCP, TFTP, HTTP, Samba)
# ==============================================================================

set -euo pipefail

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG_DIR="${BASE_DIR}/config"
SRV_DIR="${BASE_DIR}/srv"
LOGS_DIR="${BASE_DIR}/logs"
PID_DIR="${BASE_DIR}/.run"

mkdir -p "${LOGS_DIR}" "${PID_DIR}" "${SRV_DIR}/tftp" "${SRV_DIR}/http/boot" "${SRV_DIR}/samba/windows"

echo "================================================================="
echo "        Starting Windows PXE Network Installer Server            "
echo "================================================================="

# Detect primary interface and IP
INTERFACE=$(ip -4 route get 8.8.8.8 2>/dev/null | awk '{print $5; exit}' || echo "enp3s0")
SERVER_IP=$(ip -4 route get 8.8.8.8 2>/dev/null | awk '{print $7; exit}' || echo "192.168.1.41")
SUBNET=$(echo "${SERVER_IP}" | awk -F. '{print $1"."$2"."$3".0"}')

echo "[*] Detected Network Interface: ${INTERFACE}"
echo "[*] Server IP:                  ${SERVER_IP}"
echo "[*] Local Subnet:               ${SUBNET}/24"

# 1. Update iPXE script
echo "[+] Preparing iPXE boot script..."
sed -e "s|set server_ip .*|set server_ip ${SERVER_IP}|g" "${CONFIG_DIR}/boot.ipxe" > "${SRV_DIR}/http/boot.ipxe"
cp -v "${SRV_DIR}/http/boot.ipxe" "${SRV_DIR}/tftp/boot.ipxe"

# 2. Configure and run Dnsmasq (ProxyDHCP + TFTP)
RUNTIME_DNSMASQ="/tmp/dnsmasq_network_installer.conf"
cat << EOF > "${RUNTIME_DNSMASQ}"
port=0
interface=${INTERFACE}
bind-interfaces
dhcp-range=${SUBNET},proxy,255.255.255.0
enable-tftp
tftp-root=${SRV_DIR}/tftp

dhcp-match=set:bios,option:client-arch,0
dhcp-match=set:efi-x86,option:client-arch,6
dhcp-match=set:efi-x64,option:client-arch,7
dhcp-match=set:efi-x64,option:client-arch,9
dhcp-match=set:efi-arm64,option:client-arch,11

dhcp-boot=tag:bios,undionly.kpxe
dhcp-boot=tag:efi-x64,ipxe.efi
dhcp-boot=tag:efi-x86,ipxe32.efi
dhcp-boot=tag:efi-arm64,ipxe-arm64.efi
EOF

# Kill any existing standalone dnsmasq instance started by this script
if [ -f "${PID_DIR}/dnsmasq.pid" ]; then
    sudo kill -9 "$(cat "${PID_DIR}/dnsmasq.pid")" 2>/dev/null || true
    rm -f "${PID_DIR}/dnsmasq.pid"
fi

# Stop system dnsmasq if running to avoid port conflict
sudo systemctl stop dnsmasq 2>/dev/null || true

echo "[+] Starting dnsmasq (ProxyDHCP & TFTP)..."
sudo dnsmasq --conf-file="${RUNTIME_DNSMASQ}" --no-daemon --log-dhcp > "${LOGS_DIR}/dnsmasq.log" 2>&1 &
DNSMASQ_PID=$!
echo "${DNSMASQ_PID}" | sudo tee "${PID_DIR}/dnsmasq.pid" >/dev/null

# 3. Start High-Speed HTTP Server on port 8080
if [ -f "${PID_DIR}/http.pid" ]; then
    kill -9 "$(cat "${PID_DIR}/http.pid")" 2>/dev/null || true
    rm -f "${PID_DIR}/http.pid"
fi

echo "[+] Starting HTTP Server on port 8080..."
python3 -m http.server 8080 --directory "${SRV_DIR}/http" > "${LOGS_DIR}/http.log" 2>&1 &
HTTP_PID=$!
echo "${HTTP_PID}" > "${PID_DIR}/http.pid"

# 4. Check Samba Service
echo "[+] Ensuring Samba (smbd) service is running..."
# Check if windows share exists in smb.conf, append if not
if ! grep -q "\[windows\]" /etc/samba/smb.conf 2>/dev/null; then
    echo "[+] Appending [windows] share configuration to /etc/samba/smb.conf..."
    sudo bash -c "cat >> /etc/samba/smb.conf << 'EOF'

[windows]
   path = ${SRV_DIR}/samba/windows
   browseable = yes
   read only = yes
   guest ok = yes
   guest only = yes
   force user = nobody
EOF"
fi
sudo systemctl restart smbd

echo ""
echo "================================================================="
echo "   🎉 Network Installer Server is LIVE & READY FOR BOOTING!      "
echo "================================================================="
echo " Server IP:         ${SERVER_IP}"
echo " Interface:         ${INTERFACE}"
echo " TFTP Bootloader:   ipxe.efi / undionly.kpxe"
echo " HTTP Endpoint:     http://${SERVER_IP}:8080"
echo " Samba Share:       \\\\${SERVER_IP}\\windows"
echo "-----------------------------------------------------------------"
echo " Client PC Instructions:"
echo " 1. Connect the target PC via Ethernet cable to this network."
echo " 2. Power on the PC and press F12 (or F11/F8) for the Boot Menu."
echo " 3. Select 'UEFI Network Boot' / 'PXE IPv4'."
echo " 4. Windows PE will load in RAM and launch Setup automatically!"
echo "================================================================="
echo " To stop the server later, run: ./scripts/stop-server.sh"
echo "================================================================="
