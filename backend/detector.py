import os
import shutil
import subprocess
from pathlib import Path
from typing import List, Tuple, Dict, Any

def get_network_interfaces() -> List[Tuple[str, str, bool]]:
    """
    Returns a list of tuples: (interface_name, ip_address, is_default)
    """
    interfaces = []
    default_iface = ""

    # Detect default route interface
    try:
        res = subprocess.run(['ip', '-4', 'route', 'get', '8.8.8.8'], capture_output=True, text=True, timeout=2)
        if res.returncode == 0:
            parts = res.stdout.strip().split()
            if 'dev' in parts:
                default_iface = parts[parts.index('dev') + 1]
    except Exception:
        pass

    # Enumerate all active IPv4 interfaces
    try:
        res = subprocess.run(['ip', '-br', '-4', 'addr'], capture_output=True, text=True, timeout=2)
        if res.returncode == 0:
            for line in res.stdout.strip().split('\n'):
                line = line.strip()
                if not line:
                    continue
                parts = line.split()
                if len(parts) >= 3:
                    iface = parts[0]
                    state = parts[1]
                    ip_cidr = parts[2]
                    ip = ip_cidr.split('/')[0]
                    if iface != 'lo' and state.upper() == 'UP':
                        is_def = (iface == default_iface)
                        interfaces.append((iface, ip, is_def))
    except Exception:
        pass

    if not interfaces:
        interfaces.append(('enp3s0', '192.168.1.41', True))

    return interfaces


def check_dependencies(base_dir: Path) -> Dict[str, Dict[str, Any]]:
    """
    Checks status of all required CLI tools and bootloader binaries.
    """
    tools = {
        'dnsmasq': {
            'name': 'Dnsmasq (ProxyDHCP & TFTP)',
            'installed': shutil.which('dnsmasq') is not None,
            'path': shutil.which('dnsmasq') or 'Not installed',
            'desc': 'Provides non-conflicting ProxyDHCP and TFTP server'
        },
        'samba': {
            'name': 'Samba / smbd (SMB Share)',
            'installed': shutil.which('smbd') is not None or os.path.exists('/usr/sbin/smbd'),
            'path': shutil.which('smbd') or ('/usr/sbin/smbd' if os.path.exists('/usr/sbin/smbd') else 'Not installed'),
            'desc': 'Serves Windows installation media to Windows PE'
        },
        'wimtools': {
            'name': 'wimlib-imagex (WIM Patcher)',
            'installed': shutil.which('wimlib-imagex') is not None,
            'path': shutil.which('wimlib-imagex') or 'Not installed',
            'desc': 'Injects startnet.cmd auto-mount script into boot.wim'
        },
        '7zip': {
            'name': '7-Zip / 7z (ISO Extractor)',
            'installed': shutil.which('7z') is not None or shutil.which('7za') is not None,
            'path': shutil.which('7z') or shutil.which('7za') or 'Not installed',
            'desc': 'High-speed ISO extraction without root mounting'
        },
        'ipxe': {
            'name': 'iPXE UEFI Bootloader (ipxe.efi)',
            'installed': (base_dir / 'srv' / 'tftp' / 'ipxe.efi').exists() or os.path.exists('/usr/lib/ipxe/ipxe.efi'),
            'path': str(base_dir / 'srv' / 'tftp' / 'ipxe.efi') if (base_dir / 'srv' / 'tftp' / 'ipxe.efi').exists() else ('/usr/lib/ipxe/ipxe.efi' if os.path.exists('/usr/lib/ipxe/ipxe.efi') else 'Missing'),
            'desc': 'Universal network bootloader for modern UEFI PCs'
        },
        'wimboot': {
            'name': 'wimboot (Fast HTTP WIM Kernel)',
            'installed': (base_dir / 'srv' / 'http' / 'boot' / 'wimboot').exists(),
            'path': str(base_dir / 'srv' / 'http' / 'boot' / 'wimboot') if (base_dir / 'srv' / 'http' / 'boot' / 'wimboot').exists() else 'Missing',
            'desc': 'Boots Windows PE directly from RAM over HTTP in seconds'
        }
    }
    return tools


def check_staged_assets(base_dir: Path) -> Dict[str, Dict[str, Any]]:
    """
    Checks whether Windows boot assets are staged and ready.
    """
    http_boot = base_dir / 'srv' / 'http' / 'boot'
    samba_win = base_dir / 'srv' / 'samba' / 'windows'
    tftp_dir = base_dir / 'srv' / 'tftp'

    assets = {
        'ipxe_efi': {
            'name': 'iPXE Bootloader (ipxe.efi)',
            'path': tftp_dir / 'ipxe.efi',
            'ready': (tftp_dir / 'ipxe.efi').exists(),
            'size': _format_size((tftp_dir / 'ipxe.efi'))
        },
        'wimboot': {
            'name': 'wimboot Kernel',
            'path': http_boot / 'wimboot',
            'ready': (http_boot / 'wimboot').exists(),
            'size': _format_size((http_boot / 'wimboot'))
        },
        'bcd': {
            'name': 'BCD (Boot Configuration Data)',
            'path': http_boot / 'BCD',
            'ready': (http_boot / 'BCD').exists(),
            'size': _format_size((http_boot / 'BCD'))
        },
        'boot_sdi': {
            'name': 'boot.sdi (RAMDisk Envelope)',
            'path': http_boot / 'boot.sdi',
            'ready': (http_boot / 'boot.sdi').exists(),
            'size': _format_size((http_boot / 'boot.sdi'))
        },
        'boot_wim': {
            'name': 'boot.wim (Windows PE Image)',
            'path': http_boot / 'boot.wim',
            'ready': (http_boot / 'boot.wim').exists(),
            'size': _format_size((http_boot / 'boot.wim'))
        },
        'setup_exe': {
            'name': 'Windows Setup Media (setup.exe)',
            'path': samba_win / 'setup.exe',
            'ready': (samba_win / 'setup.exe').exists(),
            'size': _format_size((samba_win / 'setup.exe'))
        }
    }
    return assets


def _format_size(path: Path) -> str:
    if not path.exists():
        return 'Missing'
    try:
        size = path.stat().st_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"
    except Exception:
        return 'Available'
