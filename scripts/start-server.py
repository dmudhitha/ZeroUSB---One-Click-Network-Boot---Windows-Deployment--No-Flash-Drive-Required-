#!/usr/bin/env python3
import sys
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from backend.server_manager import ServerManager
from backend.os_manager import OSManager
from backend.detector import get_network_interfaces

def main():
    print("=" * 65)
    print("   ⚡ ZeroUSB - Universal Network Boot & Deployment Server")
    print("=" * 65)

    ifaces = get_network_interfaces()
    if not ifaces:
        print("[!] No network interfaces detected.")
        return

    # Prioritize wired Ethernet interface (enp, eth) for Direct Cable Link
    selected = ifaces[0]
    for item in ifaces:
        if item[0].startswith(('en', 'eth')):
            selected = item
            break
        elif item[2]:  # default fallback
            selected = item

    iface, ip, _ = selected
    port = 8080

    print(f"[*] Selected Interface: {iface}")
    print(f"[*] Server IP:         {ip}")
    print(f"[*] HTTP Port:         {port}")
    print(f"[*] Mode:              Direct Cable Standalone (192.168.42.x)")
    print("=" * 65)

    os_mgr = OSManager(BASE_DIR)
    os_mgr.generate_ipxe_menu(ip, port)

    srv = ServerManager(BASE_DIR)
    success = srv.start(
        interface=iface,
        server_ip=ip,
        http_port=port,
        dhcp_mode="standalone",
        boot_mode="csm",
        on_log=lambda m: print(f"[{time.strftime('%H:%M:%S')}] {m}")
    )

    if not success:
        print("[ERROR] Failed to start server services. Please check permissions.")
        return

    print("\n[✓] Server is LIVE and listening for client boot requests!")
    print("[*] Press Ctrl+C at any time to stop the server.\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[*] Stopping server...")
        srv.stop(on_log=lambda m: print(f"[{time.strftime('%H:%M:%S')}] {m}"))
        print("[✓] Server stopped cleanly.")

if __name__ == "__main__":
    main()
