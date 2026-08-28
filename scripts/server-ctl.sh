#!/usr/bin/env bash
# ==============================================================================
# Script: server-ctl.sh
# Purpose: High-privilege controller for Dnsmasq, Firewall & Samba (1 Prompt)
# ==============================================================================

set -u

ACTION="${1:-status}"
CONF_FILE="${2:-/tmp/dnsmasq_gui_runtime.conf}"
INTERFACE="${3:-enp3s0}"
SERVER_IP="${4:-192.168.42.1}"

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

case "${ACTION}" in
    start)
        # Safeguard: NEVER touch or reassign a Wi-Fi interface!
        if [[ "${INTERFACE}" =~ ^(wl|wlan|wlx) ]]; then
            echo "[ERROR] Refusing to reconfigure wireless interface ${INTERFACE} for PXE!" >&2
            exit 1
        fi

        # 0. Tell NetworkManager to stop managing this interface during PXE serving
        if command -v nmcli &>/dev/null; then
            nmcli device set "${INTERFACE}" managed no 2>/dev/null || true
        fi

        # 1. Bring wired interface UP and ensure IP is cleanly assigned
        ip link set "${INTERFACE}" up 2>/dev/null || true
        ip addr flush dev "${INTERFACE}" 2>/dev/null || true
        ip addr add "${SERVER_IP}/24" dev "${INTERFACE}" 2>/dev/null || true

        # 2. Ensure Samba share folders have full read/traverse permissions
        chmod -R a+rX "${BASE_DIR}/srv/samba" 2>/dev/null || true

        # 3. Optimize /etc/samba/smb.conf for Universal Compatibility (Win7/Win10/Win11)
        if [ -f /etc/samba/smb.conf ]; then
            if ! grep -q "server min protocol = NT1" /etc/samba/smb.conf; then
                sed -i '/\[global\]/a \   server min protocol = NT1\n   ntlm auth = yes\n   lanman auth = yes\n   map to guest = Bad User' /etc/samba/smb.conf 2>/dev/null || true
            fi
            # Ensure force user = mudhitha for shares
            sed -i 's/force user = nobody/force user = mudhitha/g' /etc/samba/smb.conf 2>/dev/null || true
        fi

        # 4. Allow firewall ports & TFTP conntrack
        modprobe nf_conntrack_tftp 2>/dev/null || true
        if command -v ufw &>/dev/null; then
            if ufw status 2>/dev/null | grep -q "active"; then
                ufw allow in on "${INTERFACE}" to any &>/dev/null || true
                ufw allow 67/udp &>/dev/null || true
                ufw allow 68/udp &>/dev/null || true
                ufw allow 69/udp &>/dev/null || true
                ufw allow 4011/udp &>/dev/null || true
                ufw allow 8080/tcp &>/dev/null || true
                ufw allow 445/tcp &>/dev/null || true
                ufw allow 139/tcp &>/dev/null || true
                ufw allow 137/udp &>/dev/null || true
                ufw allow 138/udp &>/dev/null || true
            fi
        fi

        # 5. Clean ONLY previous ZeroUSB instances (NEVER kill host system dnsmasq.service)
        if [ -f "${BASE_DIR}/.run/dnsmasq.pid" ]; then
            OLD_PID=$(cat "${BASE_DIR}/.run/dnsmasq.pid" 2>/dev/null || true)
            if [ -n "${OLD_PID}" ] && kill -0 "${OLD_PID}" 2>/dev/null; then
                kill -9 "${OLD_PID}" 2>/dev/null || true
            fi
            rm -f "${BASE_DIR}/.run/dnsmasq.pid"
        fi
        for p in $(pgrep -x dnsmasq 2>/dev/null || true); do
            if grep -q "dnsmasq_gui_runtime.conf" "/proc/${p}/cmdline" 2>/dev/null; then
                kill -9 "${p}" 2>/dev/null || true
            fi
        done

        if command -v systemctl &>/dev/null; then
            systemctl is-active dnsmasq &>/dev/null || systemctl start dnsmasq 2>/dev/null || true
        fi
        systemctl restart smbd 2>/dev/null || true
        sleep 0.3

        # 6. Launch Dnsmasq in foreground with full logging to file
        echo "[$(date)] Starting dnsmasq with config: ${CONF_FILE} on ${INTERFACE} (${SERVER_IP})" >> /tmp/dnsmasq_runtime.log
        mkdir -p "${BASE_DIR}/.run"
        dnsmasq --conf-file="${CONF_FILE}" --no-daemon --log-dhcp >> /tmp/dnsmasq_runtime.log 2>&1 &
        DNS_PID=$!
        echo "${DNS_PID}" > "${BASE_DIR}/.run/dnsmasq.pid"
        wait "${DNS_PID}"
        ;;

    stop)
        if [ -f "${BASE_DIR}/.run/dnsmasq.pid" ]; then
            OLD_PID=$(cat "${BASE_DIR}/.run/dnsmasq.pid" 2>/dev/null || true)
            if [ -n "${OLD_PID}" ] && kill -0 "${OLD_PID}" 2>/dev/null; then
                kill -9 "${OLD_PID}" 2>/dev/null || true
            fi
            rm -f "${BASE_DIR}/.run/dnsmasq.pid"
        fi
        for p in $(pgrep -x dnsmasq 2>/dev/null || true); do
            if grep -q "dnsmasq_gui_runtime.conf" "/proc/${p}/cmdline" 2>/dev/null; then
                kill -9 "${p}" 2>/dev/null || true
            fi
        done
        pkill -f "http_server.py" 2>/dev/null || true
        pkill -f "http.server 8080" 2>/dev/null || true
        if command -v nmcli &>/dev/null; then
            nmcli device set "${INTERFACE}" managed yes 2>/dev/null || true
        fi
        # Ensure host system DNS resolver remains running
        if command -v systemctl &>/dev/null; then
            systemctl is-active dnsmasq &>/dev/null || systemctl start dnsmasq 2>/dev/null || true
        fi
        echo "STOPPED"
        ;;

    status)
        RUNNING=0
        for p in $(pgrep -x dnsmasq 2>/dev/null || true); do
            if grep -q "dnsmasq_gui_runtime.conf" "/proc/${p}/cmdline" 2>/dev/null; then
                RUNNING=1
                break
            fi
        done
        [ "${RUNNING}" -eq 1 ] && echo "RUNNING" || echo "STOPPED"
        ;;

    *)
        echo "Usage: $0 {start|stop|status} [conf_file] [interface] [server_ip]"
        exit 1
        ;;
esac
