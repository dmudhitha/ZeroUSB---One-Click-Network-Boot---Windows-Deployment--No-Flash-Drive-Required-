import os
import shutil
import subprocess
import threading
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable, Tuple

# Pre-defined OS presets
OS_PRESETS = [
    {
        "slug": "win10",
        "name": "Windows 10 (64-bit)",
        "type": "windows",
        "desc": "Windows 10 Home/Pro via WinPE & Samba"
    },
    {
        "slug": "win11",
        "name": "Windows 11 (64-bit)",
        "type": "windows",
        "desc": "Windows 11 Home/Pro via WinPE & Samba"
    },
    {
        "slug": "winserver",
        "name": "Windows Server (64-bit)",
        "type": "windows",
        "desc": "Windows Server 2019/2022 via WinPE & Samba"
    },
    {
        "slug": "linuxmint",
        "name": "Linux Mint (Live & Installer)",
        "type": "linux",
        "desc": "Linux Mint Cinnamon/MATE over HTTP"
    },
    {
        "slug": "ubuntu",
        "name": "Ubuntu Desktop / Server",
        "type": "linux",
        "desc": "Ubuntu LTS Live over HTTP"
    },
    {
        "slug": "custom",
        "name": "Custom Windows / OS",
        "type": "windows",
        "desc": "Custom WIM or ISO Image"
    }
]

class OSManager:
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.srv_http = base_dir / 'srv' / 'http'
        self.srv_http_boot = base_dir / 'srv' / 'http' / 'boot'
        self.srv_http_images = base_dir / 'srv' / 'http' / 'images'
        self.srv_samba = base_dir / 'srv' / 'samba'
        self.srv_tftp = base_dir / 'srv' / 'tftp'
        self.meta_file = base_dir / 'config' / 'installed_os.json'

        self._is_running = False

    @property
    def is_running(self) -> bool:
        return self._is_running

    def get_installed_os_list(self) -> List[Dict[str, Any]]:
        """
        Scans srv directories and metadata to list all currently staged operating systems.
        """
        installed = []
        meta = self._load_meta()

        # Check subdirectories in srv/http/boot/ and srv/samba/
        # Also check root boot.wim (legacy default)
        legacy_wim = self.srv_http_boot / "boot.wim"
        legacy_samba = self.srv_samba / "windows" / "setup.exe"
        if legacy_wim.exists() and legacy_samba.exists():
            size_mb = self._get_dir_size_mb(self.srv_samba / "windows")
            installed.append({
                "slug": "default_windows",
                "name": meta.get("default_windows", {}).get("name", "Windows (Default ISO)"),
                "type": "windows",
                "path_boot": str(self.srv_http_boot),
                "path_payload": str(self.srv_samba / "windows"),
                "size_str": f"{size_mb / 1024:.2f} GB" if size_mb > 1024 else f"{size_mb:.0f} MB",
                "is_legacy": True
            })

        # Scan named subdirectories
        if self.srv_http_boot.exists():
            for child in self.srv_http_boot.iterdir():
                if child.is_dir():
                    slug = child.name
                    # Check if Windows or Linux
                    has_wim = (child / "boot.wim").exists()
                    has_kernel = (child / "vmlinuz").exists() or (child / "vmlinuz.efi").exists()

                    if has_wim or has_kernel:
                        os_meta = meta.get(slug, {})
                        os_name = os_meta.get("name", slug.upper())
                        os_type = os_meta.get("type", "windows" if has_wim else "linux")
                        
                        payload_dir = self.srv_samba / slug if os_type == "windows" else child
                        size_mb = self._get_dir_size_mb(payload_dir)

                        installed.append({
                            "slug": slug,
                            "name": os_name,
                            "type": os_type,
                            "path_boot": str(child),
                            "path_payload": str(payload_dir),
                            "size_str": f"{size_mb / 1024:.2f} GB" if size_mb > 1024 else f"{size_mb:.0f} MB",
                            "is_legacy": False
                        })

        return installed

    def extract_os(
        self,
        os_slug: str,
        os_name: str,
        os_type: str,
        iso_path: str,
        server_ip: str,
        on_progress: Callable[[float, str], None],
        on_log: Callable[[str], None],
        on_finished: Callable[[bool, str], None]
    ):
        if self._is_running:
            on_finished(False, "An OS installation/extraction task is already running.")
            return

        thread = threading.Thread(
            target=self._worker_extract,
            args=(os_slug, os_name, os_type, iso_path, server_ip, on_progress, on_log, on_finished),
            daemon=True
        )
        thread.start()

    def _worker_extract(
        self,
        os_slug: str,
        os_name: str,
        os_type: str,
        iso_path: str,
        server_ip: str,
        on_progress: Callable[[float, str], None],
        on_log: Callable[[str], None],
        on_finished: Callable[[bool, str], None]
    ):
        self._is_running = True
        iso_file = Path(iso_path)

        try:
            if not iso_file.exists():
                raise FileNotFoundError(f"ISO file not found: {iso_path}")

            on_log(f"[*] Extracting OS Profile: {os_name} [{os_slug}]")
            on_log(f"[*] Source ISO: {iso_file.name}")
            on_progress(0.05, f"Creating directories for {os_slug}...")

            boot_dir = self.srv_http_boot / os_slug
            samba_dir = self.srv_samba / os_slug
            boot_dir.mkdir(parents=True, exist_ok=True)

            seven_zip = shutil.which('7z') or shutil.which('7za') or '7z'

            if os_type == "windows":
                samba_dir.mkdir(parents=True, exist_ok=True)
                on_progress(0.15, f"Extracting Windows files to Samba share ({os_slug})...")
                on_log(f"[+] Extracting ISO to {samba_dir}...")

                cmd = [seven_zip, 'x', '-y', f'-o{samba_dir}', str(iso_file)]
                proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                for line in proc.stdout:
                    ls = line.strip()
                    if ls and ('%' in ls or 'Extracting' in ls or 'Everything is Ok' in ls):
                        on_log(f"  [7z] {ls}")
                proc.wait()

                on_progress(0.65, "Locating boot assets (BCD, boot.sdi, boot.wim)...")
                self._copy_case_insensitive(samba_dir, "bcd", boot_dir / "BCD", on_log)
                self._copy_case_insensitive(samba_dir, "boot.sdi", boot_dir / "boot.sdi", on_log)
                self._copy_case_insensitive(samba_dir, "boot.wim", boot_dir / "boot.wim", on_log)

                boot_wim = boot_dir / "boot.wim"
                if not boot_wim.exists():
                    raise FileNotFoundError("Could not find boot.wim in extracted ISO!")

                # Patch startnet.cmd with specific Samba share name
                on_progress(0.80, f"Injecting auto-mount (\\\\{server_ip}\\{os_slug}) into WinPE...")
                wimlib = shutil.which('wimlib-imagex')
                if wimlib:
                    startnet_script = f"""@echo off
title ZeroUSB - {os_name} Installer
wpeinit

echo.
echo =================================================================
echo   Connecting to ZeroUSB Server: \\\\{server_ip}\\{os_slug}
echo =================================================================
echo Initializing network adapter (waiting 6s)...
ping 127.0.0.1 -n 7 > nul

echo Mounting installation media share...
net use Z: \\\\{server_ip}\\{os_slug} /user:nobody ""

if exist Z:\\setup.exe (
    echo [OK] Setup found! Launching {os_name} Setup...
    Z:\\setup.exe
) else (
    echo [ERROR] Z:\\setup.exe not found on \\\\{server_ip}\\{os_slug}!
    cmd.exe
)
"""
                    tmp_script = Path(f"/tmp/startnet_{os_slug}.cmd")
                    tmp_script.write_text(startnet_script, encoding='utf-8')

                    tmp_cmd = Path(f"/tmp/wim_update_{os_slug}.txt")
                    tmp_cmd.write_text(f"add {tmp_script} /Windows/System32/startnet.cmd\n", encoding='utf-8')

                    target_idx = "2"
                    try:
                        info_res = subprocess.run([wimlib, 'info', str(boot_wim)], capture_output=True, text=True)
                        if "Image Count: 1" in info_res.stdout:
                            target_idx = "1"
                    except Exception:
                        target_idx = "2"

                    with open(tmp_cmd, 'r') as uf:
                        subprocess.run([wimlib, 'update', str(boot_wim), target_idx], stdin=uf, capture_output=True)

                    tmp_script.unlink(missing_ok=True)
                    tmp_cmd.unlink(missing_ok=True)
                    on_log(f"[✓] startnet.cmd injected for \\\\{server_ip}\\{os_slug}")

            elif os_type == "linux":
                on_progress(0.20, f"Extracting Linux kernel & initrd from {iso_file.name}...")
                self.srv_http_images.mkdir(parents=True, exist_ok=True)
                
                # Copy full ISO for HTTP streaming
                dst_iso = self.srv_http_images / f"{os_slug}.iso"
                on_log(f"[+] Copying ISO to HTTP images: {dst_iso}...")
                shutil.copy2(iso_file, dst_iso)

                # Extract vmlinuz and initrd
                tmp_extract = Path(f"/tmp/linux_extract_{os_slug}")
                tmp_extract.mkdir(parents=True, exist_ok=True)
                subprocess.run([seven_zip, 'x', '-y', f'-o{tmp_extract}', str(iso_file), 'casper/*', 'live/*', 'isolinux/*'], capture_output=True)

                self._copy_case_insensitive(tmp_extract, "vmlinuz", boot_dir / "vmlinuz", on_log)
                self._copy_case_insensitive(tmp_extract, "initrd", boot_dir / "initrd.lz", on_log)
                shutil.rmtree(tmp_extract, ignore_errors=True)

            # Update Metadata
            meta = self._load_meta()
            meta[os_slug] = {"name": os_name, "type": os_type, "iso": str(iso_file)}
            self._save_meta(meta)

            # Rebuild iPXE Menu & Samba shares
            on_progress(0.95, "Rebuilding iPXE Multi-Boot Menu...")
            self.generate_ipxe_menu(server_ip)

            on_progress(1.0, "Completed!")
            on_log(f"[✓] Successfully added {os_name} [{os_slug}] to ZeroUSB multi-boot catalog!")
            on_finished(True, f"{os_name} staged and added to the network boot menu!")

        except Exception as e:
            on_log(f"[ERROR] OS extraction failed: {str(e)}")
            on_finished(False, str(e))
        finally:
            self._is_running = False

    def remove_os(self, os_slug: str, server_ip: str, on_log: Optional[Callable[[str], None]] = None) -> Tuple[bool, str]:
        """
        Removes a specific OS from disk and updates the iPXE boot menu.
        """
        log = on_log or (lambda msg: None)
        try:
            log(f"[*] Removing OS Profile [{os_slug}]...")

            if os_slug == "default_windows":
                # Legacy root folders
                samba_win = self.srv_samba / "windows"
                if samba_win.exists():
                    shutil.rmtree(samba_win, ignore_errors=True)
                    samba_win.mkdir(parents=True, exist_ok=True)
                for f in ["BCD", "bcd", "boot.sdi", "boot.wim"]:
                    (self.srv_http_boot / f).unlink(missing_ok=True)
            else:
                # Remove named boot directory
                boot_dir = self.srv_http_boot / os_slug
                if boot_dir.exists():
                    shutil.rmtree(boot_dir, ignore_errors=True)
                    log(f"  [✓] Removed boot assets ({boot_dir})")

                # Remove named samba directory
                samba_dir = self.srv_samba / os_slug
                if samba_dir.exists():
                    shutil.rmtree(samba_dir, ignore_errors=True)
                    log(f"  [✓] Removed Samba payload ({samba_dir})")

                # Remove ISO image if Linux
                iso_img = self.srv_http_images / f"{os_slug}.iso"
                if iso_img.exists():
                    iso_img.unlink(missing_ok=True)
                    log(f"  [✓] Removed ISO image ({iso_img})")

            # Remove from metadata
            meta = self._load_meta()
            meta.pop(os_slug, None)
            self._save_meta(meta)

            # Rebuild iPXE Menu
            self.generate_ipxe_menu(server_ip)

            log(f"[✓] OS Profile [{os_slug}] successfully removed and iPXE menu updated!")
            return True, f"OS [{os_slug}] removed successfully."
        except Exception as e:
            log(f"[ERROR] Failed to remove OS [{os_slug}]: {str(e)}")
            return False, str(e)

    def generate_ipxe_menu(self, server_ip: str, http_port: int = 8080) -> str:
        """
        Dynamically generates boot.ipxe containing all staged operating systems.
        """
        installed = self.get_installed_os_list()
        http_base = f"http://${{server_ip}}:{http_port}"

        menu_items = []
        boot_targets = []

        windows_items = [item for item in installed if item["type"] == "windows"]
        linux_items = [item for item in installed if item["type"] == "linux"]

        if windows_items:
            menu_items.append("item --gap --             ------------------ Windows Deployments -----------------")
            for item in windows_items:
                slug = item["slug"]
                name = item["name"]
                menu_items.append(f"item {slug}          🪟 {name}")

                if item.get("is_legacy", False):
                    # Legacy root boot.wim
                    boot_targets.append(f"""
:{slug}
echo Booting {name} over HTTP...
kernel {http_base}/boot/wimboot
initrd -n bcd         {http_base}/boot/BCD        bcd
initrd -n boot.sdi    {http_base}/boot/boot.sdi   boot.sdi
initrd -n boot.wim    {http_base}/boot/boot.wim   boot.wim
boot || goto failed
""")
                else:
                    boot_targets.append(f"""
:{slug}
echo Booting {name} over HTTP...
kernel {http_base}/boot/wimboot
initrd -n bcd         {http_base}/boot/{slug}/BCD        bcd
initrd -n boot.sdi    {http_base}/boot/{slug}/boot.sdi   boot.sdi
initrd -n boot.wim    {http_base}/boot/{slug}/boot.wim   boot.wim
boot || goto failed
""")

        if linux_items:
            menu_items.append("item --gap --             ------------------ Linux Distributions -----------------")
            for item in linux_items:
                slug = item["slug"]
                name = item["name"]
                menu_items.append(f"item {slug}          🐧 {name}")
                boot_targets.append(f"""
:{slug}
echo Booting {name} kernel & initrd over HTTP...
kernel {http_base}/boot/{slug}/vmlinuz boot=casper netboot=url url={http_base}/images/{slug}.iso quiet splash
initrd {http_base}/boot/{slug}/initrd.lz
boot || goto failed
""")

        if not installed:
            menu_items.append("item --gap --             [!] No Operating Systems staged yet!")
            menu_items.append("item no_os                (Please stage an ISO from ZeroUSB app)")

        default_target = installed[0]["slug"] if installed else "boot_local"

        menu_items_str = "\n".join(menu_items)
        boot_targets_str = "\n".join(boot_targets)

        ipxe_script = f"""#!ipxe

set server_ip {server_ip}
set http_port {http_port}
set http_base http://${{server_ip}}:${{http_port}}

# Console Colors
cpair --foreground 7 --background 4 2
cpair --foreground 0 --background 7 3

:menu
menu ZeroUSB - Universal Multi-OS Deployment Server (Host: ${{server_ip}})
{menu_items_str}
item --gap --             ------------------ Local Actions -----------------------
item boot_local           💻 Boot from Local SSD / NVMe
item ipxe_shell           🔧 Drop to iPXE Diagnostic Shell
item reboot               🔄 Reboot Computer
choose --timeout 15000 --default {default_target} target && goto ${{target}}

{boot_targets_str}

:no_os
echo [!] No operating systems currently installed in ZeroUSB.
prompt Press any key to return to menu...
goto menu

:boot_local
echo Booting from local storage...
exit 1

:ipxe_shell
shell
goto menu

:reboot
reboot

:failed
echo.
echo [ERROR] Network booting failed for selected OS.
prompt Press any key to return to ZeroUSB menu...
goto menu
"""
        self.srv_http.mkdir(parents=True, exist_ok=True)
        self.srv_tftp.mkdir(parents=True, exist_ok=True)

        (self.srv_http / "boot.ipxe").write_text(ipxe_script, encoding='utf-8')
        (self.srv_tftp / "boot.ipxe").write_text(ipxe_script, encoding='utf-8')

        return ipxe_script

    def _load_meta(self) -> Dict[str, Any]:
        if self.meta_file.exists():
            try:
                return json.loads(self.meta_file.read_text(encoding='utf-8'))
            except Exception:
                return {}
        return {}

    def _save_meta(self, data: Dict[str, Any]):
        self.meta_file.parent.mkdir(parents=True, exist_ok=True)
        self.meta_file.write_text(json.dumps(data, indent=2), encoding='utf-8')

    def _copy_case_insensitive(self, search_dir: Path, target_name: str, dest_file: Path, on_log: Callable[[str], None]):
        target_lower = target_name.lower()
        for root, _, files in os.walk(search_dir):
            for file in files:
                if file.lower() == target_lower:
                    src = Path(root) / file
                    on_log(f"  Found {file} -> Staging to {dest_file.name}")
                    shutil.copy2(src, dest_file)
                    dest_file.chmod(0o644)
                    return
        on_log(f"  [!] Warning: {target_name} was not found in {search_dir}")

    def _get_dir_size_mb(self, path: Path) -> float:
        if not path.exists():
            return 0.0
        total = 0
        if path.is_file():
            return path.stat().st_size / (1024 * 1024)
        for root, _, files in os.walk(path):
            for f in files:
                try:
                    total += (Path(root) / f).stat().st_size
                except Exception:
                    pass
        return total / (1024 * 1024)
