import os
import shutil
import subprocess
import threading
from pathlib import Path
from typing import Callable, Optional

class ISOExtractor:
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.srv_http_boot = base_dir / 'srv' / 'http' / 'boot'
        self.srv_samba_win = base_dir / 'srv' / 'samba' / 'windows'
        self._is_running = False

    @property
    def is_running(self) -> bool:
        return self._is_running

    def extract_and_prepare(
        self,
        iso_path: str,
        server_ip: str,
        on_progress: Callable[[float, str], None],
        on_log: Callable[[str], None],
        on_finished: Callable[[bool, str], None]
    ):
        """
        Runs extraction and WinPE patching in a separate thread.
        """
        if self._is_running:
            on_finished(False, "An extraction task is already running.")
            return

        thread = threading.Thread(
            target=self._worker,
            args=(iso_path, server_ip, on_progress, on_log, on_finished),
            daemon=True
        )
        thread.start()

    def _worker(
        self,
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

            on_log(f"[*] Starting extraction for ISO: {iso_file.name}")
            on_log(f"[*] Target Server IP: {server_ip}")
            on_progress(0.05, "Preparing directories...")

            self.srv_http_boot.mkdir(parents=True, exist_ok=True)
            self.srv_samba_win.mkdir(parents=True, exist_ok=True)

            # Step 1: Extract full ISO into Samba directory using 7z
            on_progress(0.15, "Extracting full Windows ISO to Samba share...")
            on_log(f"[+] Extracting files to {self.srv_samba_win} using 7-Zip...")

            seven_zip = shutil.which('7z') or shutil.which('7za') or '7z'
            cmd = [seven_zip, 'x', '-y', f'-o{self.srv_samba_win}', str(iso_file)]
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )

            for line in process.stdout:
                line_str = line.strip()
                if line_str:
                    if '%' in line_str or 'Extracting' in line_str:
                        # Extract percentage if available
                        on_log(f"  [7z] {line_str}")
                    elif 'Everything is Ok' in line_str:
                        on_log("  [7z] Extraction finished OK.")

            process.wait()
            if process.returncode != 0:
                raise RuntimeError(f"7z extraction failed with exit code {process.returncode}")

            on_progress(0.65, "Locating and copying boot assets...")
            on_log("[+] Locating boot files (BCD, boot.sdi, boot.wim)...")

            # Step 2: Find and copy BCD, boot.sdi, boot.wim
            self._copy_case_insensitive(self.srv_samba_win, "bcd", self.srv_http_boot / "BCD", on_log)
            self._copy_case_insensitive(self.srv_samba_win, "boot.sdi", self.srv_http_boot / "boot.sdi", on_log)
            self._copy_case_insensitive(self.srv_samba_win, "boot.wim", self.srv_http_boot / "boot.wim", on_log)

            boot_wim_path = self.srv_http_boot / "boot.wim"
            if not boot_wim_path.exists():
                raise FileNotFoundError(f"Failed to find boot.wim in extracted ISO!")

            # Step 3: Inject custom startnet.cmd into boot.wim using wimlib-imagex
            on_progress(0.80, "Injecting automatic network mount into Windows PE...")
            on_log("[+] Customizing Windows PE startnet.cmd for automatic deployment...")

            wimlib = shutil.which('wimlib-imagex')
            if wimlib:
                startnet_script = f"""@echo off
title Windows Network Installer (via {server_ip})
wpeinit

echo.
echo =================================================================
echo   Connecting to Network Installer Server: \\\\{server_ip}\\windows
echo =================================================================
echo Initializing network adapter (waiting 6 seconds)...
ping 127.0.0.1 -n 7 > nul

echo Mounting Samba installation share...
net use Z: \\\\{server_ip}\\windows /user:nobody ""

if exist Z:\\setup.exe (
    echo.
    echo [OK] Setup files accessible! Starting Windows Setup...
    echo =================================================================
    Z:\\setup.exe
) else (
    echo.
    echo [ERROR] Z:\\setup.exe was not found on the network share!
    echo Opening WinPE Command Prompt for diagnostic inspection...
    cmd.exe
)
"""
                tmp_startnet = Path("/tmp/startnet_gui.cmd")
                tmp_startnet.write_text(startnet_script, encoding="utf-8")

                tmp_update_cmd = Path("/tmp/wim_update_gui.txt")
                tmp_update_cmd.write_text(f"add {tmp_startnet} /Windows/System32/startnet.cmd\n", encoding="utf-8")

                # Detect index (usually Index 2 has Windows Setup)
                try:
                    info_res = subprocess.run([wimlib, 'info', str(boot_wim_path)], capture_output=True, text=True)
                    target_index = "2" if "Image Count: 2" in info_res.stdout else "1"
                except Exception:
                    target_index = "2"

                on_log(f"[+] Injecting startnet.cmd into boot.wim (Image Index {target_index})...")
                with open(tmp_update_cmd, 'r') as update_file:
                    wim_proc = subprocess.run(
                        [wimlib, 'update', str(boot_wim_path), target_index],
                        stdin=update_file,
                        capture_output=True,
                        text=True
                    )

                if wim_proc.returncode == 0:
                    on_log("[✓] Successfully injected startnet.cmd into boot.wim!")
                else:
                    on_log(f"[!] Warning: wimlib update returned: {wim_proc.stderr}")

                # Clean up temporary files
                tmp_startnet.unlink(missing_ok=True)
                tmp_update_cmd.unlink(missing_ok=True)
            else:
                on_log("[!] Warning: wimlib-imagex not found. Skipping startnet.cmd injection.")

            on_progress(1.0, "Ready!")
            on_log("=================================================================")
            on_log("[✓] Windows ISO Extracted and Staged Successfully!")
            on_log("=================================================================")
            on_finished(True, "ISO extraction and boot image preparation completed successfully!")

        except Exception as e:
            on_log(f"[ERROR] Extraction failed: {str(e)}")
            on_finished(False, str(e))
        finally:
            self._is_running = False

    def purge_staged_media(self, on_log: Optional[Callable[[str], None]] = None) -> tuple[bool, str]:
        """
        Deletes all extracted Windows setup files and boot assets from the server,
        freeing up disk space while preserving wimboot kernel and iPXE bootloaders.
        """
        log = on_log or (lambda msg: None)
        try:
            log("[*] Purging extracted Windows installation files...")

            # 1. Clear Samba Windows share directory
            if self.srv_samba_win.exists():
                for item in self.srv_samba_win.iterdir():
                    try:
                        if item.is_dir():
                            shutil.rmtree(item, ignore_errors=True)
                        else:
                            item.unlink(missing_ok=True)
                    except Exception as err:
                        log(f"  [!] Warning removing {item.name}: {err}")
                log(f"  [✓] Cleared Samba directory ({self.srv_samba_win})")

            # 2. Clear extracted boot assets (BCD, boot.sdi, boot.wim) but preserve wimboot
            for asset_name in ["BCD", "bcd", "boot.sdi", "boot.wim"]:
                target = self.srv_http_boot / asset_name
                if target.exists():
                    target.unlink(missing_ok=True)
                    log(f"  [✓] Removed staged asset: {target.name}")

            log("[✓] All staged Windows ISO media removed and disk space freed!")
            return True, "All extracted Windows media and boot files removed successfully!"

        except Exception as e:
            log(f"[ERROR] Failed to purge media: {str(e)}")
            return False, str(e)

    def _copy_case_insensitive(self, search_dir: Path, target_name: str, dest_file: Path, on_log: Callable[[str], None]):
        target_lower = target_name.lower()
        for root, _, files in os.walk(search_dir):
            for file in files:
                if file.lower() == target_lower:
                    src = Path(root) / file
                    on_log(f"  Found {file} -> Copying to {dest_file.name}")
                    shutil.copy2(src, dest_file)
                    dest_file.chmod(0o644)
                    return
        on_log(f"  [!] Warning: {target_name} was not found in {search_dir}")
