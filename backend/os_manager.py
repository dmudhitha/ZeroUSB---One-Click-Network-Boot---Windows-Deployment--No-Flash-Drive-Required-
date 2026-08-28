import os
import re
import shutil
import subprocess
import threading
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable, Tuple

# Pre-defined OS presets
OS_PRESETS = [
    # Official Flagship Windows Releases
    {
        "slug": "win11",
        "name": "Windows 11 (64-bit)",
        "type": "windows",
        "desc": "Windows 11 Home/Pro via WinPE & Samba"
    },
    {
        "slug": "win11_ltsc",
        "name": "Windows 11 IoT Enterprise LTSC",
        "type": "windows",
        "desc": "Windows 11 LTSC (Bloat-Free / 10-Year Support)"
    },
    {
        "slug": "win10",
        "name": "Windows 10 (64-bit)",
        "type": "windows",
        "desc": "Windows 10 Home/Pro via WinPE & Samba"
    },
    {
        "slug": "win10_ltsc",
        "name": "Windows 10 IoT Enterprise LTSC",
        "type": "windows",
        "desc": "Windows 10 LTSC (Rock-Solid / Bloat-Free)"
    },
    {
        "slug": "win81",
        "name": "Windows 8.1 (64-bit)",
        "type": "windows",
        "desc": "Windows 8.1 Pro/Enterprise via WinPE & Samba"
    },
    {
        "slug": "win81_x86",
        "name": "Windows 8.1 (32-bit)",
        "type": "windows",
        "desc": "Windows 8.1 32-bit via WinPE & Samba"
    },
    {
        "slug": "win8",
        "name": "Windows 8 (64-bit)",
        "type": "windows",
        "desc": "Windows 8 Pro/Enterprise via WinPE & Samba"
    },
    {
        "slug": "win8_x86",
        "name": "Windows 8 (32-bit)",
        "type": "windows",
        "desc": "Windows 8 32-bit via WinPE & Samba"
    },
    {
        "slug": "win7",
        "name": "Windows 7 (64-bit)",
        "type": "windows",
        "desc": "Windows 7 SP1 Ultimate/Pro via WinPE & Samba"
    },
    {
        "slug": "win7_x86",
        "name": "Windows 7 (32-bit)",
        "type": "windows",
        "desc": "Windows 7 SP1 32-bit via WinPE & Samba"
    },
    {
        "slug": "winserver",
        "name": "Windows Server (2025/2022/2019)",
        "type": "windows",
        "desc": "Windows Server editions via WinPE & Samba"
    },
    # Popular Modified / Gaming Windows Distributions
    {
        "slug": "tiny11",
        "name": "Tiny11 (Ultra-Lightweight Win11)",
        "type": "windows",
        "desc": "Stripped, debloated Windows 11 for low-RAM PCs"
    },
    {
        "slug": "tiny10",
        "name": "Tiny10 (Ultra-Lightweight Win10)",
        "type": "windows",
        "desc": "Stripped, debloated Windows 10 for older PCs"
    },
    {
        "slug": "ghost_spectre",
        "name": "Ghost Spectre Superlite (Gaming)",
        "type": "windows",
        "desc": "Popular debloated gaming build (Win10/Win11)"
    },
    {
        "slug": "atlas_revi",
        "name": "AtlasOS / ReviOS (Low Latency)",
        "type": "windows",
        "desc": "Performance-tuned low-latency Windows edition"
    },
    # Diagnostic & Rescue Windows PE Environments
    {
        "slug": "hbcd_pe",
        "name": "Hiren's BootCD PE (Rescue Suite)",
        "type": "windows",
        "desc": "Full WinPE diagnostic desktop with repair tools"
    },
    {
        "slug": "strelec_pe",
        "name": "Sergei Strelec WinPE (Technician Suite)",
        "type": "windows",
        "desc": "Comprehensive technician repair & imaging suite"
    },
    # Legacy Windows
    {
        "slug": "winxp",
        "name": "Windows XP SP3 (Legacy 32-bit)",
        "type": "windows",
        "desc": "Classic Windows XP for vintage retro systems"
    },
    # Popular Linux Distributions
    {
        "slug": "ubuntu",
        "name": "Ubuntu Desktop / Server",
        "type": "linux",
        "desc": "Ubuntu LTS Live over HTTP"
    },
    {
        "slug": "linuxmint",
        "name": "Linux Mint (Live & Installer)",
        "type": "linux",
        "desc": "Linux Mint Cinnamon/XFCE/MATE over HTTP"
    },
    {
        "slug": "debian",
        "name": "Debian GNU/Linux",
        "type": "linux",
        "desc": "Debian Stable Live & Netinst over HTTP"
    },
    {
        "slug": "fedora",
        "name": "Fedora Workstation / Server",
        "type": "linux",
        "desc": "Fedora Workstation Live over HTTP"
    },
    {
        "slug": "kali",
        "name": "Kali Linux (Security & Pentest)",
        "type": "linux",
        "desc": "Kali Linux Live Forensic & Security Tools"
    },
    {
        "slug": "popos",
        "name": "Pop!_OS (by System76)",
        "type": "linux",
        "desc": "Pop!_OS Desktop Live over HTTP"
    },
    {
        "slug": "zorin",
        "name": "Zorin OS (Windows Alternative)",
        "type": "linux",
        "desc": "Zorin OS Core/Lite Live over HTTP"
    },
    {
        "slug": "mxlinux",
        "name": "MX Linux (Debian Stable)",
        "type": "linux",
        "desc": "MX Linux Lightweight Live over HTTP"
    },
    {
        "slug": "arch",
        "name": "Arch Linux (Rolling Release)",
        "type": "linux",
        "desc": "Arch Linux Netboot & CLI Installer"
    },
    {
        "slug": "manjaro",
        "name": "Manjaro Linux",
        "type": "linux",
        "desc": "Manjaro Desktop Live over HTTP"
    },
    {
        "slug": "cachyos",
        "name": "CachyOS (Performance Linux)",
        "type": "linux",
        "desc": "CachyOS Arch-based Optimized Live over HTTP"
    },
    {
        "slug": "bodhi",
        "name": "Bodhi Linux (Moksha Desktop)",
        "type": "linux",
        "desc": "Bodhi Linux Ultra-Lightweight Live over HTTP"
    },
    {
        "slug": "custom_linux",
        "name": "Generic / Custom Linux Live ISO",
        "type": "linux",
        "desc": "Any generic or custom bootable Linux ISO"
    },
    # Apple macOS & Recovery
    {
        "slug": "macos_recovery",
        "name": "Apple macOS Online Recovery",
        "type": "apple",
        "desc": "macOS NetBoot & OpenCore EFI Environment"
    },
    {
        "slug": "apple_diag",
        "name": "Apple Hardware Test & Diagnostics",
        "type": "apple",
        "desc": "Apple Diagnostics (AHT) Utility"
    },
    {
        "slug": "custom_apple",
        "name": "Generic Apple / DMG Image",
        "type": "apple",
        "desc": "Generic Apple DMG / EFI Boot Image"
    },
    {
        "slug": "custom",
        "name": "Custom Windows / WIM Image",
        "type": "windows",
        "desc": "Custom Windows ISO or WIM Image"
    }
]

OS_CATEGORIES = ["All Systems", "Windows", "Linux", "Apple macOS"]

CATEGORY_TYPE_MAP = {
    "All Systems": None,
    "Windows": "windows",
    "Linux": "linux",
    "Apple macOS": "apple"
}

TYPE_CATEGORY_MAP = {
    "windows": "Windows",
    "linux": "Linux",
    "apple": "Apple macOS"
}

def get_presets_by_category(category: str) -> List[Dict[str, Any]]:
    target_type = CATEGORY_TYPE_MAP.get(category)
    if not target_type:
        return OS_PRESETS
    return [p for p in OS_PRESETS if p.get("type") == target_type]

def detect_os_from_iso(iso_path: str) -> Optional[Dict[str, Any]]:
    """
    Intelligently detects OS profile from ISO filename or structure.
    """
    path_obj = Path(iso_path)
    if not path_obj.exists():
        return None

    fname = path_obj.name.lower()
    is_x86 = any(x in fname for x in ["x86", "32bit", "32-bit", "x32", "i386"])

    # Popular Custom & Gaming Windows Distributions
    if "tiny11" in fname or "tiny-11" in fname:
        return next((p for p in OS_PRESETS if p["slug"] == "tiny11"), None)

    if "tiny10" in fname or "tiny-10" in fname:
        return next((p for p in OS_PRESETS if p["slug"] == "tiny10"), None)

    if "ghost" in fname or "spectre" in fname or "superlite" in fname:
        return next((p for p in OS_PRESETS if p["slug"] == "ghost_spectre"), None)

    if "atlas" in fname or "revi" in fname or "revios" in fname:
        return next((p for p in OS_PRESETS if p["slug"] == "atlas_revi"), None)

    # Diagnostic & Rescue Windows PE
    if "hiren" in fname or "hbcd" in fname:
        return next((p for p in OS_PRESETS if p["slug"] == "hbcd_pe"), None)

    if "strelec" in fname or "sergei" in fname:
        return next((p for p in OS_PRESETS if p["slug"] == "strelec_pe"), None)

    # Windows LTSC / IoT Enterprise
    if "ltsc" in fname or "iot" in fname:
        if any(k in fname for k in ["11", "win11"]):
            return next((p for p in OS_PRESETS if p["slug"] == "win11_ltsc"), None)
        return next((p for p in OS_PRESETS if p["slug"] == "win10_ltsc"), None)

    # Windows XP
    if any(k in fname for k in ["winxp", "windows xp", "windowsxp", "win_xp"]):
        return next((p for p in OS_PRESETS if p["slug"] == "winxp"), None)

    # Windows 7 patterns (including MSDN checksum hashes like 677332, 676939)
    if any(k in fname for k in ["win7", "windows 7", "windows7", "win_7", "7_ultimate", "7_professional", "7_home", "7_enterprise", "677332", "676939"]):
        if is_x86:
            return next((p for p in OS_PRESETS if p["slug"] == "win7_x86"), None)
        return next((p for p in OS_PRESETS if p["slug"] == "win7"), None)

    # Windows 11 patterns
    if any(k in fname for k in ["win11", "windows 11", "windows11", "win_11"]):
        return next((p for p in OS_PRESETS if p["slug"] == "win11"), None)

    # Windows 10 patterns
    if any(k in fname for k in ["win10", "windows 10", "windows10", "win_10"]):
        return next((p for p in OS_PRESETS if p["slug"] == "win10"), None)

    # Windows 8.1 patterns (e.g. W81X64, win8.1, windows 8.1)
    if any(k in fname for k in ["w81", "win81", "win8.1", "windows 8.1", "windows8.1", "8.1", "8_1"]):
        if is_x86:
            return next((p for p in OS_PRESETS if p["slug"] == "win81_x86"), None)
        return next((p for p in OS_PRESETS if p["slug"] == "win81"), None)

    # Windows 8 patterns (e.g. W8X64, win8, windows 8)
    if any(k in fname for k in ["w8", "win8", "windows 8", "windows8"]):
        if is_x86:
            return next((p for p in OS_PRESETS if p["slug"] == "win8_x86"), None)
        return next((p for p in OS_PRESETS if p["slug"] == "win8"), None)

    # Windows Server patterns
    if any(k in fname for k in ["server", "winserver", "2025", "2022", "2019", "2016", "2012"]):
        return next((p for p in OS_PRESETS if p["slug"] == "winserver"), None)

    # Linux distributions
    if "mint" in fname:
        return next((p for p in OS_PRESETS if p["slug"] == "linuxmint"), None)

    if "ubuntu" in fname:
        return next((p for p in OS_PRESETS if p["slug"] == "ubuntu"), None)

    if "bodhi" in fname:
        return next((p for p in OS_PRESETS if p["slug"] == "bodhi"), None)

    if "debian" in fname:
        return next((p for p in OS_PRESETS if p["slug"] == "debian"), None)

    if "fedora" in fname:
        return next((p for p in OS_PRESETS if p["slug"] == "fedora"), None)

    if "kali" in fname:
        return next((p for p in OS_PRESETS if p["slug"] == "kali"), None)

    if "pop" in fname or "pop-os" in fname or "pop_os" in fname:
        return next((p for p in OS_PRESETS if p["slug"] == "popos"), None)

    if "zorin" in fname:
        return next((p for p in OS_PRESETS if p["slug"] == "zorin"), None)

    if "mx" in fname or "mxlinux" in fname:
        return next((p for p in OS_PRESETS if p["slug"] == "mxlinux"), None)

    if "manjaro" in fname:
        return next((p for p in OS_PRESETS if p["slug"] == "manjaro"), None)

    if "cachy" in fname:
        return next((p for p in OS_PRESETS if p["slug"] == "cachyos"), None)

    if "arch" in fname:
        return next((p for p in OS_PRESETS if p["slug"] == "arch"), None)

    if "linux" in fname:
        return next((p for p in OS_PRESETS if p["slug"] == "custom_linux"), None)

    # Apple macOS & Diagnostics detection
    if any(k in fname for k in ["macos", "osx", "os_x", "mac_os", "opencore", "monterey", "ventura", "sonoma", "sequoia", "catalina", "bigsur", "mojave", "highsierra", "aht", "apple"]):
        if any(d in fname for d in ["diag", "hardware", "aht"]):
            return next((p for p in OS_PRESETS if p["slug"] == "apple_diag"), None)
        return next((p for p in OS_PRESETS if p["slug"] == "macos_recovery"), None)
    if fname.endswith(".dmg"):
        return next((p for p in OS_PRESETS if p["slug"] == "custom_apple"), None)

    return None

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
                        
                        payload_dir = self.srv_samba / slug if (self.srv_samba / slug).exists() else child
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

        # Sort according to user-defined priority order stored in meta["_order"]
        order = meta.get("_order", [])
        if order:
            def get_sort_key(item):
                try:
                    return (0, order.index(item["slug"]))
                except ValueError:
                    return (1, item["name"].lower())
            installed.sort(key=get_sort_key)

        return installed

    def move_os_priority(self, slug: str, direction: int, server_ip: str = "192.168.42.1", http_port: int = 8080) -> bool:
        """
        Moves the operating system up (-1) or down (+1) in boot priority order.
        """
        installed = self.get_installed_os_list()
        slugs = [item["slug"] for item in installed]
        if slug not in slugs:
            return False

        idx = slugs.index(slug)
        new_idx = idx + direction
        if new_idx < 0 or new_idx >= len(slugs):
            return False

        # Swap positions
        slugs[idx], slugs[new_idx] = slugs[new_idx], slugs[idx]

        meta = self._load_meta()
        meta["_order"] = slugs
        self._save_meta(meta)

        self.generate_ipxe_menu(server_ip, http_port)
        return True

    def set_os_as_default(self, slug: str, server_ip: str = "192.168.42.1", http_port: int = 8080) -> bool:
        """
        Sets the specified operating system to #1 (Default Auto-Boot).
        """
        installed = self.get_installed_os_list()
        slugs = [item["slug"] for item in installed]
        if slug not in slugs:
            return False

        slugs.remove(slug)
        slugs.insert(0, slug)

        meta = self._load_meta()
        meta["_order"] = slugs
        self._save_meta(meta)

        self.generate_ipxe_menu(server_ip, http_port)
        return True

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
                subprocess.run(['chmod', '-R', '777', str(samba_dir)], capture_output=True)

                on_progress(0.65, "Locating boot assets (bootmgr, BCD, boot.sdi, boot.wim)...")
                self._copy_case_insensitive(samba_dir, "bootmgr", boot_dir / "bootmgr", on_log)
                self._copy_case_insensitive(samba_dir, "bootmgr.efi", boot_dir / "bootmgr.efi", on_log)
                self._copy_case_insensitive(samba_dir, "bcd", boot_dir / "BCD", on_log)
                self._copy_case_insensitive(samba_dir, "boot.sdi", boot_dir / "boot.sdi", on_log)
                self._copy_case_insensitive(samba_dir, "boot.wim", boot_dir / "boot.wim", on_log)

                # Ensure lowercase bcd link exists for wimboot compatibility
                try:
                    (boot_dir / "bcd").symlink_to("BCD")
                except Exception:
                    pass

                boot_wim = boot_dir / "boot.wim"
                if not boot_wim.exists():
                    raise FileNotFoundError("Could not find boot.wim in extracted ISO!")

                # Patch startnet.cmd with specific Samba share name
                on_progress(0.80, f"Injecting permanent Fast Network Installer into WinPE...")
                wimlib = shutil.which('wimlib-imagex')
                if wimlib and os_slug not in ["hbcd_pe", "strelec_pe"]:
                    # 1. Load pristine standalone startnet template from disk (zero python escaping hazards)
                    tpl_file = self.base_dir / "backend" / "templates" / "winpe_startnet.cmd"
                    if tpl_file.exists():
                        startnet_script = (
                            tpl_file.read_text(encoding='utf-8')
                            .replace("__OS_NAME__", os_name)
                            .replace("__SERVER_IP__", server_ip)
                            .replace("__OS_SLUG__", os_slug)
                        )
                    else:
                        raise FileNotFoundError(f"Missing WinPE template: {tpl_file}")
                    tmp_script = Path(f"/tmp/startnet_{os_slug}.cmd")
                    tmp_script.write_text(startnet_script, encoding='utf-8')

                    # 2. Also write standalone install.cmd directly into Samba share
                    install_cmd_script = f"""@echo off
title ZeroUSB Direct Fast Installer
set INDEX=1
if not "%1"=="" set INDEX=%1
set WIM_FILE=Z:\\sources\\install.wim
if not exist %WIM_FILE% set WIM_FILE=Z:\\sources\\install.esd
if not exist %WIM_FILE% set WIM_FILE=Z:\\install.wim
if not exist %WIM_FILE% set WIM_FILE=Z:\\install.esd

(
echo select disk 0
echo clean
echo convert mbr
echo create partition primary
echo format fs=ntfs quick label="Windows"
echo assign letter=C
echo active
) | diskpart > nul

dism /apply-image /imagefile:%WIM_FILE% /index:%INDEX% /applydir:C:\
if exist X:\\Drivers dism /image:C:\ /add-driver /driver:X:\Drivers /recurse > nul 2>&1
bcdboot C:\Windows /s C: /f ALL
echo [OK] Done! Rebooting in 5 seconds...
ping -n 6 127.0.0.1 > nul
wpeutil reboot
"""
                    try:
                        (samba_dir / "install.cmd").write_text(install_cmd_script, encoding='utf-8')
                        (samba_dir / "sources" / "install.cmd").write_text(install_cmd_script, encoding='utf-8')

                        # Auto-inject ei.cfg to bypass product key prompt during Windows Setup
                        sources_dir = samba_dir / "sources"
                        if sources_dir.exists():
                            (sources_dir / "ei.cfg").write_text("[EditionID]\n\n[Channel]\nRetail\n\n[VL]\n0\n", encoding='utf-8')
                            (samba_dir / "ei.cfg").write_text("[EditionID]\n\n[Channel]\nRetail\n\n[VL]\n0\n", encoding='utf-8')

                        # Auto-generate editions.txt with 32-bit vs 64-bit architecture details
                        wim_target = samba_dir / "sources" / "install.wim"
                        if not wim_target.exists():
                            wim_target = samba_dir / "install.wim"
                        if not wim_target.exists():
                            wim_target = samba_dir / "sources" / "install.esd"
                        if wim_target.exists() and wimlib:
                            wim_res = subprocess.run([wimlib, 'info', str(wim_target)], capture_output=True, text=True)
                            ed_lines = [
                                "=================================================================",
                                "  Available Windows Editions and Architecture:",
                                "=================================================================",
                                ""
                            ]
                            cur_ed = {}
                            for wl in wim_res.stdout.splitlines():
                                wl = wl.strip()
                                if wl.startswith("Index:"):
                                    if cur_ed:
                                        ed_lines.append(f"  [Index {cur_ed.get('idx','?')}]  {cur_ed.get('name','Windows'):<28} [{cur_ed.get('arch','Unknown')}]")
                                    cur_ed = {'idx': wl.split(":", 1)[1].strip()}
                                elif wl.startswith("Name:") and cur_ed and 'name' not in cur_ed:
                                    cur_ed['name'] = wl.split(":", 1)[1].strip()
                                elif wl.startswith("Architecture:") and cur_ed:
                                    wa = wl.split(":", 1)[1].strip().lower()
                                    cur_ed['arch'] = "64-bit (x64)" if "64" in wa else ("32-bit (x86)" if ("86" in wa or "32" in wa) else wa)
                            if cur_ed:
                                ed_lines.append(f"  [Index {cur_ed.get('idx','?')}]  {cur_ed.get('name','Windows'):<28} [{cur_ed.get('arch','Unknown')}]")
                            ed_lines.append("")
                            ed_lines.append("=================================================================")
                            ed_content = "\r\n".join(ed_lines) + "\r\n"
                            (samba_dir / "editions.txt").write_text(ed_content, encoding='utf-8')
                            (samba_dir / "sources" / "editions.txt").write_text(ed_content, encoding='utf-8')
                    except Exception:
                        pass

                    # 3. Create update directives for boot.wim
                    tmp_winpeshl = Path(f"/tmp/winpeshl_{os_slug}.ini")
                    tmp_winpeshl.write_text('[LaunchApp]\nAppPath = %SystemRoot%\\system32\\cmd.exe /k %SystemRoot%\\system32\\startnet.cmd\n\n[LaunchApps]\n%SystemRoot%\\system32\\cmd.exe, /k %SystemRoot%\\system32\\startnet.cmd\n', encoding='utf-8')

                    tmp_cmd = Path(f"/tmp/wim_update_{os_slug}.txt")
                    update_directives = [
                        f"add {tmp_winpeshl} /Windows/System32/winpeshl.ini",
                        f"add {tmp_script} /Windows/System32/startnet.cmd"
                    ]

                    # Add Atheros / Realtek network drivers if available in /tmp/ar8162_ansi
                    if Path('/tmp/ar8162_ansi').exists():
                        update_directives.append("add /tmp/ar8162_ansi /Drivers/Atheros_AR8162")

                    tmp_cmd.write_text('\n'.join(update_directives) + '\n', encoding='utf-8')

                    try:
                        info_res = subprocess.run([wimlib, 'info', str(boot_wim)], capture_output=True, text=True)
                        match = re.search(r'Image Count:\s*(\d+)', info_res.stdout)
                        img_count = int(match.group(1)) if match else 2
                    except Exception:
                        img_count = 2

                    for idx in range(1, img_count + 1):
                        on_log(f"[*] Injecting ZeroUSB menu into boot.wim Image {idx}/{img_count}...")
                        with open(tmp_cmd, 'r') as uf:
                            res = subprocess.run([wimlib, 'update', str(boot_wim), str(idx)], stdin=uf, capture_output=True, text=True)
                            if res.returncode != 0:
                                on_log(f"[!] Warning updating image {idx}: {res.stderr}")

                    tmp_script.unlink(missing_ok=True)
                    tmp_winpeshl.unlink(missing_ok=True)
                    tmp_cmd.unlink(missing_ok=True)

                    # 4. Mirror to primary default boot.wim and set full 777 permissions
                    try:
                        shutil.copy2(boot_wim, self.srv_http_boot / "boot.wim")
                        subprocess.run(['chmod', '-R', '777', str(samba_dir), str(boot_dir)], capture_output=True)
                    except Exception:
                        pass

                    on_log(f"[✓] Permanent Fast DISM Network Installer & drivers injected for \\\\{server_ip}\\{os_slug}")

            elif os_type == "linux":
                on_progress(0.20, f"Preparing Linux files for Direct Network Mount...")
                self.srv_http_images.mkdir(parents=True, exist_ok=True)
                samba_dir = self.srv_samba / os_slug
                samba_dir.mkdir(parents=True, exist_ok=True)

                # 1. Copy full ISO for HTTP streaming fallback
                dst_iso = self.srv_http_images / f"{os_slug}.iso"
                if not dst_iso.exists():
                    on_log(f"[+] Copying ISO to HTTP images: {dst_iso}...")
                    shutil.copy2(iso_file, dst_iso)

                # 2. Extract full contents to Samba share for instant Direct CIFS Live Desktop
                on_progress(0.35, f"Extracting live filesystem to Samba share for Instant CIFS Boot...")
                on_log(f"[+] Extracting live filesystem to {samba_dir}...")
                cmd = [seven_zip, 'x', '-y', f'-o{samba_dir}', str(iso_file)]
                proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                for line in proc.stdout:
                    ls = line.strip()
                    if ls and ('%' in ls or 'Extracting' in ls or 'Everything is Ok' in ls):
                        on_log(f"  [7z] {ls}")
                proc.wait()
                subprocess.run(['chmod', '-R', '777', str(samba_dir)], capture_output=True)

                # 3. Locate kernel & initrd
                on_progress(0.85, "Locating Linux kernel & initrd...")
                self._copy_case_insensitive(samba_dir, "vmlinuz", boot_dir / "vmlinuz", on_log)
                self._copy_case_insensitive(samba_dir, "initrd", boot_dir / "initrd.lz", on_log)

            elif os_type == "apple":
                on_progress(0.20, f"Preparing Apple macOS / OpenCore boot assets from {iso_file.name}...")
                self.srv_http_images.mkdir(parents=True, exist_ok=True)
                dst_iso = self.srv_http_images / f"{os_slug}.iso"
                on_log(f"[+] Copying Apple image to HTTP images: {dst_iso}...")
                shutil.copy2(iso_file, dst_iso)

                # Extract EFI bootloader if present
                tmp_extract = Path(f"/tmp/apple_extract_{os_slug}")
                tmp_extract.mkdir(parents=True, exist_ok=True)
                subprocess.run([seven_zip, 'x', '-y', f'-o{tmp_extract}', str(iso_file), 'EFI/*', 'boot/*', '*.efi', 'System/*'], capture_output=True)
                self._copy_case_insensitive(tmp_extract, "bootx64.efi", boot_dir / "bootx64.efi", on_log)
                self._copy_case_insensitive(tmp_extract, "boot.efi", boot_dir / "boot.efi", on_log)
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
        key_index = 1

        menu_items.append("item --gap --             [ TIP: Press 1, 2, 3, 4, H, or R directly to select ]")
        menu_items.append("item --gap --             ------------------ Operating Systems -------------------")

        for item in installed:
            slug = item["slug"]
            name = item["name"]
            os_type = item["type"]
            k = str(key_index) if key_index <= 9 else chr(ord('a') + (key_index - 10))
            key_index += 1

            if os_type == "windows":
                menu_items.append(f"item --key {k} {slug:<18} [{k.upper()}] {name}")
                if item.get("is_legacy", False):
                    boot_targets.append(f"""
:{slug}
echo Booting {name} over HTTP...
kernel {http_base}/boot/${{wimboot_file}}
initrd {http_base}/boot/${{bootmgr_file}}  ${{bootmgr_name}}
initrd {http_base}/boot/BCD                bcd
initrd {http_base}/boot/boot.sdi           boot.sdi
initrd {http_base}/boot/boot.wim           boot.wim
boot || goto failed
""")
                else:
                    boot_targets.append(f"""
:{slug}
echo Booting {name} over HTTP...
kernel {http_base}/boot/${{wimboot_file}}
initrd {http_base}/boot/{slug}/${{bootmgr_file}}  ${{bootmgr_name}}
initrd {http_base}/boot/{slug}/BCD                bcd
initrd {http_base}/boot/{slug}/boot.sdi           boot.sdi
initrd {http_base}/boot/{slug}/boot.wim           boot.wim
boot || goto failed
""")
            elif os_type == "linux":
                has_cifs = (self.srv_samba / slug).exists() and any(
                    (self.srv_samba / slug / d).exists() for d in ["casper", "live"]
                )
                if has_cifs:
                    menu_items.append(f"item --key {k} {slug + '_live':<18} [{k.upper()}] Try {name} (Live Desktop)")
                    boot_targets.append(f"""
:{slug}_live
echo Booting {name} Live Desktop via Direct CIFS Mount...
kernel {http_base}/boot/{slug}/vmlinuz ip=dhcp boot=casper netboot=cifs nfsroot=//${{server_ip}}/{slug} quiet splash
initrd {http_base}/boot/{slug}/initrd.lz
boot || goto {slug}_ram

:{slug}_ram
echo Booting {name} via Full RAM ISO Streaming (Virtual CD-ROM Loopback)...
kernel {http_base}/boot/{slug}/vmlinuz ip=dhcp boot=casper netboot=url url={http_base}/images/{slug}.iso quiet splash
initrd {http_base}/boot/{slug}/initrd.lz
boot || goto failed
""")
                else:
                    menu_items.append(f"item --key {k} {slug:<18} [{k.upper()}] {name}")
                    if slug in ["debian", "kali"]:
                        boot_args = f"ip=dhcp boot=live components fetch={http_base}/images/{slug}.iso quiet splash"
                    elif slug == "fedora":
                        boot_args = f"ip=dhcp root=live:{http_base}/images/{slug}.iso rd.live.image quiet"
                    elif slug in ["arch", "manjaro", "cachyos"]:
                        boot_args = f"ip=dhcp archiso_http_srv={http_base}/images/ quiet"
                    else:
                        boot_args = f"ip=dhcp boot=casper netboot=url url={http_base}/images/{slug}.iso quiet splash"

                    boot_targets.append(f"""
:{slug}
echo Booting {name} kernel & initrd over HTTP...
kernel {http_base}/boot/{slug}/vmlinuz {boot_args}
initrd {http_base}/boot/{slug}/initrd.lz
boot || goto failed
""")
            elif os_type == "apple":
                menu_items.append(f"item --key {k} {slug:<18} [{k.upper()}] {name}")
                boot_targets.append(f"""
:{slug}
echo Booting {name} over HTTP...
chain {http_base}/boot/{slug}/bootx64.efi || chain {http_base}/boot/{slug}/boot.efi || chain {http_base}/images/{slug}.iso || goto failed
""")

        if not installed:
            menu_items.append("item --gap --             [!] No Operating Systems staged yet!")
            menu_items.append("item no_os                (Please stage an ISO from ZeroUSB app)")

        if installed:
            first = installed[0]
            first_cifs = (self.srv_samba / first["slug"]).exists() and any(
                (self.srv_samba / first["slug"] / d).exists() for d in ["casper", "live"]
            )
            default_target = f"{first['slug']}_live" if (first_cifs and first["type"] == "linux") else first["slug"]
        else:
            default_target = "boot_local"

        menu_items_str = "\n".join(menu_items)
        boot_targets_str = "\n".join(boot_targets)

        ipxe_script = f"""#!ipxe
 
set server_ip {server_ip}
set http_port {http_port}
set http_base http://${{server_ip}}:${{http_port}}

# Architecture auto-detection (Dual-Mode: UEFI 64-bit vs BIOS 32-bit CSM)
iseq ${{platform}} efi && goto mode_uefi || goto mode_bios

:mode_uefi
set mode_label UEFI (64-bit)
set wimboot_file wimboot.x86_64
set bootmgr_file bootmgr.efi
set bootmgr_name bootmgr.efi
goto menu

:mode_bios
set mode_label Legacy BIOS / CSM (32-bit)
set wimboot_file wimboot.i386
set bootmgr_file bootmgr
set bootmgr_name bootmgr
goto menu

:menu
menu ZeroUSB - Universal Deployment Server [Active Mode: ${{mode_label}}]
{menu_items_str}
item --gap --             ------------------ Local Actions -----------------------
item --key h boot_local           [H] Boot from Local Storage (SSD / NVMe / HDD)
item --key d ipxe_shell           [D] iPXE Diagnostic Shell
item --key r reboot               [R] Reboot Computer
choose --timeout 30000 --default {default_target} target && goto ${{target}}

{boot_targets_str}

:no_os
echo [!] No operating systems currently installed in ZeroUSB.
prompt Press any key to return to menu...
goto menu

:boot_local
echo Booting from local hard drive (Drive 0x80)...
sanboot --no-describe --drive 0x80 || exit 0

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
        try:
            (self.base_dir / "config" / "boot.ipxe").write_text(ipxe_script, encoding='utf-8')
        except Exception:
            pass

        # Also generate GRUB2 network boot configuration
        self.generate_grub_cfg(server_ip, http_port)

        return ipxe_script

    def generate_grub_cfg(self, server_ip: str, http_port: int = 8080) -> str:
        """
        Dynamically generates grub.cfg for GRUB2 Network Bootloader with full USB keyboard support.
        """
        installed = self.get_installed_os_list()
        http_base = f"http://{server_ip}:{http_port}"

        # Ensure srv/tftp/boot symlinks exist for TFTP kernel loading
        tftp_boot = self.srv_tftp / "boot"
        tftp_boot.mkdir(parents=True, exist_ok=True)
        if self.srv_http_boot.exists():
            for item in self.srv_http_boot.iterdir():
                dest = tftp_boot / item.name
                if not dest.exists() and item.name != "grub":
                    try:
                        dest.symlink_to(item)
                    except Exception:
                        pass

        cfg_lines = [
            'set default="0"',
            'set timeout=15',
            '',
            '# Native input drivers for all USB and PS/2 keyboards',
            'insmod keylayouts',
            'insmod at_keyboard',
            'insmod usb',
            'insmod uhci',
            'insmod ohci',
            'insmod ehci',
            'insmod usb_keyboard',
            'terminal_input --append at_keyboard',
            'terminal_input --append usb_keyboard',
            'terminal_input --append console',
            '',
            'insmod all_video',
            'insmod font',
            'if loadfont (tftp)/boot/grub/fonts/unicode.pf2 ; then',
            '    insmod gfxterm',
            '    set gfxmode=auto',
            '    terminal_output gfxterm',
            'fi',
            '',
            'set menu_color_normal=white/black',
            'set menu_color_highlight=black/light-gray',
            '',
        ]

        # Linux entries
        for item in installed:
            if item["type"] == "linux":
                slug = item["slug"]
                name = item["name"]
                cfg_lines.extend([
                    f'# ==================== {name} ====================',
                    f'menuentry "Install {name} (Direct Fast Installer)" --id {slug}_install {{',
                    f'    echo "Launching {name} Direct Installer (only-ubiquity)..."',
                    f'    linux /boot/{slug}/vmlinuz ip=dhcp boot=casper only-ubiquity netboot=cifs nfsroot=//{server_ip}/{slug} quiet splash',
                    f'    echo "Loading initial ramdisk..."',
                    f'    initrd /boot/{slug}/initrd.lz',
                    f'}}',
                    f'',
                    f'menuentry "Try {name} without installing" --id {slug}_live {{',
                    f'    echo "Loading {name} kernel over network..."',
                    f'    linux /boot/{slug}/vmlinuz ip=dhcp boot=casper netboot=cifs nfsroot=//{server_ip}/{slug} quiet splash',
                    f'    echo "Loading initial ramdisk..."',
                    f'    initrd /boot/{slug}/initrd.lz',
                    f'}}',
                    f'',
                    f'menuentry "Try {name} In Safe Graphics Mode" --id {slug}_safe {{',
                    f'    echo "Loading {name} kernel (Safe Graphics)..."',
                    f'    linux /boot/{slug}/vmlinuz ip=dhcp boot=casper nomodeset xforcevesa netboot=cifs nfsroot=//{server_ip}/{slug} quiet splash',
                    f'    echo "Loading initial ramdisk..."',
                    f'    initrd /boot/{slug}/initrd.lz',
                    f'}}',
                    f'',
                    f'menuentry "{name} (Full RAM Virtual CD-ROM Mode)" --id {slug}_ram {{',
                    f'    echo "Loading {name} ISO into RAM..."',
                    f'    linux /boot/{slug}/vmlinuz ip=dhcp boot=casper only-ubiquity netboot=url url={http_base}/images/{slug}.iso quiet splash',
                    f'    echo "Loading initial ramdisk..."',
                    f'    initrd /boot/{slug}/initrd.lz',
                    f'}}',
                    f'',
                    f'menuentry "Check disc for defects" --id {slug}_check {{',
                    f'    echo "Checking media integrity for {name}..."',
                    f'    linux /boot/{slug}/vmlinuz ip=dhcp boot=casper integrity-check netboot=cifs nfsroot=//{server_ip}/{slug} quiet splash',
                    f'    echo "Loading initial ramdisk..."',
                    f'    initrd /boot/{slug}/initrd.lz',
                    f'}}',
                    f'',
                ])
            elif item["type"] == "windows":
                slug = item["slug"]
                name = item["name"]
                cfg_lines.extend([
                    f'# ==================== {name} ====================',
                    f'menuentry "{name}" --id {slug} {{',
                    f'    echo "Loading Windows Bootloader..."',
                    f'    insmod chain',
                    f'    chainloader /boot/{slug}/bootmgr.efi',
                    f'}}',
                    f'',
                ])

        # Standard navigation options
        cfg_lines.extend([
            'menuentry "Boot from first hard drive" {',
            '    set root=(hd0)',
            '    chainloader +1',
            '}',
            '',
            'menuentry "Reboot Computer" {',
            '    reboot',
            '}',
            '',
            'menuentry "Power Off" {',
            '    halt',
            '}',
        ])

        content = "\n".join(cfg_lines) + "\n"
        grub_cfg_file = self.srv_tftp / "boot" / "grub" / "grub.cfg"
        grub_cfg_file.parent.mkdir(parents=True, exist_ok=True)
        grub_cfg_file.write_text(content, encoding='utf-8')
        return content

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
                fl = file.lower()
                if fl == target_lower or fl.startswith(target_lower + ".") or fl.startswith(target_lower):
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
