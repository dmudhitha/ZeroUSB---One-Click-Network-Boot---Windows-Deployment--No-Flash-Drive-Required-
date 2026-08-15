import os
import shutil
import socket
import subprocess
import threading
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Dict, Optional, Callable

class ServerManager:
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.config_dir = base_dir / 'config'
        self.srv_dir = base_dir / 'srv'
        self.logs_dir = base_dir / 'logs'
        self.pid_dir = base_dir / '.run'

        self.http_server: Optional[ThreadingHTTPServer] = None
        self.http_thread: Optional[threading.Thread] = None
        self.dnsmasq_process: Optional[subprocess.Popen] = None
        self._is_active = False

        self.current_ip = "192.168.1.41"
        self.current_interface = "enp3s0"
        self.current_http_port = 8080

    @property
    def is_active(self) -> bool:
        return self._is_active

    def start(
        self,
        interface: str,
        server_ip: str,
        http_port: int = 8080,
        on_log: Optional[Callable[[str], None]] = None
    ) -> bool:
        log = on_log or (lambda msg: None)
        self.current_interface = interface
        self.current_ip = server_ip
        self.current_http_port = http_port

        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.pid_dir.mkdir(parents=True, exist_ok=True)

        try:
            log(f"[*] Starting PXE Network Services on {interface} ({server_ip})...")

            # 1. Generate updated iPXE boot script
            log("[+] Generating iPXE boot script (boot.ipxe)...")
            boot_ipxe_src = self.config_dir / 'boot.ipxe'
            boot_ipxe_content = boot_ipxe_src.read_text(encoding='utf-8')
            boot_ipxe_content = boot_ipxe_content.replace(
                "set server_ip 192.168.1.41", f"set server_ip {server_ip}"
            ).replace(
                "set http_port 8080", f"set http_port {http_port}"
            )

            (self.srv_dir / 'http' / 'boot.ipxe').write_text(boot_ipxe_content, encoding='utf-8')
            (self.srv_dir / 'tftp' / 'boot.ipxe').write_text(boot_ipxe_content, encoding='utf-8')

            # 2. Start Python HTTP Server
            log(f"[+] Starting HTTP Server on port {http_port}...")
            self._start_http_server(http_port, log)

            # 3. Generate Dnsmasq config and launch ProxyDHCP + TFTP
            log(f"[+] Starting Dnsmasq ProxyDHCP & TFTP on interface {interface}...")
            self._start_dnsmasq(interface, server_ip, log)

            # 4. Check Samba
            log("[+] Verifying Samba service status...")
            self._check_samba(log)

            self._is_active = True
            log(f"[✓] Network Installer is ACTIVE and serving PXE on {server_ip}!")
            return True

        except Exception as e:
            log(f"[ERROR] Failed to start services: {str(e)}")
            self.stop(log)
            return False

    def stop(self, on_log: Optional[Callable[[str], None]] = None):
        log = on_log or (lambda msg: None)
        log("[*] Stopping Network Installer services...")

        # Stop HTTP Server
        if self.http_server:
            try:
                self.http_server.shutdown()
                self.http_server.server_close()
            except Exception:
                pass
            self.http_server = None
            log("  Stopped HTTP server.")

        # Stop Dnsmasq process
        if self.dnsmasq_process:
            try:
                self.dnsmasq_process.terminate()
                self.dnsmasq_process.wait(timeout=2)
            except Exception:
                try:
                    self.dnsmasq_process.kill()
                except Exception:
                    pass
            self.dnsmasq_process = None
            log("  Stopped Dnsmasq service.")

        # Kill any orphan dnsmasq processes started by our config
        try:
            subprocess.run(['pkexec', 'killall', '-9', 'dnsmasq'], capture_output=True, timeout=2)
        except Exception:
            pass

        self._is_active = False
        log("[✓] All Network Installer services stopped.")

    def get_status(self) -> Dict[str, bool]:
        """
        Returns live operational status of each component.
        """
        # Check HTTP port
        http_ok = False
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.5)
                http_ok = (s.connect_ex((self.current_ip, self.current_http_port)) == 0)
        except Exception:
            http_ok = False

        # Check Dnsmasq process
        dnsmasq_ok = (self.dnsmasq_process is not None and self.dnsmasq_process.poll() is None)

        # Check Samba port 445 or smbd process
        samba_ok = False
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.5)
                samba_ok = (s.connect_ex((self.current_ip, 445)) == 0 or s.connect_ex(('127.0.0.1', 445)) == 0)
        except Exception:
            samba_ok = False

        return {
            'http': http_ok,
            'dnsmasq': dnsmasq_ok,
            'samba': samba_ok,
            'is_serving': (http_ok and dnsmasq_ok)
        }

    def _start_http_server(self, port: int, log: Callable[[str], None]):
        srv_http_dir = str(self.srv_dir / 'http')

        class CustomHandler(SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=srv_http_dir, **kwargs)

            def log_message(self, format, *args):
                # Suppress flood, log only important transfers
                msg = format % args
                if "GET" in msg and any(ext in msg for ext in ['.wim', 'boot', 'BCD', 'ipxe']):
                    log(f"  [HTTP] {msg}")

        self.http_server = ThreadingHTTPServer(('0.0.0.0', port), CustomHandler)
        self.http_thread = threading.Thread(target=self.http_server.serve_forever, daemon=True)
        self.http_thread.start()

    def _start_dnsmasq(self, interface: str, server_ip: str, log: Callable[[str], None]):
        subnet = ".".join(server_ip.split(".")[:3]) + ".0"
        conf_path = Path("/tmp/dnsmasq_gui_runtime.conf")
        tftp_root = str(self.srv_dir / 'tftp')

        conf_content = f"""port=0
interface={interface}
bind-interfaces
dhcp-range={subnet},proxy,255.255.255.0
enable-tftp
tftp-root={tftp_root}

dhcp-match=set:bios,option:client-arch,0
dhcp-match=set:efi-x86,option:client-arch,6
dhcp-match=set:efi-x64,option:client-arch,7
dhcp-match=set:efi-x64,option:client-arch,9
dhcp-match=set:efi-arm64,option:client-arch,11

dhcp-boot=tag:bios,undionly.kpxe
dhcp-boot=tag:efi-x64,ipxe.efi
dhcp-boot=tag:efi-x86,ipxe32.efi
dhcp-boot=tag:efi-arm64,ipxe-arm64.efi
"""
        conf_path.write_text(conf_content, encoding='utf-8')

        # Kill any existing dnsmasq
        pkexec = shutil.which('pkexec')
        cmd = [pkexec or 'sudo', 'dnsmasq', f'--conf-file={conf_path}', '--no-daemon', '--log-dhcp']

        self.dnsmasq_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )

        def log_dnsmasq_output():
            for line in self.dnsmasq_process.stdout:
                line_s = line.strip()
                if line_s:
                    if any(k in line_s for k in ['DHCPDISCOVER', 'DHCPOFFER', 'DHCPREQUEST', 'DHCPACK', 'sent', 'TFTP']):
                        log(f"  [PXE] {line_s}")

        t = threading.Thread(target=log_dnsmasq_output, daemon=True)
        t.start()

    def _check_samba(self, log: Callable[[str], None]):
        # Ensure smbd is active and configure shares for all staged OS folders
        try:
            samba_root = self.srv_dir / 'samba'
            shares_to_add = []

            if samba_root.exists():
                for share_dir in samba_root.iterdir():
                    if share_dir.is_dir():
                        share_name = share_dir.name
                        # Check if share block is in /etc/samba/smb.conf
                        try:
                            conf_text = Path('/etc/samba/smb.conf').read_text(encoding='utf-8', errors='ignore')
                        except Exception:
                            conf_text = ""

                        if f"[{share_name}]" not in conf_text:
                            shares_to_add.append((share_name, str(share_dir)))

            if shares_to_add:
                log(f"  [+] Configuring dynamic Samba shares: {', '.join([s[0] for s in shares_to_add])}...")
                pkexec = shutil.which('pkexec')
                snippet = ""
                for s_name, s_path in shares_to_add:
                    snippet += f"\n[{s_name}]\n   path = {s_path}\n   browseable = yes\n   read only = yes\n   guest ok = yes\n   guest only = yes\n   force user = nobody\n"

                tmp_samba_snippet = Path("/tmp/samba_multi_os.txt")
                tmp_samba_snippet.write_text(snippet, encoding='utf-8')
                subprocess.run(
                    [pkexec or 'sudo', 'bash', '-c', f'cat {tmp_samba_snippet} >> /etc/samba/smb.conf'],
                    capture_output=True
                )
                tmp_samba_snippet.unlink(missing_ok=True)

            # Restart / reload Samba
            pkexec = shutil.which('pkexec')
            subprocess.run([pkexec or 'sudo', 'systemctl', 'restart', 'smbd'], capture_output=True)
            log("  [✓] Samba shares active and ready for client connections.")
        except Exception as e:
            log(f"  [!] Note on Samba configuration: {e}")
