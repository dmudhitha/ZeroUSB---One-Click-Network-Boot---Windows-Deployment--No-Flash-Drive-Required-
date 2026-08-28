#!/usr/bin/env bash
# ==============================================================================
# Script: start-server.sh
# Purpose: Starts ZeroUSB Multi-OS Network Installer (ProxyDHCP, TFTP, HTTP, Samba)
# ==============================================================================

set -euo pipefail

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG_DIR="${BASE_DIR}/config"
SRV_DIR="${BASE_DIR}/srv"
LOGS_DIR="${BASE_DIR}/logs"
PID_DIR="${BASE_DIR}/.run"

mkdir -p "${LOGS_DIR}" "${PID_DIR}" "${SRV_DIR}/tftp" "${SRV_DIR}/http/boot" "${SRV_DIR}/samba"

echo "================================================================="
echo "        Starting ZeroUSB Network OS Deployment Server            "
echo "================================================================="

# Detect primary interface and IP
INTERFACE=$(ip -4 route get 8.8.8.8 2>/dev/null | awk '{print $5; exit}' || echo "enp3s0")
SERVER_IP=$(ip -4 route get 8.8.8.8 2>/dev/null | awk '{print $7; exit}' || echo "192.168.1.41")
SUBNET=$(echo "${SERVER_IP}" | awk -F. '{print $1"."$2"."$3".0"}')

echo "[*] Detected Network Interface: ${INTERFACE}"
echo "[*] Server IP:                  ${SERVER_IP}"
echo "[*] Local Subnet:               ${SUBNET}/24"

# 1. Ensure UFW allows PXE broadcast ports
if command -v ufw &>/dev/null; then
    if sudo ufw status | grep -q "active"; then
        echo "[+] Configuring UFW Firewall for PXE broadcast..."
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

# 2. Update iPXE script
echo "[+] Preparing iPXE boot script..."
sed -e "s|set server_ip .*|set server_ip ${SERVER_IP}|g" "${CONFIG_DIR}/boot.ipxe" > "${SRV_DIR}/http/boot.ipxe"
cp -v "${SRV_DIR}/http/boot.ipxe" "${SRV_DIR}/tftp/boot.ipxe"

# 3. Kill all previous dnsmasq processes to prevent socket conflicts
echo "[+] Clearing any previous dnsmasq instances..."
sudo killall -9 dnsmasq 2>/dev/null || true
sudo systemctl stop dnsmasq 2>/dev/null || true
sleep 0.5

# 4. Configure and run Dnsmasq (ProxyDHCP + TFTP)
RUNTIME_DNSMASQ="/tmp/dnsmasq_network_installer.conf"
cat << EOF > "${RUNTIME_DNSMASQ}"
# ZeroUSB Dynamic Runtime Config
port=0
log-dhcp
interface=${INTERFACE}

# ProxyDHCP mode on local host IP (matches physical interface enp3s0)
dhcp-range=${SERVER_IP},proxy

# TFTP Server Configuration
enable-tftp
tftp-root=${SRV_DIR}/tftp

# Client Architecture Detection
dhcp-match=set:bios,option:client-arch,0
dhcp-match=set:efi-x86,option:client-arch,6
dhcp-match=set:efi-x64,option:client-arch,7
dhcp-match=set:efi-x64,option:client-arch,9
dhcp-match=set:efi-arm64,option:client-arch,11

# iPXE User-Class matching
dhcp-userclass=set:ipxe,iPXE

# Explicit DHCP Options 66 (TFTP Server) and 67 (Boot filename) for Intel Option ROMs
dhcp-option=66,${SERVER_IP}

# If client is ALREADY running iPXE, deliver the HTTP menu script
dhcp-option=tag:ipxe,67,http://${SERVER_IP}:8080/boot.ipxe

# If client is initial PXE ROM (!ipxe), deliver the TFTP bootloader binary
dhcp-option=tag:!ipxe,tag:bios,67,undionly.kpxe
dhcp-option=tag:!ipxe,tag:efi-x64,67,ipxe.efi
dhcp-option=tag:!ipxe,tag:efi-x86,67,ipxe32.efi
dhcp-option=tag:!ipxe,tag:efi-arm64,67,ipxe-arm64.efi

# PXE Service & Prompt Definitions (REQUIRED for Intel PXE ROM port 4011 ProxyDHCP)
pxe-prompt="ZeroUSB Network Boot", 0
pxe-service=x86PC,"ZeroUSB BIOS Bootloader",undionly.kpxe
pxe-service=PC98,"ZeroUSB PC98",undionly.kpxe
pxe-service=IA64_EFI,"ZeroUSB IA64",ipxe.efi
pxe-service=Alpha,"ZeroUSB Alpha",undionly.kpxe
pxe-service=Arc_x86,"ZeroUSB Arc",undionly.kpxe
pxe-service=Intel_Lean_Client,"ZeroUSB Lean",undionly.kpxe
pxe-service=IA32_EFI,"ZeroUSB UEFI 32",ipxe32.efi
pxe-service=BC_EFI,"ZeroUSB UEFI 64 (BC)",ipxe.efi
pxe-service=Xscale_EFI,"ZeroUSB Xscale",ipxe.efi
pxe-service=X86-64_EFI,"ZeroUSB UEFI 64",ipxe.efi
pxe-service=ARM64_EFI,"ZeroUSB ARM64",ipxe-arm64.efi

# If client is already running iPXE, load boot.ipxe directly over HTTP
dhcp-boot=tag:ipxe,http://${SERVER_IP}:8080/boot.ipxe

# If client is initial UEFI/BIOS PXE, deliver the appropriate iPXE binary via TFTP
dhcp-boot=tag:!ipxe,tag:bios,undionly.kpxe,${SERVER_IP},${SERVER_IP}
dhcp-boot=tag:!ipxe,tag:efi-x64,ipxe.efi,${SERVER_IP},${SERVER_IP}
dhcp-boot=tag:!ipxe,tag:efi-x86,ipxe32.efi,${SERVER_IP},${SERVER_IP}
dhcp-boot=tag:!ipxe,tag:efi-arm64,ipxe-arm64.efi,${SERVER_IP},${SERVER_IP}

# Fallback default for BIOS Intel PXE ROMs
dhcp-boot=tag:bios,undionly.kpxe,${SERVER_IP},${SERVER_IP}
# Fallback default for UEFI Intel PXE ROMs
dhcp-boot=tag:efi-x64,ipxe.efi,${SERVER_IP},${SERVER_IP}
# General fallback
dhcp-boot=undionly.kpxe,${SERVER_IP},${SERVER_IP}
EOF

echo "[+] Starting dnsmasq (ProxyDHCP port 4011 & TFTP port 69)..."
sudo dnsmasq --conf-file="${RUNTIME_DNSMASQ}" --no-daemon --log-dhcp > "${LOGS_DIR}/dnsmasq.log" 2>&1 &
DNSMASQ_PID=$!
echo "${DNSMASQ_PID}" | sudo tee "${PID_DIR}/dnsmasq.pid" >/dev/null

# 5. Start High-Speed HTTP Server on port 8080
if [ -f "${PID_DIR}/http.pid" ]; then
    kill -9 "$(cat "${PID_DIR}/http.pid")" 2>/dev/null || true
    rm -f "${PID_DIR}/http.pid"
fi

echo "[+] Starting High-Speed HTTP Streaming Server on port 8080..."
python3 "${SCRIPT_DIR}/http_server.py" 8080 > "${LOGS_DIR}/http.log" 2>&1 &
HTTP_PID=$!
echo "${HTTP_PID}" > "${PID_DIR}/http.pid"

# 6. Configure Samba Shares for all staged OS folders
echo "[+] Ensuring Samba (smbd) service is running..."
for share_dir in "${SRV_DIR}/samba"/*; do
    if [ -d "${share_dir}" ]; then
        share_name=$(basename "${share_dir}")
        if ! grep -q "\[${share_name}\]" /etc/samba/smb.conf 2>/dev/null; then
            echo "[+] Adding Samba share [${share_name}] -> ${share_dir}..."
            sudo bash -c "cat >> /etc/samba/smb.conf << EOF

[${share_name}]
   path = ${share_dir}
   browseable = yes
   read only = yes
   guest ok = yes
   guest only = yes
   force user = nobody
EOF"
        fi
    fi
done
sudo systemctl restart smbd

echo ""
echo "================================================================="
echo "   🎉 ZeroUSB Server is LIVE & READY FOR BOOTING!               "
echo "================================================================="
echo " Server IP:         ${SERVER_IP}"
echo " Interface:         ${INTERFACE}"
echo " ProxyDHCP Port:    UDP 4011 (Active)"
echo " TFTP Bootloader:   ipxe.efi / undionly.kpxe (UDP 69)"
echo " HTTP Endpoint:     http://${SERVER_IP}:8080"
echo " Samba Shares:      \\\\${SERVER_IP}\\<os_name>"
echo "-----------------------------------------------------------------"
echo " Client PC Instructions:"
echo " 1. Connect the target PC via Ethernet cable to the router/switch."
echo " 2. Power on the PC and press F12 (or F11/F8) for the Boot Menu."
echo " 3. Select 'UEFI Network Boot' / 'PXE IPv4'."
echo " 4. ZeroUSB Multi-Boot Menu will appear on screen!"
echo "================================================================="
