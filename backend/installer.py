import os
import shutil
import subprocess
import threading
import urllib.request
from pathlib import Path
from typing import Callable

class DependencyInstaller:
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.srv_tftp = base_dir / 'srv' / 'tftp'
        self.srv_http_boot = base_dir / 'srv' / 'http' / 'boot'
        self._is_running = False

    @property
    def is_running(self) -> bool:
        return self._is_running

    def install_dependencies(
        self,
        on_progress: Callable[[float, str], None],
        on_log: Callable[[str], None],
        on_finished: Callable[[bool, str], None]
    ):
        if self._is_running:
            on_finished(False, "An installation is already running.")
            return

        thread = threading.Thread(
            target=self._worker,
            args=(on_progress, on_log, on_finished),
            daemon=True
        )
        thread.start()

    def _worker(
        self,
        on_progress: Callable[[float, str], None],
        on_log: Callable[[str], None],
        on_finished: Callable[[bool, str], None]
    ):
        self._is_running = True
        try:
            self.srv_tftp.mkdir(parents=True, exist_ok=True)
            self.srv_http_boot.mkdir(parents=True, exist_ok=True)

            on_log("[*] Checking and installing system packages (dnsmasq, samba, wimtools, 7zip, ipxe)...")
            on_progress(0.2, "Installing system packages via apt...")

            # Run apt install using pkexec or sudo if available
            pkexec = shutil.which('pkexec')
            cmd = ['sudo', 'apt-get', 'update', '-y']
            if pkexec:
                cmd = ['pkexec', 'apt-get', 'install', '-y', 'dnsmasq', 'samba', 'wimtools', '7zip', 'curl', 'ipxe', 'ipxe-qemu']
            else:
                cmd = ['sudo', 'apt-get', 'install', '-y', 'dnsmasq', 'samba', 'wimtools', '7zip', 'curl', 'ipxe', 'ipxe-qemu']

            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )
            for line in proc.stdout:
                line_s = line.strip()
                if line_s:
                    on_log(f"  [apt] {line_s}")
            proc.wait()

            on_progress(0.6, "Setting up iPXE bootloaders in TFTP root...")
            on_log("[+] Copying iPXE EFI and BIOS bootloader ROMs...")

            for src_name, dst_name in [
                ('/usr/lib/ipxe/ipxe.efi', 'ipxe.efi'),
                ('/usr/lib/ipxe/undionly.kpxe', 'undionly.kpxe'),
                ('/usr/lib/ipxe/ipxe32.efi', 'ipxe32.efi'),
            ]:
                if os.path.exists(src_name):
                    shutil.copy2(src_name, self.srv_tftp / dst_name)
                    (self.srv_tftp / dst_name).chmod(0o644)
                    on_log(f"  Copied {src_name} -> {dst_name}")

            on_progress(0.8, "Downloading latest wimboot binary...")
            wimboot_dest = self.srv_http_boot / 'wimboot'
            wimboot_url = "https://github.com/ipxe/wimboot/releases/latest/download/wimboot"
            on_log(f"[+] Downloading wimboot from {wimboot_url}...")

            urllib.request.urlretrieve(wimboot_url, str(wimboot_dest))
            wimboot_dest.chmod(0o644)
            on_log(f"[✓] wimboot downloaded successfully ({wimboot_dest.stat().st_size} bytes)")

            on_progress(1.0, "Completed!")
            on_finished(True, "All dependencies and bootloaders installed successfully!")

        except Exception as e:
            on_log(f"[ERROR] Dependency installation failed: {str(e)}")
            on_finished(False, str(e))
        finally:
            self._is_running = False
