#!/usr/bin/env python3
"""
==============================================================================
 ZeroUSB - Live Network Boot Packet Monitor & Sniffer
 Monitors raw network traffic on enp3s0 for:
 - DHCP/BOOTP Broadcasts (UDP 67/68)
 - ProxyDHCP Requests (UDP 4011)
 - TFTP Bootloader Requests (UDP 69)
 - HTTP Kernel/WinPE Streaming (TCP 8080)
 - ARP Discovery Packets
 - ICMP Pings
==============================================================================
"""

import os
import sys
import socket
import struct
import time
from datetime import datetime

# ANSI Colors
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RED = "\033[91m"
BOLD = "\033[1m"
RESET = "\033[0m"

def mac_addr(bytes_addr):
    return ':'.join(f'{b:02x}' for b in bytes_addr)

def main():
    if os.geteuid() != 0:
        print(f"{RED}[!] Error: Live packet monitoring requires root (sudo) privileges.{RESET}")
        print(f"Run: {BOLD}sudo python3 {sys.argv[0]}{RESET}")
        sys.exit(1)

    interface = "enp3s0"
    print(f"\n{BOLD}{CYAN}================================================================={RESET}")
    print(f"{BOLD}{CYAN}   ⚡ ZeroUSB — Live Network Boot Packet Sniffer & Monitor        {RESET}")
    print(f"{BOLD}{CYAN}================================================================={RESET}")
    print(f"[*] Listening for incoming client boot traffic on: {BOLD}{GREEN}{interface}{RESET}")
    print(f"[*] Watching for: {YELLOW}DHCP (67/68){RESET}, {YELLOW}ProxyDHCP (4011){RESET}, {YELLOW}TFTP (69){RESET}, {YELLOW}HTTP (8080){RESET}, {YELLOW}ARP{RESET}...")
    print(f"[*] {BOLD}Turn on your Target PC and press F12 now...{RESET}\n")

    # Create raw packet socket on Linux
    try:
        raw_sock = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.ntohs(0x0003))
        raw_sock.bind((interface, 0))
    except Exception as e:
        print(f"{RED}[ERROR] Failed to bind raw socket: {e}{RESET}")
        sys.exit(1)

    packet_count = 0

    while True:
        try:
            raw_data, _ = raw_sock.recvfrom(65535)
            packet_count += 1
            now = datetime.now().strftime("%H:%M:%S.%f")[:-3]

            # Parse Ethernet Header (14 bytes)
            eth_proto = struct.unpack('!H', raw_data[12:14])[0]
            src_mac = mac_addr(raw_data[6:12])
            dst_mac = mac_addr(raw_data[0:6])

            # 1. ARP Packets (0x0806)
            if eth_proto == 0x0806:
                arp_header = raw_data[14:42]
                if len(arp_header) >= 28:
                    op, s_mac, s_ip, t_mac, t_ip = struct.unpack('!2s6s4s6s4s', arp_header[6:28])
                    src_ip_str = socket.inet_ntoa(s_ip)
                    dst_ip_str = socket.inet_ntoa(t_ip)
                    if src_ip_str != "192.168.1.41" and not src_ip_str.startswith("0.0.0.0"):
                        # Target PC is asking for gateway or host
                        print(f"[{now}] {CYAN}[ARP]{RESET} Device {BOLD}{src_ip_str}{RESET} (MAC: {src_mac}) is probing network for {dst_ip_str}")

            # 2. IPv4 Packets (0x0800)
            elif eth_proto == 0x0800:
                ip_header = raw_data[14:34]
                if len(ip_header) < 20:
                    continue
                
                iph = struct.unpack('!BBHHHBBH4s4s', ip_header)
                protocol = iph[6]
                src_ip = socket.inet_ntoa(iph[8])
                dst_ip = socket.inet_ntoa(iph[9])
                ihl = (iph[0] & 0xF) * 4

                # UDP Traffic (Protocol 17)
                if protocol == 17:
                    udp_header = raw_data[14 + ihl : 14 + ihl + 8]
                    if len(udp_header) < 8:
                        continue
                    src_port, dst_port, ulen, ucheck = struct.unpack('!HHHH', udp_header)
                    payload = raw_data[14 + ihl + 8 :]

                    # DHCP / BOOTP (Ports 67, 68)
                    if dst_port in [67, 68] or src_port in [67, 68]:
                        msg_type = "DHCP Packet"
                        if len(payload) > 240:
                            # Parse DHCP Message Type option 53
                            if b'\x35\x01\x01' in payload:
                                msg_type = f"{BOLD}{GREEN}DHCPDISCOVER (Client looking for PXE Server!){RESET}"
                            elif b'\x35\x01\x02' in payload:
                                msg_type = f"{YELLOW}DHCPOFFER (Server offering IP/Bootloader){RESET}"
                            elif b'\x35\x01\x03' in payload:
                                msg_type = f"{BOLD}{GREEN}DHCPREQUEST (Client requesting boot){RESET}"
                            elif b'\x35\x01\x05' in payload:
                                msg_type = f"{GREEN}DHCPACK (Server confirmed bootloader!){RESET}"

                        print(f"[{now}] 🎯 {BOLD}{GREEN}[DHCP/PXE]{RESET} {msg_type}")
                        print(f"       From: {src_ip}:{src_port} (MAC: {src_mac}) ➔ To: {dst_ip}:{dst_port}")

                    # ProxyDHCP (Port 4011)
                    elif dst_port == 4011 or src_port == 4011:
                        print(f"[{now}] ⚡ {BOLD}{GREEN}[ProxyDHCP 4011]{RESET} Client {src_mac} ({src_ip}) contacting ProxyDHCP port 4011!")

                    # TFTP (Port 69)
                    elif dst_port == 69:
                        filename = "Unknown"
                        try:
                            parts = payload[2:].split(b'\x00')
                            filename = parts[0].decode('utf-8', errors='ignore')
                        except Exception:
                            pass
                        print(f"[{now}] 📥 {BOLD}{GREEN}[TFTP Port 69]{RESET} Client {src_mac} downloading bootloader: {BOLD}{YELLOW}{filename}{RESET}")

                # TCP Traffic (Protocol 6)
                elif protocol == 6:
                    tcp_header = raw_data[14 + ihl : 14 + ihl + 20]
                    if len(tcp_header) < 20:
                        continue
                    src_port, dst_port = struct.unpack('!HH', tcp_header[:4])
                    if dst_port == 8080 or src_port == 8080:
                        payload = raw_data[14 + ihl + 20 :]
                        if b"GET" in payload:
                            try:
                                get_line = payload.split(b"\r\n")[0].decode('utf-8', errors='ignore')
                                print(f"[{now}] 🚀 {BOLD}{GREEN}[HTTP 8080 Streamer]{RESET} Client {src_ip} ➔ {BOLD}{CYAN}{get_line}{RESET}")
                            except Exception:
                                pass

        except KeyboardInterrupt:
            print(f"\n{YELLOW}[*] Live monitor stopped by user.{RESET}")
            break
        except Exception as e:
            pass

if __name__ == "__main__":
    main()
