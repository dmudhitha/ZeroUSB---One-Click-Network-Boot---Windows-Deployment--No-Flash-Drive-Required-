<div align="center">

<img src="assets/icon.png" width="140" height="140" alt="ZeroUSB App Icon" style="border-radius: 28px; box-shadow: 0 10px 30px rgba(0,0,0,0.4);" />

# ⚡ ZeroUSB

### 🚀 *One-Click Network Boot & High-Speed Multi-OS Deployment Engine (No Flash Drive Required)*

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![OS](https://img.shields.io/badge/Platform-Linux%20%7C%20Ubuntu-E95420?style=for-the-badge&logo=ubuntu&logoColor=white)](https://ubuntu.com)
[![PXE](https://img.shields.io/badge/Protocol-iPXE%20%7C%20ProxyDHCP%20%7C%20DirectCable-10B981?style=for-the-badge)](https://ipxe.org)
[![UI](https://img.shields.io/badge/GUI-CustomTkinter-2563EB?style=for-the-badge)](https://customtkinter.tomschimansky.com)
[![Status](https://img.shields.io/badge/Verified-Win7%20%7C%20Win8%20%7C%20Win10%20%7C%20Bodhi%20Linux-success?style=for-the-badge)]()

<br/>

**ZeroUSB** transforms any Linux system into an enterprise-grade, high-speed **PXE Multi-OS Network Deployment Server**. Install **Windows 11, Windows 10, Windows 8/8.1, Windows 7, Windows Server**, or **Linux distributions** directly to bare-metal PCs or Virtual Machines across your local network without USB sticks, optical drives, or Windows Server WDS.

</div>

---

## 📑 Table of Contents
- [🌟 Key Highlights & Innovations](#-key-highlights--innovations)
- [✅ Tested & Verified Operating Systems](#-tested--verified-operating-systems)
- [🌐 Network Topologies (Direct Cable vs Router LAN)](#-network-topologies)
- [🖥️ Graphical Desktop Application (GUI)](#️-graphical-desktop-application-gui)
- [⚡ Quick Start Guide](#-quick-start-guide)
- [🪟 Windows Host Compatibility (WSL2 & Native Roadmap)](#-windows-host-compatibility-wsl2--native-roadmap)
- [🛠️ Interactive WinPE Deployment Menu](#️-interactive-winpe-deployment-menu)
- [💻 Client PC Boot Key Reference](#-client-pc-boot-key-reference)
- [📊 Real-Time Network Telemetry](#-real-time-network-telemetry)
- [📂 Repository Directory Hierarchy](#-repository-directory-hierarchy)
- [🔍 Troubleshooting Matrix](#-troubleshooting-matrix)
- [🧠 Obsidian Knowledge Base Integration](#-obsidian-knowledge-base-integration)

---

## 🌟 Key Highlights & Innovations

- **🚀 Direct Cable Point-to-Point Mode (No Router Needed):** Connect a single Ethernet cable between your Linux machine and the target PC. ZeroUSB provisions an isolated high-speed subnet (`192.168.42.1`) with authoritative DHCP and instant Gigabit wire throughput.
- **🔄 Interactive GUI Boot Menu Priority Reordering:** Visually manage and reorder your boot targets (`[1]`, `[2]`, `[3]`) from the desktop GUI using `▲` and `▼` buttons or `⭐ Make #1`. Slot `#1` automatically becomes the default auto-boot target.
- **🔑 Automatic `ei.cfg` Product Key Bypass:** Auto-injects `ei.cfg` into `\sources\` for all Windows images, completely bypassing the mandatory product key screen in Windows 8 / 8.1 and skipping setup key prompts in Windows 10 and 11.
- **🐧 Instant CIFS Linux Live Mount:** Mounts Linux live filesystems (`casper` / `live`) directly across Samba CIFS at wire speed, booting distros like Bodhi, Ubuntu, and Linux Mint into full desktop environments in seconds.
- **🛡️ Data-Safe Targeted Partition Formatting:** Heuristically detects existing Windows installations across drive letters (`C:` through `H:`) via kernel signature inspection (`ntoskrnl.exe`). Formats **only** the target OS partition, keeping secondary drives, partitions, and personal data 100% safe.
- **⚡ Wire-Speed Direct DISM Apply (~90s Install):** Bypasses standard sluggish setup wizards by applying the install image directly over SMB at raw gigabit network speeds, injecting hardware drivers, and generating system bootloaders automatically.
- **🚫 Permanent Optical Media Check Bypass:** Eliminates the classic Microsoft *"A required CD/DVD drive device driver is missing"* error by streaming payloads directly and passing `/installfrom:Z:\sources\install.wim` bypass flags.
- **🧱 Decoupled Standalone Template Architecture:** Batch scripts are stored in standalone template files (`backend/templates/winpe_startnet.cmd`), guaranteeing zero Python multiline escape sequence conflicts (`\n` line mangling or backslash continuation).
- **🎛️ Dual-Dispatcher WinPE Shell:** Custom `winpeshl.ini` supporting both `[LaunchApp]` and `[LaunchApps]` directives without illegal quotes, guaranteeing client PCs boot straight into the custom deployment menu.
- **🏷️ Architecture & Edition Inspection:** Parses image metadata with `wimlib-imagex info` to clearly label 64-bit (`[64-bit (x64)]`) and 32-bit (`[32-bit (x86)]`) editions in custom selection menus.
- **📈 60 FPS Real-Time Waveform Telemetry:** Live hardware data flow canvas tracking upload (TX), download (RX), peak speeds, and active deployment milestones.

---

## ✅ Tested & Verified Operating Systems

All images listed below have been thoroughly field-tested, staged, and verified for successful network boot and complete installation on bare-metal hardware:

| Operating System | Edition & Architecture | Source / Provenance | Status | Boot Mechanism |
| :--- | :--- | :--- | :---: | :--- |
| **Windows 7** | Professional SP1 (64-bit) | [Massgrave Official Links](https://massgrave.dev/windows_7_links) | 🟢 **PASS** | HTTP Wimboot + CIFS Fast DISM Apply |
| **Windows 8 / 8.1** | Professional (64-bit) | [Massgrave Official Links](https://massgrave.dev/windows_7_links) | 🟢 **PASS** | Auto-injected `ei.cfg` (Product Key Bypassed) |
| **Windows 10** | Professional / Home (64-bit) | [Massgrave Official Links](https://massgrave.dev/windows_7_links) | 🟢 **PASS** | Direct DISM Wire-Speed Apply (~90 seconds) |
| **Bodhi Linux** | Moksha Desktop 7.0 (64-bit) | [Bodhi Linux Official](https://www.bodhilinux.com) | 🟢 **PASS** | Direct CIFS Mount (`netboot=cifs`) + Live Desktop |

> [!TIP]
> **Genuine Untampered ISO Images:** All Windows ISO images tested in this platform were obtained via **[massgrave.dev Windows Links](https://massgrave.dev/windows_7_links)**, which link directly to official Microsoft servers (Digital River / TechBench / MSDN) with verified SHA-1 and SHA-256 cryptographic hashes.

---

## 🌐 Network Topologies

### Topology A: Direct PC-to-PC Gigabit Cable Mode (Fastest & Simplest)
```
┌──────────────────────────────┐                         ┌──────────────────────────────┐
│       THIS PC (Linux)        │                         │      TARGET CLIENT PC        │
│    ZeroUSB Server Host       │ ══════════════════════► │    Blank SSD / Laptop / PC   │
│         192.168.42.1         │   Single Ethernet Cable │                              │
│                              │   Gigabit Link (1 Gbps) │ 1. Press Boot Key (F9/F12)   │
│ • CustomTkinter GUI          │   Streams Bootloader,   │ 2. Select Network Boot       │
│ • Dnsmasq (DHCP + TFTP)      │   WinPE & WIM Payload   │ 3. Installs Windows to SSD   │
│ • High-Speed Samba \\win8    │   at ~110 MB/s          │    in ~90 Seconds            │
└──────────────────────────────┘                         └──────────────────────────────┘
```

### Topology B: Router LAN Mode (ProxyDHCP Coexistence)
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
│    192.168.1.41 (Server)   │ ══════════════════════► │    Bare-Metal PC or VM     │
│                            │   ProxyDHCP on Port 4011│                            │
│ • Serves TFTP & HTTP       │   Coexists safely with  │ • PXE discovers ZeroUSB    │
│ • WinPE streams into RAM   │   existing router pool  │ • WinPE auto-mounts SMB    │
└────────────────────────────┘                         └────────────────────────────┘
```

---

## 🖥️ Graphical Desktop Application (GUI)

Launch the desktop management console with a single command:

```bash
python3 /home/mudhitha/System/Network-Installer/app.py
```
*Or execute the launcher wrapper:*
```bash
bash /home/mudhitha/System/Network-Installer/run-gui.sh
```

```text
┌─────────────────────────────────────────────────────────────────────────────────┐
│ ⚡ ZeroUSB - Multi-OS Network Deployment Platform                ● SERVING PXE  │
├─────────────────────────────────────────────────────────────────────────────────┤
│ [🎛️ Control Center & Telemetry]  [💿 OS Profiles]  [📦 Dependencies]  [📜 Logs] │
├─────────────────────────────────────────────────────────────────────────────────┤
│ 📊 Real-Time Network Data Flow & Throughput                                     │
│  TX: 104.2 MB/s | RX: 420 KB/s | Peak: 112.5 MB/s | Total: 4.8 GB              │
│                                                                                 │
│   120 MB/s ┼                     ╭────────╮                                     │
│    80 MB/s ┼                  ╭──╯        ╰────────╮                            │
│    40 MB/s ┼        ╭─────────╯                    ╰──────                      │
│     0 KB/s ┴────────┴─────────────────────────────────────┴                     │
│              60s ago                  30s ago                Now                │
├─────────────────────────────────────────────────────────────────────────────────┤
│ Active Profiles: [Windows 8 x64]  [Windows 10 x64]  [Windows 11]  [Linux Mint]  │
│ Pipeline: [1. DHCP/TFTP] ➔ [2. HTTP Wimboot] ➔ [3. WinPE RAM] ➔ [4. SMB DISM]   │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## ⚡ Quick Start Guide

### 1. Install System Dependencies & Bootloaders
Open the GUI and navigate to **📦 Dependencies & Tools**, then click **"📥 Install & Download All Dependencies"**.  
*CLI Alternative:*
```bash
bash scripts/install-prereqs.sh
```

### 2. Stage Windows or Linux ISO Images
1. Navigate to the **💿 OS Profiles & Extraction** tab.
2. Select your OS preset (e.g., *Windows 10*, *Windows 8*, *Windows 11*).
3. Browse and select your ISO file.
4. Click **"⚡ Extract & Prepare OS Profile"**. ZeroUSB automatically extracts setup media, builds editions catalogs, and injects custom WinPE bootloader hooks into `boot.wim`.

### 3. Launch Services
1. Go to the **🎛️ Control Center** tab.
2. Choose your network interface (e.g., `eth0` / `enp3s0`).
3. Click **"🚀 Start Network Deployment Server"**. The indicator badge turns **Green** (`● SERVING PXE`).

---

## 🪟 Windows Host Compatibility (WSL2 & Native Roadmap)

While ZeroUSB is engineered primarily on Linux for high-speed Samba and raw low-level network daemon control, it can also be hosted from a **Windows 10 / 11 PC**:

### A. Running on Windows Today (via WSL2 + Mirrored Networking)
You can run ZeroUSB on a Windows host using **Windows Subsystem for Linux (WSL2)**:

1. **Install Ubuntu on WSL**:
   ```powershell
   wsl --install -d Ubuntu
   ```
2. **Enable Mirrored Networking** (Required for DHCP/PXE broadcasts to bridge to physical Ethernet):
   Create or edit `C:\Users\<YourUsername>\.wslconfig`:
   ```ini
   [wsl2]
   networkingMode=mirrored
   ```
3. **Launch ZeroUSB in WSL**:
   Inside Ubuntu WSL, clone the repo and run:
   ```bash
   bash scripts/install-prereqs.sh
   python3 app.py
   ```
   *Thanks to WSLg, the full desktop application window renders directly on your Windows desktop.*

---

### B. Native Windows Application Roadmap (`ZeroUSB.exe`)
ZeroUSB's architecture is modular and designed for straightforward native porting to Windows without requiring WSL or Linux:

| Layer | Linux Implementation | Native Windows Architecture |
| :--- | :--- | :--- |
| **GUI Framework** | Python + CustomTkinter | **Identical** (100% cross-platform out-of-the-box) |
| **HTTP Boot Server** | Pure Python HTTP daemon | **Identical** (`scripts/http_server.py`) |
| **File Sharing (CIFS)** | Linux `smbd` daemon | **Built into Windows Kernel** (`net share win10=... /grant:everyone,full`) |
| **ISO / WIM Extraction** | `7z` & `wimlib-imagex` | Bundled Windows binaries (`7z.exe`, `wimlib-imagex.exe`) |
| **DHCP / TFTP Server** | `dnsmasq` | Portable `Tftpd64.exe` (CLI) or pure-Python DHCP/TFTP engine |

---

## 🛠️ Interactive WinPE Deployment Menu

When the client boots over the network, WinPE initializes hardware, establishes network leases, mounts `Z:\`, and displays the high-contrast ASCII deployment console:

```text
=================================================================
  ZeroUSB Multi-OS Fast Network Installer
  Target:      Windows 10 (64-bit)
  Server:      \\192.168.42.1\win10
  Image File:  Z:\sources\install.wim
=================================================================

  [1] Full Clean Install          - Wipes Disk 0 (Fresh Drive)
  [2] Format C: and Install OS    - Keeps Other Drives and Data Safe
  [3] Graphical Setup             - Launches Standard Windows Setup Wizard
  [4] Custom Edition              - Select Edition (Pro / Home / Enterprise)
  [5] Command Prompt              - Manual Diskpart and Diagnostic Tools
  [6] Reboot Computer

=================================================================
Enter your choice (1-6) [Default=2]: 
```

### Menu Options Explained:
- **`[1] Full Clean Install`**: Automatically partitions and formats the entire Disk 0 (MBR/NTFS), creates a bootable primary drive, and applies the OS. Ideal for brand new SSDs.
- **`[2] Format C: and Install OS (Recommended)`**: Heuristically locates the existing Windows partition (`\Windows\System32\ntoskrnl.exe`), confirms drive selection, formats **only** that partition, and preserves all other drive volumes and personal files.
- **`[3] Graphical Setup`**: Launches the familiar Microsoft Windows Setup Wizard (`Z:\sources\setup.exe /installfrom:...`) with network bypasses pre-configured.
- **`[4] Custom Edition`**: Displays all detected editions in the WIM image with architecture tags (`[64-bit (x64)]` vs `[32-bit (x86)]`) and allows custom index deployment.
- **`[5] Command Prompt`**: Drops to interactive WinPE CLI for diskpart, driver diagnostics, or network inspection.
- **`[6] Reboot Computer`**: Reboots client via `wpeutil reboot`.

---

## 💻 Client PC Boot Key Reference

Connect an Ethernet cable to the target PC, power on, and immediately tap the manufacturer boot menu key:

| Manufacturer | Boot Menu Key | BIOS Setup Key | Special OEM Notes |
| :--- | :--- | :--- | :--- |
| **HP / Compaq** | **`F9`** | **`F10`** | Must enable *Internal Network Adapter Boot* in BIOS (`F10` ➔ System Configuration ➔ Device Configurations). |
| **Dell / Alienware** | **`F12`** | **`F2`** | Select *UEFI: Network Boot* or *IPv4 PXE*. |
| **Lenovo / ThinkPad** | **`F12`** or **`Enter`** | **`F1`** | Select *PCI LAN* or *Network Boot*. |
| **ASUS** | **`F8`** or **`Esc`** | **`Del`** / **`F2`** | Enable PXE Network Stack in Advanced Settings. |
| **Acer** | **`F12`** | **`F2`** | Enable *F12 Boot Menu* in BIOS first. |
| **MSI** | **`F11`** | **`Del`** | Select *Realtek PXE* or *UEFI Network*. |

---

## 📊 Real-Time Network Telemetry

The desktop application includes a dedicated 60 FPS hardware telemetry canvas:
- **Emerald Waveform (`#10b981`):** Real-time server TX bandwidth (streaming WIM/ESD images at Gigabit speeds).
- **Sky Blue Line (`#38bdf8`):** Client RX traffic acknowledgments and SMB negotiation packets.
- **Auto-Scaling Dynamics:** Automatically switches units across `KB/s`, `MB/s`, and `GB/s`.
- **Milestone Highlighting:** Visual indicators activate as stages occur (`ProxyDHCP` ➔ `TFTP` ➔ `HTTP` ➔ `Samba`).

---

## 📂 Repository Directory Hierarchy

```text
/home/mudhitha/System/Network-Installer/
├── app.py                      # 🎛️ Modern CustomTkinter Graphical Management Suite
├── run-gui.sh                  # 🚀 Desktop GUI launch wrapper (X11 / Wayland)
├── ui/
│   ├── theme.py                # 🎨 UI styling tokens, dark mode palette, and typography
│   └── network_chart.py        # 📊 60 FPS rolling canvas network throughput graph
├── backend/
│   ├── detector.py             # 🔍 Hardware NIC discovery & dependency validation
│   ├── network_monitor.py      # 📈 Live bandwidth telemetry engine (psutil)
│   ├── server_manager.py       # 🚀 Multi-service supervisor (Dnsmasq, HTTP, Samba)
│   ├── os_manager.py           # 💿 Multi-OS profile manager & dynamic iPXE builder
│   └── templates/
│       └── winpe_startnet.cmd  # 🧱 Decoupled standalone WinPE DOS batch template
├── config/
│   ├── dnsmasq.conf            # ⚙️ Dual-mode DHCP / ProxyDHCP & TFTP configuration
│   ├── smb.conf                # ⚙️ High-throughput guest-accessible SMB share configuration
│   └── boot.ipxe               # ⚙️ Real-time generated dynamic iPXE boot menu
├── srv/
│   ├── tftp/                   # 📁 TFTP root serving ipxe.efi and undionly.kpxe
│   ├── http/boot/              # 📁 HTTP root serving wimboot, BCD, and boot.wim
│   └── samba/                  # 📁 Multi-OS SMB root (e.g. srv/samba/win10, srv/samba/win8)
├── scripts/
│   ├── install-prereqs.sh      # 📥 Installs packages & fetches bootloaders
│   ├── start-server.sh         # 🚀 CLI server starter
│   ├── stop-server.sh          # 🛑 CLI server stopper
│   └── test-server.sh          # 🩺 14-point pre-flight diagnostic suite
└── README.md                   # 📖 Complete Documentation
```

---

## 🔍 Troubleshooting Matrix

| Issue | Root Cause | Solution |
| :--- | :--- | :--- |
| **`Windows 8 / 8.1 Demands Product Key (No Skip Button)`** | Windows 8 installer disables the "Skip" button by default in `setup.exe`. | ZeroUSB automatically injects `ei.cfg` to restore edition selection and skip the prompt. Alternatively, choose Option `[1]` or `[2]` (Direct DISM Install) to bypass setup wizards entirely. |
| **`USB Keyboard Unresponsive at Boot Menu`** | Legacy 16-bit BIOS drops USB scan-codes on modern USB 3.0 / xHCI ports. | 1. Switch client PC from *Legacy/CSM* to *UEFI Network Boot* in BIOS (`ipxe.efi` native 64-bit USB HID drivers).<br>2. Plug into a Black USB 2.0 port.<br>3. In the ZeroUSB GUI, move your desired OS to **Slot #1** to auto-boot without touching any keys! |
| **`A required CD/DVD drive device driver is missing`** | Standard Microsoft `setup.exe` checking for physical optical bus media. | Choose Option `[2]` or `[1]` for direct DISM wire-speed apply, or launch setup with `/installfrom:Z:\sources\install.wim`. |
| **`PXE-E53: No boot filename received`** | Target PC did not receive DHCP response or firewall blocked UDP ports. | Run `sudo ufw allow 67/udp && sudo ufw allow 4011/udp && sudo ufw allow 69/udp` and confirm cable connection. |
| **`Screen drops to X:\windows\system32> prompt`** | WinPE shell did not automatically execute `startnet.cmd`. | Fixed permanently with dual `[LaunchApp]` and `[LaunchApps]` directives in `winpeshl.ini`. Type `startnet` to launch manually. |
| **`'Data' is not recognized as an internal command`** | Unescaped ampersand (`&`) in Windows command prompt batch scripts. | Replaced `&` with the word `and` across all menu strings and scripts. |
| **`'findstr' is not recognized as an internal command`** | Minimal OEM WinPE images omit `findstr.exe`. | Replaced pipelined filters with direct `ipconfig` execution. |
| **`The syntax of the command is incorrect`** | Python string escaping converted `\ntoskrnl.exe` into a newline character. | Decoupled script into standalone disk template (`backend/templates/winpe_startnet.cmd`). |
| **`Client PC ignores Network Boot Key`** | OEM BIOS has network boot disabled by default (notably HP/Compaq). | Enter BIOS setup (`F10` or `F2`), enable *Internal Network Adapter Boot*, and select via `F9`. |

---

## 🧠 Obsidian Knowledge Base Integration

This project is continuously maintained and documented within the Obsidian Second Brain vault:

- **📘 Comprehensive Knowledge Guide:** [`02_Knowledge/windows-network-pxe-installation.md`](file:///home/mudhitha/Documents/ObsidianVault/02_Knowledge/windows-network-pxe-installation.md)
- **🗺️ Project Roadmap & Specs:** [`01_Projects/network-installer.md`](file:///home/mudhitha/Documents/ObsidianVault/01_Projects/network-installer.md)
- **📝 Optimization Session Log:** [`00_Sessions/2026-08-16_zero_usb_direct_pxe_deployment_and_optimization.md`](file:///home/mudhitha/Documents/ObsidianVault/00_Sessions/2026-08-16_zero_usb_direct_pxe_deployment_and_optimization.md)
- **📅 Daily Audit Log:** [`00_Daily/2026-08-28.md`](file:///home/mudhitha/Documents/ObsidianVault/00_Daily/2026-08-28.md)

---

<div align="center">
  <sub>Engineered with ❤️ for seamless, lightning-fast bare-metal OS deployments from Linux.</sub>
</div>
