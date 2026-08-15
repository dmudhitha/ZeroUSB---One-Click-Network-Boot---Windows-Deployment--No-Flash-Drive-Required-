<div align="center">

<img src="assets/icon.png" width="140" height="140" alt="ZeroUSB App Icon" style="border-radius: 28px; box-shadow: 0 10px 30px rgba(0,0,0,0.4);" />

# ⚡ ZeroUSB

### 🚀 *One-Click Network Boot Server to Install Windows & OS Images (No Flash Drive Required)*

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![OS](https://img.shields.io/badge/Platform-Linux%20%7C%20Ubuntu-E95420?style=for-the-badge&logo=ubuntu&logoColor=white)](https://ubuntu.com)
[![PXE](https://img.shields.io/badge/Protocol-iPXE%20%7C%20ProxyDHCP-10B981?style=for-the-badge)](https://ipxe.org)
[![UI](https://img.shields.io/badge/GUI-CustomTkinter-2563EB?style=for-the-badge)](https://customtkinter.tomschimansky.com)
[![Status](https://img.shields.io/badge/Status-Tested%20%26%20Ready-success?style=for-the-badge)]()

<br/>

**ZeroUSB** turns your Linux machine into an enterprise-grade, high-speed **PXE Network Installation Server**. Deploy **Windows 10, Windows 11, and Windows Server** directly to bare-metal PCs or Virtual Machines across your local network without USB flash drives or Windows Server WDS.

</div>

---

## 📑 Table of Contents
- [🌟 Key Highlights](#-key-highlights)
- [🌐 Network Architecture & Topology](#-network-architecture--topology)
- [🖥️ Graphical Desktop Application (GUI)](#️-graphical-desktop-application-gui)
- [⚡ Quick Start Guide](#-quick-start-guide)
- [💻 Booting the Target Client PC](#-booting-the-target-client-pc)
- [📊 Real-Time Network Telemetry](#-real-time-network-telemetry)
- [🛠️ Diagnostics & Pre-Flight Testing](#️-diagnostics--pre-flight-testing)
- [📂 Repository Directory Hierarchy](#-repository-directory-hierarchy)
- [🔍 Troubleshooting Matrix](#-troubleshooting-matrix)
- [🧠 Obsidian Knowledge Base Integration](#-obsidian-knowledge-base-integration)

---

## 🌟 Key Highlights

- **🛡️ Non-Invasive ProxyDHCP (`dnsmasq`):** Operates on port `4011` alongside your existing home/office router without replacing or conflicting with your router's DHCP pool.
- **⚡ 100x Faster HTTP Streaming (`wimboot`):** Streams the 688 MB `boot.wim` directly into the client PC's RAM in **10–20 seconds** over HTTP instead of slow TFTP.
- **🤖 Zero-Touch WinPE Auto-Mount:** Automatically patches `startnet.cmd` inside `boot.wim` using `wimlib-imagex` to connect `\\server\windows` and trigger `setup.exe` automatically.
- **📊 Real-Time Network Data Flow Monitor:** Dynamic 60fps rolling waveform canvas tracking live upload (TX), download (RX), peak transfer speeds, and active boot stages.
- **🎛️ Cross-Architecture Support:** Automatically detects and serves both **Modern UEFI (x64)** and **Legacy BIOS** client machines.

---

## 🌐 Network Architecture & Topology

```
                       ┌──────────────────────────────────┐
                       │       Your Home / Office         │
                       │        Internet Router           │
                       │         (192.168.1.1)            │
                       └────────────────┬─────────────────┘
                                        │
             ┌──────────────────────────┴──────────────────────────┐
             │                                                     │
   [ Ethernet Cable ]                                     [ Ethernet Cable ]
             │                                                     │
             ▼                                                     ▼
┌────────────────────────────┐                         ┌────────────────────────────┐
│      THIS PC (Linux)       │                         │     TARGET CLIENT PC       │
│   192.168.1.41 (Server)    │ ══════════════════════► │    Blank SSD / New Build   │
│                            │   Streams iPXE Boot,    │                            │
│ • CustomTkinter GUI        │   WinPE (HTTP:8080)     │ 1. Press F12 at power-on   │
│ • ProxyDHCP + TFTP Server  │   & Windows Media (SMB) │ 2. Select 'Network Boot'   │
│ • Samba \\windows Share    │   at ~100 MB/s (1 Gbps) │ 3. Installs Windows to SSD │
└────────────────────────────┘                         └────────────────────────────┘
```

---

## 🖥️ Graphical Desktop Application (GUI)

Launch the visual application with a single command:

```bash
python3 /home/mudhitha/System/Network-Installer/app.py
```
*(Or open your Linux application launcher and select **"Windows Network PXE Installer"**).*

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│ ⚡ Windows Network PXE Installer                                 ● SERVING PXE  │
├─────────────────────────────────────────────────────────────────────────────────┤
│ [🎛️ Control Center & Telemetry]  [💿 ISO Manager]  [📦 Dependencies]  [📜 Logs] │
├─────────────────────────────────────────────────────────────────────────────────┤
│ 📊 Real-Time Network Data Flow & Throughput                                     │
│  TX: 84.5 MB/s | RX: 120 KB/s | Peak: 112.5 MB/s | Total: 3.4 GB               │
│                                                                                 │
│   120 MB/s ┼                     ╭────────╮                                     │
│    80 MB/s ┼                  ╭──╯        ╰────────╮                            │
│    40 MB/s ┼        ╭─────────╯                    ╰──────                      │
│     0 KB/s ┴────────┴─────────────────────────────────────┴                     │
│              60s ago                  30s ago                Now                │
├─────────────────────────────────────────────────────────────────────────────────┤
│ Pipeline: [1. ProxyDHCP] ➔ [2. TFTP Bootloader] ➔ [3. HTTP WinPE] ➔ [4. Samba]  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## ⚡ Quick Start Guide

### Step 1: Install Dependencies & Download Bootloaders
1. Open the app and go to the **📦 Dependencies & Tools** tab.
2. Click **"📥 Install & Download All Dependencies"**.
   *(CLI Alternative: `bash scripts/install-prereqs.sh`)*

---

### Step 2: Prepare & Stage Windows ISO
1. Go to the **💿 ISO & Image Manager** tab.
2. Browse and select your Windows 10, Windows 11, or Server `.iso` file.
3. Click **"⚡ Extract & Prepare Windows Boot Image"**.
   *(CLI Alternative: `bash scripts/extract-iso.sh /path/to/windows.iso`)*

---

### Step 3: Start the PXE Server
1. Go to the **🎛️ Control Center** tab.
2. Confirm your network interface (e.g., `enp3s0 - 192.168.1.41`).
3. Click **"🚀 Start PXE Network Server"**. The badge turns **green** (`● SERVING PXE`).
   *(CLI Alternative: `sudo bash scripts/start-server.sh`)*

---

## 💻 Booting the Target Client PC

1. **Connect Cable:** Plug an Ethernet cable between the target PC and your router/switch.
2. **Power On & Enter Boot Menu:** Turn on the PC and repeatedly tap the **Boot Menu** key:
   - **Dell / Alienware:** `F12`
   - **Lenovo / ThinkPad:** `F12` or `Enter`
   - **HP:** `F9` or `Esc`
   - **ASUS / Acer / MSI:** `F8`, `F11`, or `F12`
3. **Select Network Boot:** Choose **"UEFI: Network Boot"** (or **"PXE IPv4"**).
4. **Automated Setup:**
   - Client loads `ipxe.efi` via TFTP.
   - Downloads `boot.wim` into RAM in 15 seconds.
   - WinPE starts and mounts `\\192.168.1.41\windows` as `Z:`.
   - Windows Setup GUI launches directly!

---

## 📊 Real-Time Network Telemetry

The built-in telemetry canvas continuously monitors your active network interface:
- **Emerald Wave (`#10b981`):** Represents server-to-client transmission (bootloaders, WinPE, setup media).
- **Sky Blue Line (`#38bdf8`):** Incoming acknowledgments from the target PC.
- **Dynamic Auto-Ranging:** Scale automatically adjusts between `KB/s`, `MB/s`, and `GB/s`.
- **Pipeline Stage Highlighting:** Illuminates when `ProxyDHCP`, `TFTP`, `HTTP`, or `Samba` are actively serving data.

---

## 🛠️ Diagnostics & Pre-Flight Testing

Run the included 14-point pre-flight diagnostic tool to verify all services and assets:

```bash
bash scripts/test-server.sh
```

```text
=================================================================
   Windows Network PXE Installer - Pre-Flight Diagnostics        
=================================================================

[1] Checking Network Interface & IP Configuration...
  [PASS] Server IP detected (192.168.1.41)
  [PASS] Network interface UP (enp3s0)

[2] Checking TFTP Network Bootloaders...
  [PASS] ipxe.efi (UEFI x64 Bootloader)
  [PASS] undionly.kpxe (Legacy BIOS Bootloader)
  [PASS] boot.ipxe (iPXE Boot Script)

[3] Checking HTTP Stream Assets (wimboot & WinPE)...
  [PASS] wimboot (Fast WIM Kernel)
  [PASS] BCD (Boot Configuration Data)
  [PASS] boot.sdi (RAMDisk Descriptor)
  [PASS] boot.wim (Windows PE Image)

[4] Checking WinPE Auto-Mount Script Injection...
  [PASS] startnet.cmd present in boot.wim (Index 2)

[5] Checking Samba Windows Setup Share Media...
  [PASS] setup.exe accessible
  [PASS] sources directory accessible

[6] Validating Service Configurations...
  [PASS] dnsmasq.conf syntax
  [PASS] smb.conf syntax

=================================================================
  ✔ ALL 14 CHECKS PASSED! Your server is 100% ready for PXE boot.
=================================================================
```

---

## 📂 Repository Directory Hierarchy

```text
/home/mudhitha/System/Network-Installer/
├── app.py                      # 🎛️ Main CustomTkinter Graphical Application
├── ui/
│   ├── theme.py                # 🎨 Modern Slate styling & color tokens
│   └── network_chart.py        # 📊 Real-time 60fps network data flow canvas
├── backend/
│   ├── detector.py             # 🔍 Hardware interface & dependency inspector
│   ├── network_monitor.py      # 📈 Per-second TX/RX traffic monitor (psutil)
│   ├── server_manager.py       # 🚀 Multi-service lifecycle manager
│   ├── iso_extractor.py        # 💿 7z extractor & WinPE startnet.cmd patcher
│   └── installer.py            # 📦 Automated dependency & bootloader downloader
├── config/
│   ├── dnsmasq.conf            # ⚙️ ProxyDHCP & TFTP server setup
│   ├── smb.conf                # ⚙️ Samba guest configuration for \\windows
│   └── boot.ipxe               # ⚙️ Dynamic iPXE interactive bootloader menu
├── srv/
│   ├── tftp/                   # 📁 TFTP root (ipxe.efi, undionly.kpxe)
│   ├── http/boot/              # 📁 HTTP root (wimboot, BCD, boot.sdi, boot.wim)
│   └── samba/windows/          # 📁 SMB root (Full extracted Windows ISO media)
├── scripts/
│   ├── install-prereqs.sh      # 📥 Installs packages & fetches bootloaders
│   ├── extract-iso.sh          # 💿 CLI ISO extractor & WinPE injector
│   ├── clean-iso.sh            # 🗑️ Purges extracted ISO media to free disk space
│   ├── start-server.sh         # 🚀 CLI server starter
│   ├── stop-server.sh          # 🛑 CLI server stopper
│   └── test-server.sh          # 🩺 14-point diagnostic test suite
└── README.md                   # 📖 Documentation
```

---

## 🔍 Troubleshooting Matrix

| Issue | Root Cause | Solution |
| :--- | :--- | :--- |
| **`PXE-E53: No boot filename received`** | Target PC did not receive ProxyDHCP response or firewall blocked UDP ports. | Run `sudo ufw allow 67/udp && sudo ufw allow 4011/udp && sudo ufw allow 69/udp`. |
| **`TFTP Timeout / Open Timeout`** | Dnsmasq TFTP service is not running. | Check `sudo systemctl status dnsmasq` or start via the GUI app. |
| **`wimboot: out of memory`** | Client PC has insufficient RAM (< 2 GB) or 32-bit UEFI. | Ensure target PC has $\ge 4\text{ GB}$ RAM and 64-bit UEFI enabled. |
| **`WinPE stops with System error 53`** | Target PC lacks Ethernet NIC drivers in WinPE. | Inject NIC `.inf` drivers into `boot.wim` using `wimlib-imagex update boot.wim 2`. |
| **`Access Denied on net use Z:`** | Samba guest account mapping issue. | Verify `guest ok = yes` and `force user = nobody` in `config/smb.conf`. |

---

## 🧠 Obsidian Knowledge Base Integration

This project is connected directly with the Obsidian Second Brain vault:

- **Comprehensive Knowledge Guide:** [`02_Knowledge/windows-network-pxe-installation.md`](file:///home/mudhitha/Documents/ObsidianVault/02_Knowledge/windows-network-pxe-installation.md)
- **Project Roadmap & Spec:** [`01_Projects/network-installer.md`](file:///home/mudhitha/Documents/ObsidianVault/01_Projects/network-installer.md)
- **Session History & Audit Trail:** [`00_Sessions/2026-08-15_windows_network_pxe_installer.md`](file:///home/mudhitha/Documents/ObsidianVault/00_Sessions/2026-08-15_windows_network_pxe_installer.md)

---

<div align="center">
  <sub>Engineered with ❤️ for seamless network OS deployment on Linux.</sub>
</div>
