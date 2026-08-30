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

        self.current_ip = "192.168.42.1"
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
        dhcp_mode: str = "proxy",
        boot_mode: str = "dual",
        on_log: Optional[Callable[[str], None]] = None
    ) -> bool:
        log = on_log or (lambda msg: None)
        self.current_interface = interface
        self.current_ip = server_ip
        self.current_http_port = http_port

        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.pid_dir.mkdir(parents=True, exist_ok=True)

        try:
            log(f"[*] Starting ZeroUSB PXE Services on {interface} ({server_ip}) [Mode: {dhcp_mode.upper()} | Target: {boot_mode.upper()}]...")

            # 1. Start Python HTTP Server
            log(f"[+] Starting High-Speed HTTP Streaming Server on port {http_port}...")
            self._start_http_server(http_port, log)

            # 2. Start Dnsmasq, Firewall & Network Config via unified controller
            log(f"[+] Starting Dnsmasq ({dhcp_mode.upper()} mode, Target: {boot_mode.upper()}, TFTP port 69) on {interface}...")
            self._start_dnsmasq(interface, server_ip, http_port, dhcp_mode, boot_mode, log)

            # 3. Check Samba service & dynamic shares
            log("[+] Verifying Samba shares for Windows setup...")
            self._check_samba(log)

            self._is_active = True
            log(f"[✓] ZeroUSB Server is ACTIVE and serving PXE to network ({server_ip})!")
            return True

        except Exception as e:
            log(f"[ERROR] Failed to start services: {str(e)}")
            self.stop(log)
            return False

    def stop(self, on_log: Optional[Callable[[str], None]] = None):
        log = on_log or (lambda msg: None)
        log("[*] Stopping ZeroUSB network services...")

        # Stop Internal HTTP Server
        if self.http_server:
            try:
                self.http_server.shutdown()
                self.http_server.server_close()
            except Exception:
                pass
            self.http_server = None

        if self.dnsmasq_process:
            try:
                self.dnsmasq_process.terminate()
                self.dnsmasq_process.wait(timeout=1)
            except Exception:
                try:
                    self.dnsmasq_process.kill()
                except Exception:
                    pass
            self.dnsmasq_process = None

        # Execute unified stop via server-ctl.sh
        ctrl_script = str(self.base_dir / "scripts" / "server-ctl.sh")
        try:
            if os.geteuid() == 0:
                cmd = [ctrl_script, "stop"]
            elif shutil.which('pkexec'):
                cmd = ['pkexec', ctrl_script, "stop"]
            else:
                cmd = ['sudo', ctrl_script, "stop"]
            subprocess.run(cmd, capture_output=True, timeout=3)
        except Exception:
            pass

        if (self.pid_dir / "http.pid").exists():
            (self.pid_dir / "http.pid").unlink(missing_ok=True)
        if (self.pid_dir / "dnsmasq.pid").exists():
            (self.pid_dir / "dnsmasq.pid").unlink(missing_ok=True)

        self._is_active = False
        log("[✓] All ZeroUSB services stopped.")

    def get_status(self) -> Dict[str, bool]:
        """
        Returns live operational status of each component.
        """
        # Check HTTP port
        http_ok = False
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.3)
                http_ok = (s.connect_ex(('127.0.0.1', self.current_http_port)) == 0 or
                           s.connect_ex((self.current_ip, self.current_http_port)) == 0)
        except Exception:
            http_ok = False

        # Check Dnsmasq process
        dnsmasq_ok = (self.dnsmasq_process is not None and self.dnsmasq_process.poll() is None)
        if not dnsmasq_ok:
            pid_file = self.pid_dir / "dnsmasq.pid"
            if pid_file.exists():
                try:
                    pid = int(pid_file.read_text().strip())
                    os.kill(pid, 0)
                    dnsmasq_ok = True
                except Exception:
                    pass
            if not dnsmasq_ok:
                try:
                    res = subprocess.run(['pgrep', '-x', 'dnsmasq'], capture_output=True, text=True)
                    for p in res.stdout.strip().split():
                        if not p: continue
                        cmd_path = Path(f"/proc/{p}/cmdline")
                        if cmd_path.exists() and "dnsmasq_gui_runtime.conf" in cmd_path.read_text(errors='ignore'):
                            dnsmasq_ok = True
                            break
                except Exception:
                    pass

        # Check Samba port 445 or smbd process
        samba_ok = False
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.3)
                samba_ok = (s.connect_ex(('127.0.0.1', 445)) == 0 or
                            s.connect_ex((self.current_ip, 445)) == 0)
        except Exception:
            samba_ok = False

        return {
            'http': http_ok,
            'dnsmasq': dnsmasq_ok,
            'samba': samba_ok,
            'is_serving': (http_ok and dnsmasq_ok)
        }

    def _configure_firewall(self, log: Callable[[str], None]):
        """
        Ensures UFW allows required PXE UDP and TCP ports, plus dynamic TFTP return traffic.
        """
        try:
            res = subprocess.run(['ufw', 'status'], capture_output=True, text=True, timeout=2)
            if 'active' in res.stdout.lower():
                log("  [+] Configuring UFW firewall for PXE and TFTP...")
                pkexec = shutil.which('pkexec')
                cmd_prefix = [pkexec] if pkexec else ['sudo']
                subprocess.run(cmd_prefix + ['modprobe', 'nf_conntrack_tftp'], capture_output=True, timeout=2)
                subprocess.run(cmd_prefix + ['ufw', 'allow', 'in', 'on', self.current_interface, 'to', 'any'], capture_output=True, timeout=2)
                for port, proto in [(67, 'udp'), (68, 'udp'), (69, 'udp'), (4011, 'udp'),
                                    (self.current_http_port, 'tcp'), (445, 'tcp'), (139, 'tcp'),
                                    (137, 'udp'), (138, 'udp')]:
                    subprocess.run(cmd_prefix + ['ufw', 'allow', f"{port}/{proto}"], capture_output=True, timeout=2)
                log("  [✓] Firewall configured successfully.")
        except Exception as e:
            log(f"  [!] Firewall note: {e}")

    def _start_http_server(self, port: int, log: Callable[[str], None]):
        if self.http_server:
            try:
                self.http_server.shutdown()
                self.http_server.server_close()
            except Exception:
                pass
            self.http_server = None

        srv_http_dir = str(self.srv_dir / 'http')

        class CustomHandler(SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=srv_http_dir, **kwargs)

            def copyfile(self, source, outputfile):
                """Zero-copy kernel sendfile streaming for maximum network wire throughput."""
                try:
                    in_fd = source.fileno()
                    out_fd = outputfile.fileno()
                    file_size = os.fstat(in_fd).st_size
                    try:
                        self.connection.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                        self.connection.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 4 * 1024 * 1024)
                    except Exception:
                        pass
                    offset = 0
                    while offset < file_size:
                        sent = os.sendfile(out_fd, in_fd, offset, 16 * 1024 * 1024)
                        if sent == 0:
                            break
                        offset += sent
                    return
                except Exception:
                    pass
                # Fallback to 1MB high-throughput buffer
                shutil.copyfileobj(source, outputfile, length=1024 * 1024)

            def log_message(self, format, *args):
                msg = format % args
                if "GET" in msg and any(ext in msg for ext in ['.wim', 'boot', 'BCD', 'ipxe', '.iso', '.lz']):
                    log(f"  [HTTP] {msg}")

        self.http_server = ThreadingHTTPServer(('0.0.0.0', port), CustomHandler)
        self.http_thread = threading.Thread(target=self.http_server.serve_forever, daemon=True)
        self.http_thread.start()

    def _start_dnsmasq(self, interface: str, server_ip: str, http_port: int, dhcp_mode: str, boot_mode: str, log: Callable[[str], None]):
        ip_parts = server_ip.split(".")
        subnet = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}.0"
        ip_prefix = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}"
        conf_path = Path("/tmp/dnsmasq_gui_runtime.conf")
        tftp_root = str(self.srv_dir / 'tftp')

        if boot_mode == "csm":
            bios_bootloader = "undionly.kpxe"
            uefi_bootloader = "undionly.kpxe"
        elif boot_mode == "uefi":
            # Native UEFI mode: Always serve ipxe.efi to UEFI clients. Keep undionly.kpxe for legacy BIOS clients so they never crash with 'NBP too big'
            bios_bootloader = "undionly.kpxe"
            uefi_bootloader = "ipxe.efi"
        else:
            # Dual Mode (Auto-Detect CSM & UEFI)
            bios_bootloader = "undionly.kpxe"
            uefi_bootloader = "ipxe.efi"

        if dhcp_mode == "standalone":
            dhcp_block = f"""# Standalone Full Authoritative DHCP Server (Direct Cable Mode)
dhcp-authoritative
dhcp-range={ip_prefix}.150,{ip_prefix}.199,255.255.255.0,1h
dhcp-option=option:router,{server_ip}
dhcp-option=option:dns-server,{server_ip}
dhcp-option=66,{server_ip}

# Direct Boot file mapping (Direct & Fast Chaining):
dhcp-boot=tag:ipxe,boot.ipxe,{server_ip},{server_ip}
dhcp-option=tag:ipxe,67,http://{server_ip}:{http_port}/boot.ipxe

dhcp-boot=tag:!ipxe,tag:bios,{bios_bootloader},{server_ip},{server_ip}
dhcp-option=tag:!ipxe,tag:bios,67,{bios_bootloader}

dhcp-boot=tag:!ipxe,tag:efi-x64,{uefi_bootloader},{server_ip},{server_ip}
dhcp-option=tag:!ipxe,tag:efi-x64,67,{uefi_bootloader}
"""
        else:
            dhcp_block = f"""# ProxyDHCP Mode (Co-exists with Router DHCP)
dhcp-range={server_ip},proxy
dhcp-option=66,{server_ip}

dhcp-option=tag:ipxe,67,http://{server_ip}:{http_port}/boot.ipxe
dhcp-option=tag:!ipxe,tag:bios,67,{bios_bootloader}
dhcp-option=tag:!ipxe,tag:efi-x64,67,{uefi_bootloader}
dhcp-option=tag:!ipxe,tag:efi-x86,67,ipxe32.efi
dhcp-option=tag:!ipxe,tag:efi-arm64,67,ipxe-arm64.efi

# PXE Services
pxe-prompt="ZeroUSB Network Boot", 0
pxe-service=x86PC,"ZeroUSB BIOS / CSM Bootloader",{bios_bootloader}
pxe-service=X86-64_EFI,"ZeroUSB UEFI 64 Bootloader",{uefi_bootloader}

dhcp-boot=tag:ipxe,http://{server_ip}:{http_port}/boot.ipxe
dhcp-boot=tag:!ipxe,tag:bios,{bios_bootloader},{server_ip},{server_ip}
dhcp-boot=tag:!ipxe,tag:efi-x64,{uefi_bootloader},{server_ip},{server_ip}
"""

        conf_content = f"""# ZeroUSB Dynamic Runtime Config
port=0
log-dhcp
user=root
interface={interface}
bind-dynamic
except-interface=lo

# High-Performance TFTP Server
enable-tftp
tftp-root={tftp_root}
tftp-max=1000

# Client Architecture Detection
dhcp-match=set:bios,option:client-arch,0
dhcp-match=set:efi-x86,option:client-arch,6
dhcp-match=set:efi-x64,option:client-arch,7
dhcp-match=set:efi-x64,option:client-arch,9
dhcp-match=set:efi-arm64,option:client-arch,11

# Match iPXE via Option 175 and User-Class (Universal iPXE Chaining)
dhcp-match=set:ipxe,175
dhcp-userclass=set:ipxe,iPXE

{dhcp_block}
"""
        conf_path.write_text(conf_content, encoding='utf-8')
        ctrl_script = str(self.base_dir / "scripts" / "server-ctl.sh")
        if os.geteuid() == 0:
            cmd = [ctrl_script, "start", str(conf_path), interface, server_ip]
        elif shutil.which('pkexec'):
            cmd = ['pkexec', ctrl_script, "start", str(conf_path), interface, server_ip]
        else:
            cmd = ['sudo', ctrl_script, "start", str(conf_path), interface, server_ip]

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
                    if any(k in line_s for k in ['DHCPDISCOVER', 'DHCPOFFER', 'DHCPREQUEST', 'DHCPACK', 'sent', 'TFTP', 'proxy']):
                        log(f"  [PXE] {line_s}")
                    else:
                        log(f"  [*] {line_s}")
            rc = self.dnsmasq_process.poll()
            if rc is not None and rc != 0:
                log(f"  [!] Dnsmasq/PXE controller process exited with code {rc}")

        t = threading.Thread(target=log_dnsmasq_output, daemon=True)
        t.start()

    def _check_samba(self, log: Callable[[str], None]):
        try:
            samba_root = self.srv_dir / 'samba'
            shares_to_add = []

            if samba_root.exists():
                for share_dir in samba_root.iterdir():
                    if share_dir.is_dir():
                        share_name = share_dir.name
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
            log("  [✓] Samba shares active and ready for client connections.")
        except Exception as e:
            log(f"  [!] Note on Samba configuration: {e}")
