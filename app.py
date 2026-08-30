#!/usr/bin/env python3
"""
==============================================================================
 ZeroUSB - Desktop GUI (Multi-OS Network Deployer)
 High-Performance One-Click Network Boot Server for Multiple Windows & Linux OSs
 With Real-Time Network Data Flow Graph, Multi-OS Staging, and Dynamic Removal
==============================================================================
"""

import os
import sys
import time
import shutil
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
import customtkinter as ctk

# Ensure script directory is in Python path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from ui.theme import THEME, FONTS
from ui.network_chart import NetworkTrafficChart
from backend.detector import get_network_interfaces, check_dependencies, check_staged_assets
from backend.server_manager import ServerManager
from backend.installer import DependencyInstaller
from backend.network_monitor import NetworkMonitor
from backend.os_manager import OSManager, OS_PRESETS, OS_CATEGORIES, get_presets_by_category, TYPE_CATEGORY_MAP, detect_os_from_iso

# Configure CustomTkinter Appearance
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class NetworkInstallerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.base_dir = BASE_DIR
        self.server_manager = ServerManager(self.base_dir)
        self.os_manager = OSManager(self.base_dir)
        self.dep_installer = DependencyInstaller(self.base_dir)
        self.network_monitor = NetworkMonitor(interface="enp3s0")

        # Window Configuration
        self.title("ZeroUSB - Multi-OS Network Deployer")
        self.geometry("1080x860")
        self.minsize(960, 740)
        self.configure(fg_color=THEME["bg_dark"])

        # Maximize Window on Startup
        try:
            self.after(50, self._maximize_window)
        except Exception:
            pass

        # Window Icon
        icon_path = self.base_dir / "assets" / "icon.png"
        if icon_path.exists():
            try:
                from PIL import ImageTk, Image
                self._app_icon_img = ImageTk.PhotoImage(Image.open(icon_path))
                self.wm_iconphoto(True, self._app_icon_img)
            except Exception:
                pass

        # State Variables
        self.interfaces_list = []
        self.selected_interface_var = ctk.StringVar()
        self.selected_ip_var = ctk.StringVar(value="192.168.1.41")
        self.http_port_var = ctk.StringVar(value="8080")
        self.dhcp_mode_var = ctk.StringVar(value="Standalone DHCP (Direct PC Cable)")
        self.boot_target_mode_var = ctk.StringVar(value="⚡ Dual Mode (Auto-Detect CSM & UEFI)")
        self.default_os_var = ctk.StringVar(value="Loading...")
        self.boot_timeout_var = ctk.StringVar(value="⏱️ 10 Seconds (Default)")
        self.iso_path_var = ctk.StringVar()
        self.selected_category_var = ctk.StringVar(value="All Systems")
        self.selected_preset_var = ctk.StringVar(value="Windows 10 (64-bit)")
        self.selected_remove_os_var = ctk.StringVar()

        # Build UI
        self._create_header()
        self._create_tabs()
        self._create_status_bar()

        # Start Network Telemetry Monitor
        self.network_monitor.start()

        # Initial Refresh
        self.refresh_network_interfaces()
        self.refresh_dependencies_view()
        self.refresh_installed_os_view()

        # Periodic health check & telemetry loop
        self.after(500, self._periodic_health_check)

    # --------------------------------------------------------------------------
    # UI Creation
    # --------------------------------------------------------------------------
    def _create_header(self):
        header_frame = ctk.CTkFrame(self, fg_color=THEME["surface"], corner_radius=0, height=70)
        header_frame.pack(fill="x", padx=0, pady=0)
        header_frame.pack_propagate(False)

        title_box = ctk.CTkFrame(header_frame, fg_color="transparent")
        title_box.pack(side="left", padx=20, pady=12)

        title_lbl = ctk.CTkLabel(
            title_box,
            text="⚡ ZeroUSB",
            font=ctk.CTkFont(family="Inter", size=20, weight="bold"),
            text_color=THEME["text_primary"]
        )
        title_lbl.pack(anchor="w")

        subtitle_lbl = ctk.CTkLabel(
            title_box,
            text="One-Click Multi-OS Network Deployment (Windows 10/11 & Linux) — No Flash Drives Required",
            font=ctk.CTkFont(family="Inter", size=11),
            text_color=THEME["text_muted"]
        )
        subtitle_lbl.pack(anchor="w")

        # Global Server Status Badge
        self.server_status_badge = ctk.CTkLabel(
            header_frame,
            text="● OFFLINE",
            font=ctk.CTkFont(family="Inter", size=12, weight="bold"),
            text_color=THEME["text_muted"],
            fg_color=THEME["card_border"],
            corner_radius=12,
            padx=14,
            pady=6
        )
        self.server_status_badge.pack(side="right", padx=20, pady=15)

    def _create_tabs(self):
        self.tabview = ctk.CTkTabview(
            self,
            fg_color=THEME["bg_dark"],
            segmented_button_fg_color=THEME["surface"],
            segmented_button_selected_color=THEME["primary"],
            segmented_button_selected_hover_color=THEME["primary_hover"],
            segmented_button_unselected_hover_color=THEME["card_hover"],
            text_color=THEME["text_primary"],
            corner_radius=10
        )
        self.tabview.pack(fill="both", expand=True, padx=16, pady=10)

        self.tab_dashboard = self.tabview.add("🎛️ Control Center & Telemetry")
        self.tab_os_manager = self.tabview.add("💿 Multi-OS Manager")
        self.tab_deps = self.tabview.add("📦 Dependencies & Tools")
        self.tab_logs = self.tabview.add("📜 Live Console")

        self._build_dashboard_tab()
        self._build_multi_os_tab()
        self._build_deps_tab()
        self._build_logs_tab()

    def _maximize_window(self):
        try:
            # Native Linux X11 window maximization
            self.attributes('-zoomed', True)
        except Exception:
            try:
                # Windows / platform fallback
                self.state('zoomed')
            except Exception:
                try:
                    w = self.winfo_screenwidth()
                    h = self.winfo_screenheight()
                    self.geometry(f"{w}x{h}+0+0")
                except Exception:
                    pass

    # --------------------------------------------------------------------------
    # Tab 1: Control Center & Real-Time Telemetry Dashboard
    # --------------------------------------------------------------------------
    def _build_dashboard_tab(self):
        tab = self.tab_dashboard

        # Full-height scrollable container for Dashboard tab
        self.dashboard_scroll = ctk.CTkScrollableFrame(
            tab,
            fg_color="transparent",
            scrollbar_button_color=THEME["card_border"],
            scrollbar_button_hover_color=THEME["primary"]
        )
        self.dashboard_scroll.pack(fill="both", expand=True, padx=2, pady=2)

        # Top Section: Two Column Control & Info Cards
        top_container = ctk.CTkFrame(self.dashboard_scroll, fg_color="transparent")
        top_container.pack(fill="x", padx=4, pady=(2, 6))
        top_container.grid_columnconfigure(0, weight=5)
        top_container.grid_columnconfigure(1, weight=5)

        # Left Column: Configuration & Controls
        left_card = ctk.CTkFrame(top_container, fg_color=THEME["card_bg"], corner_radius=10, border_width=1, border_color=THEME["card_border"])
        left_card.grid(row=0, column=0, sticky="nsew", padx=6, pady=4)

        ctk.CTkLabel(
            left_card,
            text="Server Configuration",
            font=ctk.CTkFont(family="Inter", size=14, weight="bold"),
            text_color=THEME["text_primary"]
        ).pack(anchor="w", padx=16, pady=(12, 4))

        # Interface Selector Row
        iface_row = ctk.CTkFrame(left_card, fg_color="transparent")
        iface_row.pack(fill="x", padx=16, pady=(0, 6))

        self.iface_menu = ctk.CTkOptionMenu(
            iface_row,
            variable=self.selected_interface_var,
            values=["Detecting..."],
            command=self._on_interface_selected,
            fg_color=THEME["surface"],
            button_color=THEME["primary"],
            button_hover_color=THEME["primary_hover"],
            dynamic_resizing=False,
            height=32
        )
        self.iface_menu.pack(side="left", fill="x", expand=True)

        refresh_btn = ctk.CTkButton(
            iface_row,
            text="🔄",
            width=34,
            height=32,
            fg_color=THEME["surface"],
            hover_color=THEME["card_hover"],
            command=self.refresh_network_interfaces
        )
        refresh_btn.pack(side="right", padx=(6, 0))

        # DHCP Mode Selector Row
        dhcp_mode_row = ctk.CTkFrame(left_card, fg_color="transparent")
        dhcp_mode_row.pack(fill="x", padx=16, pady=(0, 6))

        ctk.CTkLabel(dhcp_mode_row, text="DHCP:", font=ctk.CTkFont(family="Inter", size=11), text_color=THEME["text_secondary"]).pack(side="left", padx=(0, 6))

        self.dhcp_mode_menu = ctk.CTkOptionMenu(
            dhcp_mode_row,
            variable=self.dhcp_mode_var,
            values=[
                "ProxyDHCP (Connected to Router)",
                "Standalone DHCP (Direct PC Cable)"
            ],
            fg_color=THEME["surface"],
            button_color=THEME["card_border"],
            button_hover_color=THEME["card_hover"],
            dynamic_resizing=False,
            height=30
        )
        self.dhcp_mode_menu.pack(side="left", fill="x", expand=True)

        # Boot Target Mode Selector Row (CSM vs UEFI)
        boot_mode_row = ctk.CTkFrame(left_card, fg_color="transparent")
        boot_mode_row.pack(fill="x", padx=16, pady=(0, 6))

        ctk.CTkLabel(boot_mode_row, text="Target:", font=ctk.CTkFont(family="Inter", size=11), text_color=THEME["text_secondary"]).pack(side="left", padx=(0, 6))

        self.boot_mode_menu = ctk.CTkOptionMenu(
            boot_mode_row,
            variable=self.boot_target_mode_var,
            values=[
                "⚡ Dual Mode (Auto-Detect CSM & UEFI)",
                "🛡️ Pure CSM / Legacy BIOS Mode",
                "🚀 Pure Native UEFI 64-bit Mode"
            ],
            command=self._on_boot_mode_changed,
            fg_color=THEME["surface"],
            button_color=THEME["card_border"],
            button_hover_color=THEME["card_hover"],
            dynamic_resizing=False,
            height=30
        )
        self.boot_mode_menu.pack(side="left", fill="x", expand=True)

        # Default Boot OS Selector Row
        default_os_row = ctk.CTkFrame(left_card, fg_color="transparent")
        default_os_row.pack(fill="x", padx=16, pady=(0, 4))

        ctk.CTkLabel(
            default_os_row,
            text="Default OS:",
            font=ctk.CTkFont(family="Inter", size=11, weight="bold"),
            text_color=THEME["text_primary"]
        ).pack(side="left", padx=(0, 6))

        self.default_os_menu = ctk.CTkOptionMenu(
            default_os_row,
            variable=self.default_os_var,
            values=["No OS installed"],
            command=self._on_default_os_menu_selected,
            fg_color=THEME["surface"],
            button_color=THEME["card_border"],
            button_hover_color=THEME["card_hover"],
            dynamic_resizing=False,
            height=30
        )
        self.default_os_menu.pack(side="left", fill="x", expand=True)

        # Auto-Boot Countdown Timer Row
        timeout_row = ctk.CTkFrame(left_card, fg_color="transparent")
        timeout_row.pack(fill="x", padx=16, pady=(0, 8))

        ctk.CTkLabel(
            timeout_row,
            text="Auto-Boot:",
            font=ctk.CTkFont(family="Inter", size=11, weight="bold"),
            text_color=THEME["text_primary"]
        ).pack(side="left", padx=(0, 6))

        self.timeout_menu = ctk.CTkOptionMenu(
            timeout_row,
            variable=self.boot_timeout_var,
            values=[
                "⚡ Instant Boot (0s - No Keyboard Needed)",
                "⏱️ 3 Seconds",
                "⏱️ 5 Seconds",
                "⏱️ 10 Seconds (Default)",
                "⏱️ 15 Seconds",
                "⏱️ 30 Seconds",
                "🛑 Wait Forever (No Timer)"
            ],
            command=self._on_timeout_menu_selected,
            fg_color=THEME["surface"],
            button_color=THEME["card_border"],
            button_hover_color=THEME["card_hover"],
            dynamic_resizing=False,
            height=30
        )
        self.timeout_menu.pack(side="left", fill="x", expand=True)

        # Live Service Health Sub-Card
        services_box = ctk.CTkFrame(left_card, fg_color=THEME["surface"], corner_radius=8, border_width=1, border_color=THEME["card_border"])
        services_box.pack(fill="x", padx=16, pady=(0, 10))

        self.lbl_status_tftp = self._create_service_indicator(services_box, "TFTP & ProxyDHCP (dnsmasq)")
        self.lbl_status_http = self._create_service_indicator(services_box, "Fast HTTP Streamer (Port 8080)")
        self.lbl_status_samba = self._create_service_indicator(services_box, "Samba Multi-OS Shares")

        # Giant Start/Stop Button
        self.btn_toggle_server = ctk.CTkButton(
            left_card,
            text="🚀 Start PXE Network Server",
            font=ctk.CTkFont(family="Inter", size=13, weight="bold"),
            fg_color=THEME["success"],
            hover_color="#059669",
            height=38,
            command=self._toggle_server
        )
        self.btn_toggle_server.pack(fill="x", padx=16, pady=(0, 12))

        # Right Column: Client Instructions & Staged OS Summary
        right_card = ctk.CTkFrame(top_container, fg_color=THEME["card_bg"], corner_radius=10, border_width=1, border_color=THEME["card_border"])
        right_card.grid(row=0, column=1, sticky="nsew", padx=6, pady=4)

        ctk.CTkLabel(
            right_card,
            text="Multi-OS Client Boot Guide",
            font=ctk.CTkFont(family="Inter", size=14, weight="bold"),
            text_color=THEME["text_primary"]
        ).pack(anchor="w", padx=16, pady=(12, 4))

        guide_text = (
            "1. Connect target PC to Ethernet switch/router.\n"
            "2. Turn on PC & press Boot Menu key (F12, F11, F8).\n"
            "3. Select 'UEFI Network Boot' / 'PXE IPv4'.\n"
            "4. The ZeroUSB menu appears -> Select your OS to install!"
        )
        ctk.CTkLabel(
            right_card,
            text=guide_text,
            font=ctk.CTkFont(family="Inter", size=11),
            text_color=THEME["text_secondary"],
            justify="left"
        ).pack(anchor="w", padx=16, pady=(0, 8))

        # Quick Actions & Tools Toolbar
        tools_row = ctk.CTkFrame(right_card, fg_color="transparent")
        tools_row.pack(fill="x", padx=16, pady=(0, 8))

        btn_sniff = ctk.CTkButton(
            tools_row,
            text="📡 Live Packet Sniffer",
            font=ctk.CTkFont(family="Inter", size=11, weight="bold"),
            fg_color=THEME["surface"],
            hover_color=THEME["card_hover"],
            height=30,
            command=self._launch_packet_sniffer
        )
        btn_sniff.pack(side="left", fill="x", expand=True, padx=(0, 4))

        btn_shares = ctk.CTkButton(
            tools_row,
            text="📂 Open Server Folder",
            font=ctk.CTkFont(family="Inter", size=11),
            fg_color=THEME["surface"],
            hover_color=THEME["card_hover"],
            height=30,
            command=self._open_boot_folder
        )
        btn_shares.pack(side="right", fill="x", expand=True, padx=(4, 0))

        # Staged Operating Systems Box
        self.dashboard_os_box = ctk.CTkFrame(right_card, fg_color=THEME["surface"], corner_radius=8, border_width=1, border_color=THEME["card_border"])
        self.dashboard_os_box.pack(fill="both", expand=True, padx=16, pady=(0, 12))

        # Bottom Section: Real-Time Network Data Flow Graph Widget
        self.network_chart = NetworkTrafficChart(self.dashboard_scroll)
        self.network_chart.pack(fill="x", expand=False, padx=8, pady=(4, 16))

    def _create_service_indicator(self, parent, name: str):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=10, pady=2)

        name_lbl = ctk.CTkLabel(row, text=name, font=ctk.CTkFont(family="Inter", size=10), text_color=THEME["text_secondary"])
        name_lbl.pack(side="left")

        val_lbl = ctk.CTkLabel(row, text="● Checking", font=ctk.CTkFont(family="Inter", size=10, weight="bold"), text_color=THEME["text_muted"])
        val_lbl.pack(side="right")
        return val_lbl

    # --------------------------------------------------------------------------
    # Tab 2: Multi-OS Manager (Add, List & Remove Operating Systems)
    # --------------------------------------------------------------------------
    def _build_multi_os_tab(self):
        tab = self.tab_os_manager

        # Scrollable container for multi-OS cards
        container = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=4, pady=4)

        # Card 1: Add New OS
        card_add = ctk.CTkFrame(container, fg_color=THEME["card_bg"], corner_radius=10, border_width=1, border_color=THEME["card_border"])
        card_add.pack(fill="x", padx=12, pady=(4, 10))

        ctk.CTkLabel(
            card_add,
            text="➕ Stage & Add New Operating System",
            font=ctk.CTkFont(family="Inter", size=15, weight="bold"),
            text_color=THEME["text_primary"]
        ).pack(anchor="w", padx=20, pady=(16, 4))

        ctk.CTkLabel(
            card_add,
            text="Select an OS profile and provide an ISO file. ZeroUSB will extract the files, patch auto-mount scripts, and add it to your network boot menu.",
            font=ctk.CTkFont(family="Inter", size=11),
            text_color=THEME["text_secondary"],
            justify="left"
        ).pack(anchor="w", padx=20, pady=(0, 12))

        # Preset Dropdown & ISO Picker
        preset_row = ctk.CTkFrame(card_add, fg_color="transparent")
        preset_row.pack(fill="x", padx=20, pady=(0, 10))

        # Category Selector Dropdown
        ctk.CTkLabel(preset_row, text="Category:", font=ctk.CTkFont(family="Inter", size=12, weight="bold"), text_color=THEME["text_secondary"]).pack(side="left", padx=(0, 6))

        self.category_menu = ctk.CTkOptionMenu(
            preset_row,
            variable=self.selected_category_var,
            values=OS_CATEGORIES,
            command=self._on_category_changed,
            fg_color=THEME["surface"],
            button_color=THEME["primary"],
            button_hover_color=THEME["primary_hover"],
            height=34,
            width=135
        )
        self.category_menu.pack(side="left", padx=(0, 14))

        # Target Profile Selector Dropdown
        ctk.CTkLabel(preset_row, text="Target OS Profile:", font=ctk.CTkFont(family="Inter", size=12), text_color=THEME["text_secondary"]).pack(side="left", padx=(0, 6))

        preset_names = [p["name"] for p in OS_PRESETS]
        self.preset_menu = ctk.CTkOptionMenu(
            preset_row,
            variable=self.selected_preset_var,
            values=preset_names,
            fg_color=THEME["surface"],
            button_color=THEME["primary"],
            button_hover_color=THEME["primary_hover"],
            height=34,
            width=280
        )
        self.preset_menu.pack(side="left", fill="x", expand=True)

        # ISO Path Row
        iso_row = ctk.CTkFrame(card_add, fg_color="transparent")
        iso_row.pack(fill="x", padx=20, pady=(0, 12))

        self.entry_iso = ctk.CTkEntry(
            iso_row,
            textvariable=self.iso_path_var,
            placeholder_text="/path/to/Windows_or_Linux.iso",
            height=36,
            fg_color=THEME["surface"],
            border_color=THEME["card_border"]
        )
        self.entry_iso.pack(side="left", fill="x", expand=True, padx=(0, 8))

        browse_btn = ctk.CTkButton(
            iso_row,
            text="Browse ISO...",
            width=120,
            height=36,
            fg_color=THEME["primary"],
            hover_color=THEME["primary_hover"],
            command=self._browse_iso
        )
        browse_btn.pack(side="right")

        # Extract Button & Progress
        action_row = ctk.CTkFrame(card_add, fg_color="transparent")
        action_row.pack(fill="x", padx=20, pady=(0, 10))

        self.btn_extract_os = ctk.CTkButton(
            action_row,
            text="⚡ Extract & Add to Multi-Boot Menu",
            font=ctk.CTkFont(family="Inter", size=13, weight="bold"),
            fg_color=THEME["accent"],
            hover_color="#0369a1",
            height=38,
            command=self._start_os_extraction
        )
        self.btn_extract_os.pack(side="left", padx=(0, 12))

        self.lbl_os_step = ctk.CTkLabel(action_row, text="Ready", font=ctk.CTkFont(family="Inter", size=12), text_color=THEME["text_muted"])
        self.lbl_os_step.pack(side="left")

        self.progress_os = ctk.CTkProgressBar(card_add, fg_color=THEME["surface"], progress_color=THEME["primary"], height=8)
        self.progress_os.pack(fill="x", padx=20, pady=(0, 16))
        self.progress_os.set(0.0)

        # Card 2: Currently Staged Operating Systems
        self.card_staged = ctk.CTkFrame(container, fg_color=THEME["card_bg"], corner_radius=10, border_width=1, border_color=THEME["card_border"])
        self.card_staged.pack(fill="x", padx=12, pady=(0, 10))

        ctk.CTkLabel(
            self.card_staged,
            text="📋 Active Operating Systems in Network Boot Menu",
            font=ctk.CTkFont(family="Inter", size=15, weight="bold"),
            text_color=THEME["text_primary"]
        ).pack(anchor="w", padx=20, pady=(16, 8))

        self.os_list_container = ctk.CTkFrame(self.card_staged, fg_color=THEME["surface"], corner_radius=8, border_width=1, border_color=THEME["card_border"])
        self.os_list_container.pack(fill="x", padx=20, pady=(0, 14))

        # Card 3: Remove Operating System Control
        card_remove = ctk.CTkFrame(container, fg_color=THEME["card_bg"], corner_radius=10, border_width=1, border_color=THEME["card_border"])
        card_remove.pack(fill="x", padx=12, pady=(0, 14))

        ctk.CTkLabel(
            card_remove,
            text="🗑️ Remove / Uninstall Operating System",
            font=ctk.CTkFont(family="Inter", size=15, weight="bold"),
            text_color=THEME["text_primary"]
        ).pack(anchor="w", padx=20, pady=(16, 4))

        ctk.CTkLabel(
            card_remove,
            text="Select an OS from the dropdown below to delete its files, free up disk space, and remove it from the client boot menu.",
            font=ctk.CTkFont(family="Inter", size=11),
            text_color=THEME["text_secondary"]
        ).pack(anchor="w", padx=20, pady=(0, 12))

        remove_row = ctk.CTkFrame(card_remove, fg_color="transparent")
        remove_row.pack(fill="x", padx=20, pady=(0, 18))

        ctk.CTkLabel(remove_row, text="Select OS to Remove:", font=ctk.CTkFont(family="Inter", size=12), text_color=THEME["text_secondary"]).pack(side="left", padx=(0, 8))

        self.remove_os_menu = ctk.CTkOptionMenu(
            remove_row,
            variable=self.selected_remove_os_var,
            values=["No OS installed"],
            fg_color=THEME["surface"],
            button_color=THEME["card_border"],
            button_hover_color=THEME["card_hover"],
            height=36,
            width=320
        )
        self.remove_os_menu.pack(side="left", padx=(0, 12))

        self.btn_remove_os = ctk.CTkButton(
            remove_row,
            text="🗑️ Remove Selected OS",
            font=ctk.CTkFont(family="Inter", size=13, weight="bold"),
            fg_color=THEME["danger"],
            hover_color="#dc2626",
            height=36,
            command=self._remove_selected_os
        )
        self.btn_remove_os.pack(side="left")

    # --------------------------------------------------------------------------
    # Tab 3: Dependencies & Tools
    # --------------------------------------------------------------------------
    def _build_deps_tab(self):
        tab = self.tab_deps

        card = ctk.CTkFrame(tab, fg_color=THEME["card_bg"], corner_radius=10, border_width=1, border_color=THEME["card_border"])
        card.pack(fill="both", expand=True, padx=12, pady=12)

        ctk.CTkLabel(
            card,
            text="System Dependencies & Bootloader Binaries",
            font=ctk.CTkFont(family="Inter", size=16, weight="bold"),
            text_color=THEME["text_primary"]
        ).pack(anchor="w", padx=20, pady=(18, 6))

        desc = "ZeroUSB relies on lightweight native system tools (dnsmasq, samba, wimtools, 7zip, ipxe) and wimboot."
        ctk.CTkLabel(card, text=desc, font=ctk.CTkFont(family="Inter", size=11), text_color=THEME["text_secondary"]).pack(anchor="w", padx=20, pady=(0, 14))

        self.deps_box = ctk.CTkFrame(card, fg_color=THEME["surface"], corner_radius=8, border_width=1, border_color=THEME["card_border"])
        self.deps_box.pack(fill="both", expand=True, padx=20, pady=(0, 16))

        action_box = ctk.CTkFrame(card, fg_color="transparent")
        action_box.pack(fill="x", padx=20, pady=(0, 18))

        self.btn_install_deps = ctk.CTkButton(
            action_box,
            text="📥 Install & Download All Dependencies",
            font=ctk.CTkFont(family="Inter", size=13, weight="bold"),
            fg_color=THEME["primary"],
            hover_color=THEME["primary_hover"],
            height=40,
            command=self._start_dep_installation
        )
        self.btn_install_deps.pack(side="left")

        refresh_deps_btn = ctk.CTkButton(
            action_box,
            text="🔄 Recheck Status",
            width=130,
            height=40,
            fg_color=THEME["card_border"],
            hover_color=THEME["card_hover"],
            command=self.refresh_dependencies_view
        )
        refresh_deps_btn.pack(side="left", padx=10)

    # --------------------------------------------------------------------------
    # Tab 4: Live Console & Logs
    # --------------------------------------------------------------------------
    def _build_logs_tab(self):
        tab = self.tab_logs

        card = ctk.CTkFrame(tab, fg_color=THEME["card_bg"], corner_radius=10, border_width=1, border_color=THEME["card_border"])
        card.pack(fill="both", expand=True, padx=12, pady=12)

        top_bar = ctk.CTkFrame(card, fg_color="transparent")
        top_bar.pack(fill="x", padx=16, pady=(14, 8))

        ctk.CTkLabel(top_bar, text="Live Server Activity & Execution Log", font=ctk.CTkFont(family="Inter", size=14, weight="bold"), text_color=THEME["text_primary"]).pack(side="left")

        btn_copy = ctk.CTkButton(
            top_bar,
            text="📋 Copy Logs",
            width=90,
            height=30,
            fg_color=THEME["surface"],
            hover_color=THEME["card_hover"],
            command=self._copy_logs
        )
        btn_copy.pack(side="right", padx=(8, 0))

        btn_clear = ctk.CTkButton(
            top_bar,
            text="🗑️ Clear",
            width=80,
            height=30,
            fg_color=THEME["surface"],
            hover_color=THEME["card_hover"],
            command=self._clear_logs
        )
        btn_clear.pack(side="right")

        self.log_textbox = ctk.CTkTextbox(
            card,
            fg_color=THEME["console_bg"],
            text_color=THEME["console_fg"],
            font=ctk.CTkFont(family="JetBrains Mono", size=11),
            corner_radius=8,
            border_width=1,
            border_color=THEME["console_border"]
        )
        self.log_textbox.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        self.log_textbox.insert("end", "[*] ZeroUSB Multi-OS Deployer initialized with real-time telemetry.\n")

    def _create_status_bar(self):
        bar = ctk.CTkFrame(self, fg_color=THEME["surface"], height=28, corner_radius=0)
        bar.pack(fill="x", side="bottom")

        self.status_bar_lbl = ctk.CTkLabel(
            bar,
            text="Ready. Select an interface and start the server.",
            font=ctk.CTkFont(family="Inter", size=10),
            text_color=THEME["text_muted"]
        )
        self.status_bar_lbl.pack(side="left", padx=16, pady=4)

    # --------------------------------------------------------------------------
    # Event Handlers & Controller Actions
    # --------------------------------------------------------------------------
    def log(self, message: str):
        timestamp = time.strftime("%H:%M:%S")
        formatted = f"[{timestamp}] {message}\n"
        self.log_textbox.insert("end", formatted)
        self.log_textbox.see("end")

    def refresh_network_interfaces(self):
        interfaces = get_network_interfaces()
        self.interfaces_list = interfaces
        options = [f"{iface} - {ip}" for iface, ip, _ in interfaces]

        self.iface_menu.configure(values=options)

        # Always prioritize wired Ethernet interface (enp, eth, eno, ens) for PXE deployment
        selected_tuple = None
        for iface, ip, is_def in interfaces:
            if any(iface.startswith(p) for p in ['enp', 'eth', 'eno', 'ens']):
                selected_tuple = (iface, ip)
                break
        if not selected_tuple and interfaces:
            selected_tuple = (interfaces[0][0], interfaces[0][1])

        if selected_tuple:
            opt_str = f"{selected_tuple[0]} - {selected_tuple[1]}"
            self.selected_interface_var.set(opt_str)
            self.selected_ip_var.set(selected_tuple[1])
            self.network_monitor.set_interface(selected_tuple[0])

        self.log(f"[*] Detected network interfaces: {', '.join(options)}")

    def _on_interface_selected(self, choice: str):
        if " - " in choice:
            iface, ip = choice.split(" - ")
            self.selected_ip_var.set(ip)
            self.network_monitor.set_interface(iface)
            self.log(f"[*] Selected interface: {iface} (IP: {ip})")

    def _on_boot_mode_changed(self, choice: str):
        if "UEFI" in choice and "Dual" not in choice:
            self.log("[*] Target Boot Mode set to Pure Native UEFI (64-bit).")
        elif "Legacy" in choice or "CSM" in choice:
            self.log("[*] Target Boot Mode set to Pure CSM / Legacy BIOS (32-bit).")
        else:
            self.log("[*] Target Boot Mode set to Dual Mode (Auto-Detect CSM & UEFI).")

    def _on_default_os_menu_selected(self, choice: str):
        installed = self.os_manager.get_installed_os_list()
        for idx, item in enumerate(installed):
            opt_str = f"[{idx+1}] {item['name']}"
            if opt_str == choice or item['name'] in choice:
                self._set_os_default(item['slug'])
                break

    def _on_timeout_menu_selected(self, choice: str):
        if "Instant" in choice or "0s" in choice:
            sec = 0
        elif "3" in choice:
            sec = 3
        elif "5" in choice:
            sec = 5
        elif "10" in choice:
            sec = 10
        elif "15" in choice:
            sec = 15
        elif "30" in choice:
            sec = 30
        elif "Wait" in choice or "Forever" in choice:
            sec = -1
        else:
            sec = 10

        choice_iface = self.selected_interface_var.get()
        ip = choice_iface.split(" - ")[1] if " - " in choice_iface else "192.168.42.1"
        try:
            port = int(self.http_port_var.get())
        except ValueError:
            port = 8080

        self.os_manager.set_boot_timeout(sec, ip, port)
        self.log(f"[*] Boot menu auto-boot timeout set to: {sec}s ({choice})")

    def refresh_dependencies_view(self):
        deps = check_dependencies(self.base_dir)

        for widget in self.deps_box.winfo_children():
            widget.destroy()

        for key, info in deps.items():
            row = ctk.CTkFrame(self.deps_box, fg_color="transparent")
            row.pack(fill="x", padx=14, pady=6)

            info_box = ctk.CTkFrame(row, fg_color="transparent")
            info_box.pack(side="left", fill="x", expand=True)

            lbl_name = ctk.CTkLabel(info_box, text=info['name'], font=ctk.CTkFont(family="Inter", size=12, weight="bold"), text_color=THEME["text_primary"])
            lbl_name.pack(anchor="w")

            lbl_desc = ctk.CTkLabel(info_box, text=f"{info['desc']} ({info['path']})", font=ctk.CTkFont(family="Inter", size=10), text_color=THEME["text_muted"])
            lbl_desc.pack(anchor="w")

            is_ok = info['installed']
            badge = ctk.CTkLabel(
                row,
                text="✓ Installed" if is_ok else "✗ Missing",
                font=ctk.CTkFont(family="Inter", size=11, weight="bold"),
                text_color=THEME["success"] if is_ok else THEME["danger"],
                fg_color=THEME["success_bg"] if is_ok else THEME["danger_bg"],
                corner_radius=8,
                padx=10,
                pady=4
            )
            badge.pack(side="right", padx=6)

    def refresh_installed_os_view(self):
        installed = self.os_manager.get_installed_os_list()

        # Update Multi-OS tab list
        for widget in self.os_list_container.winfo_children():
            widget.destroy()

        # Update Dashboard OS box
        for widget in self.dashboard_os_box.winfo_children():
            widget.destroy()

        header_row = ctk.CTkFrame(self.dashboard_os_box, fg_color="transparent")
        header_row.pack(fill="x", padx=12, pady=(10, 4))
        ctk.CTkLabel(header_row, text="Available Boot Menu Images", font=ctk.CTkFont(family="Inter", size=12, weight="bold"), text_color=THEME["text_primary"]).pack(side="left")
        ctk.CTkLabel(header_row, text="[ #1 is Auto-Boot Default ]", font=ctk.CTkFont(family="Inter", size=10), text_color=THEME["accent"]).pack(side="right")

        if not installed:
            ctk.CTkLabel(self.os_list_container, text="No operating systems staged yet. Add one above!", font=ctk.CTkFont(family="Inter", size=12), text_color=THEME["text_muted"]).pack(padx=16, pady=16)
            ctk.CTkLabel(self.dashboard_os_box, text="[!] No OS staged yet. Please add an ISO.", font=ctk.CTkFont(family="Inter", size=11), text_color=THEME["text_muted"]).pack(anchor="w", padx=12, pady=4)
            self.remove_os_menu.configure(values=["No OS installed"])
            self.selected_remove_os_var.set("No OS installed")
            self.btn_remove_os.configure(state="disabled")
            self.default_os_menu.configure(values=["No OS installed"])
            self.default_os_var.set("No OS installed")
        else:
            default_options = [f"[{i+1}] {item['name']}" for i, item in enumerate(installed)]
            self.default_os_menu.configure(values=default_options)
            self.default_os_var.set(default_options[0])

            # Sync timeout menu with current setting
            t_sec = self.os_manager.get_boot_timeout()
            timeout_map = {
                0: "⚡ Instant Boot (0s - No Keyboard Needed)",
                3: "⏱️ 3 Seconds",
                5: "⏱️ 5 Seconds",
                10: "⏱️ 10 Seconds (Default)",
                15: "⏱️ 15 Seconds",
                30: "⏱️ 30 Seconds",
                -1: "🛑 Wait Forever (No Timer)"
            }
            self.boot_timeout_var.set(timeout_map.get(t_sec, f"⏱️ {t_sec} Seconds"))

            remove_options = []
            total_count = len(installed)

            for idx, item in enumerate(installed):
                slug = item["slug"]
                icon = "🪟" if item["type"] == "windows" else ("🧰" if item["type"] in ["rescue", "rescue_memdisk", "iso_stream"] else "🐧")
                is_default = (idx == 0)

                # =========================================================
                # 1. Dashboard Row: Available Boot Menu Images
                # =========================================================
                d_row = ctk.CTkFrame(self.dashboard_os_box, fg_color=THEME["surface"] if is_default else "transparent", corner_radius=6)
                d_row.pack(fill="x", padx=10, pady=2)

                # Boot index badge [1], [2], etc.
                idx_badge = ctk.CTkLabel(
                    d_row,
                    text=f"[{idx + 1}] DEFAULT" if is_default else f"[{idx + 1}]",
                    font=ctk.CTkFont(family="Inter", size=10, weight="bold"),
                    text_color=THEME["success"] if is_default else THEME["text_secondary"],
                    fg_color=THEME["success_bg"] if is_default else THEME["card_bg"],
                    corner_radius=4,
                    padx=6,
                    pady=2
                )
                idx_badge.pack(side="left", padx=(6, 8), pady=4)

                # OS Name label
                ctk.CTkLabel(
                    d_row,
                    text=f"{icon} {item['name']}",
                    font=ctk.CTkFont(family="Inter", size=11, weight="bold" if is_default else "normal"),
                    text_color=THEME["text_primary"] if is_default else THEME["text_secondary"],
                    anchor="w"
                ).pack(side="left", fill="x", expand=True, pady=4)

                # Reorder & Set Default Buttons on Dashboard
                btn_frame = ctk.CTkFrame(d_row, fg_color="transparent")
                btn_frame.pack(side="right", padx=(4, 6), pady=2)

                if not is_default:
                    btn_make_def = ctk.CTkButton(
                        btn_frame,
                        text="⭐ Set Default",
                        width=85,
                        height=22,
                        font=ctk.CTkFont(size=9, weight="bold"),
                        fg_color=THEME["primary"],
                        hover_color=THEME["primary_hover"],
                        text_color="#ffffff",
                        command=lambda s=slug: self._set_os_default(s)
                    )
                    btn_make_def.pack(side="left", padx=(0, 4))

                btn_up = ctk.CTkButton(
                    btn_frame,
                    text="▲",
                    width=24,
                    height=22,
                    font=ctk.CTkFont(size=9, weight="bold"),
                    fg_color=THEME["card_bg"] if idx > 0 else THEME["surface"],
                    hover_color=THEME["card_hover"],
                    text_color=THEME["text_primary"] if idx > 0 else THEME["text_muted"],
                    state="normal" if idx > 0 else "disabled",
                    command=lambda s=slug: self._move_os_priority(s, -1)
                )
                btn_up.pack(side="left", padx=1)

                btn_down = ctk.CTkButton(
                    btn_frame,
                    text="▼",
                    width=24,
                    height=22,
                    font=ctk.CTkFont(size=9, weight="bold"),
                    fg_color=THEME["card_bg"] if idx < total_count - 1 else THEME["surface"],
                    hover_color=THEME["card_hover"],
                    text_color=THEME["text_primary"] if idx < total_count - 1 else THEME["text_muted"],
                    state="normal" if idx < total_count - 1 else "disabled",
                    command=lambda s=slug: self._move_os_priority(s, 1)
                )
                btn_down.pack(side="left", padx=1)

                # Size label
                ctk.CTkLabel(d_row, text=f"({item['size_str']})", font=ctk.CTkFont(family="Inter", size=10), text_color=THEME["text_muted"]).pack(side="right", padx=(0, 4), pady=4)

                # =========================================================
                # 2. Multi-OS Manager Tab Row
                # =========================================================
                row = ctk.CTkFrame(self.os_list_container, fg_color=THEME["surface"] if is_default else "transparent", corner_radius=6)
                row.pack(fill="x", padx=10, pady=4)

                order_badge = ctk.CTkLabel(
                    row,
                    text=f"Boot Target #{idx + 1}" + (" (Default)" if is_default else ""),
                    font=ctk.CTkFont(family="Inter", size=11, weight="bold"),
                    text_color=THEME["success"] if is_default else THEME["text_muted"],
                    fg_color=THEME["success_bg"] if is_default else THEME["card_bg"],
                    corner_radius=6,
                    padx=8,
                    pady=4
                )
                order_badge.pack(side="left", padx=(10, 8), pady=8)

                name_box = ctk.CTkFrame(row, fg_color="transparent")
                name_box.pack(side="left", fill="x", expand=True, pady=6)

                lbl_title = ctk.CTkLabel(name_box, text=f"{icon} {item['name']}", font=ctk.CTkFont(family="Inter", size=12, weight="bold"), text_color=THEME["text_primary"])
                lbl_title.pack(anchor="w")

                lbl_path = ctk.CTkLabel(name_box, text=f"Slug: [{item['slug']}] | Size: {item['size_str']}", font=ctk.CTkFont(family="Inter", size=10), text_color=THEME["text_muted"])
                lbl_path.pack(anchor="w")

                # Action buttons in Multi-OS Tab
                tab_btn_box = ctk.CTkFrame(row, fg_color="transparent")
                tab_btn_box.pack(side="right", padx=10, pady=6)

                if not is_default:
                    btn_make_def = ctk.CTkButton(
                        tab_btn_box,
                        text="⭐ Make #1",
                        width=70,
                        height=26,
                        font=ctk.CTkFont(family="Inter", size=11),
                        fg_color=THEME["accent"],
                        hover_color=THEME["primary"],
                        command=lambda s=slug: self._set_os_default(s)
                    )
                    btn_make_def.pack(side="left", padx=3)

                btn_tab_up = ctk.CTkButton(
                    tab_btn_box,
                    text="▲ Move Up",
                    width=75,
                    height=26,
                    font=ctk.CTkFont(family="Inter", size=11),
                    fg_color=THEME["card_bg"] if idx > 0 else THEME["surface"],
                    hover_color=THEME["card_hover"],
                    text_color=THEME["text_primary"] if idx > 0 else THEME["text_muted"],
                    state="normal" if idx > 0 else "disabled",
                    command=lambda s=slug: self._move_os_priority(s, -1)
                )
                btn_tab_up.pack(side="left", padx=2)

                btn_tab_down = ctk.CTkButton(
                    tab_btn_box,
                    text="▼ Move Down",
                    width=75,
                    height=26,
                    font=ctk.CTkFont(family="Inter", size=11),
                    fg_color=THEME["card_bg"] if idx < total_count - 1 else THEME["surface"],
                    hover_color=THEME["card_hover"],
                    text_color=THEME["text_primary"] if idx < total_count - 1 else THEME["text_muted"],
                    state="normal" if idx < total_count - 1 else "disabled",
                    command=lambda s=slug: self._move_os_priority(s, 1)
                )
                btn_tab_down.pack(side="left", padx=2)

                # Remove menu options
                opt_str = f"{item['name']} ({item['slug']}) - {item['size_str']}"
                remove_options.append(opt_str)

            self.remove_os_menu.configure(values=remove_options)
            self.selected_remove_os_var.set(remove_options[0])
            self.btn_remove_os.configure(state="normal")

    def _move_os_priority(self, slug: str, direction: int):
        ip = self.selected_ip_var.get() or "192.168.42.1"
        port = int(self.http_port_var.get() or 8080)
        success = self.os_manager.move_os_priority(slug, direction, ip, port)
        if success:
            self.refresh_installed_os_view()
            new_list = [f"[{i+1}] {item['name']}" for i, item in enumerate(self.os_manager.get_installed_os_list())]
            self.log(f"[✓] Boot menu priority updated: {', '.join(new_list)}")

    def _set_os_default(self, slug: str):
        ip = self.selected_ip_var.get() or "192.168.42.1"
        port = int(self.http_port_var.get() or 8080)
        success = self.os_manager.set_os_as_default(slug, ip, port)
        if success:
            self.refresh_installed_os_view()
            new_list = [f"[{i+1}] {item['name']}" for i, item in enumerate(self.os_manager.get_installed_os_list())]
            self.log(f"[✓] [{slug}] is now set as #1 Default Boot OS! Current order: {', '.join(new_list)}")

    def _periodic_health_check(self):
        # 1. Update Network Telemetry Chart
        stats = self.network_monitor.get_stats()
        self.network_chart.update_metrics(stats)

        # 2. Update Service Health Indicators
        status = self.server_manager.get_status()

        self.lbl_status_tftp.configure(
            text="● Active" if status['dnsmasq'] else "● Stopped",
            text_color=THEME["success"] if status['dnsmasq'] else THEME["text_muted"]
        )
        self.lbl_status_http.configure(
            text="● Active" if status['http'] else "● Stopped",
            text_color=THEME["success"] if status['http'] else THEME["text_muted"]
        )
        self.lbl_status_samba.configure(
            text="● Active" if status['samba'] else "● Stopped",
            text_color=THEME["success"] if status['samba'] else THEME["text_muted"]
        )

        # Global Badge
        if status['is_serving']:
            self.server_status_badge.configure(
                text=f"● SERVING PXE ({self.server_manager.current_ip})",
                text_color="#ffffff",
                fg_color=THEME["success"]
            )
            self.btn_toggle_server.configure(
                text="🛑 Stop PXE Network Server",
                fg_color=THEME["danger"],
                hover_color="#dc2626"
            )
        else:
            self.server_status_badge.configure(
                text="● OFFLINE",
                text_color=THEME["text_muted"],
                fg_color=THEME["card_border"]
            )
            self.btn_toggle_server.configure(
                text="🚀 Start PXE Network Server",
                fg_color=THEME["success"],
                hover_color="#059669"
            )

        self.after(500, self._periodic_health_check)

    def _toggle_server(self):
        is_running = self.server_manager.is_active or self.server_manager.get_status()['is_serving']
        if is_running:
            self.server_manager.stop(on_log=self.log)
            self.status_bar_lbl.configure(text="Server stopped.")
        else:
            choice = self.selected_interface_var.get()
            if " - " in choice:
                iface, ip = choice.split(" - ")
            else:
                iface, ip = "enp3s0", "192.168.1.41"

            try:
                port = int(self.http_port_var.get())
            except ValueError:
                port = 8080

            dhcp_mode_slug = "standalone" if "Direct" in self.dhcp_mode_var.get() else "proxy"
            
            boot_mode_raw = self.boot_target_mode_var.get()
            if "CSM" in boot_mode_raw or "Legacy" in boot_mode_raw:
                boot_mode_slug = "csm"
            elif "UEFI" in boot_mode_raw and "Dual" not in boot_mode_raw:
                boot_mode_slug = "uefi"
            else:
                boot_mode_slug = "dual"

            self.status_bar_lbl.configure(text=f"Starting PXE server on {iface} ({ip}) [{dhcp_mode_slug.upper()} | {boot_mode_slug.upper()}]...")
            # Generate updated multi-OS menu
            self.os_manager.generate_ipxe_menu(ip, port)

            success = self.server_manager.start(
                interface=iface,
                server_ip=ip,
                http_port=port,
                dhcp_mode=dhcp_mode_slug,
                boot_mode=boot_mode_slug,
                on_log=self.log
            )
            if success:
                self.status_bar_lbl.configure(text=f"Server LIVE on {ip}! Ready for client multi-OS network boot.")
            else:
                messagebox.showerror("Server Error", "Failed to start network server. Check live logs tab.")

    def _on_category_changed(self, category: str):
        filtered = get_presets_by_category(category)
        names = [p["name"] for p in filtered]
        self.preset_menu.configure(values=names)
        if self.selected_preset_var.get() not in names and names:
            self.selected_preset_var.set(names[0])
        self.log(f"[*] Filtered OS Profiles by category: {category} ({len(names)} profiles)")

    def _browse_iso(self):
        path = filedialog.askopenfilename(
            title="Select Operating System Installation Image",
            filetypes=[
                ("Supported Images", "*.iso *.dmg *.img"),
                ("ISO Disk Images", "*.iso"),
                ("Apple DMG Images", "*.dmg"),
                ("All Files", "*.*")
            ]
        )
        if path:
            self.iso_path_var.set(path)
            self.log(f"[*] Selected Image: {path}")

            # Auto-detect preset from image filename or signature
            detected = detect_os_from_iso(path)
            if detected:
                cat_name = TYPE_CATEGORY_MAP.get(detected.get("type"), "All Systems")
                self.selected_category_var.set(cat_name)
                self._on_category_changed(cat_name)
                self.selected_preset_var.set(detected["name"])
                self.log(f"[✓] Auto-detected OS Profile: {detected['name']} [{cat_name}]")
            else:
                self.log("[*] Unrecognized image name - please select Category & Profile manually.")

    def _start_os_extraction(self):
        iso_path = self.iso_path_var.get().strip()
        if not iso_path or not Path(iso_path).exists():
            messagebox.showwarning("No ISO Selected", "Please select a valid ISO file first.")
            return

        choice = self.selected_interface_var.get()
        server_ip = choice.split(" - ")[1] if " - " in choice else "192.168.1.41"

        # Find selected preset
        preset_name = self.selected_preset_var.get()
        preset = next((p for p in OS_PRESETS if p["name"] == preset_name), OS_PRESETS[0])
        os_slug = preset["slug"]
        os_type = preset["type"]

        self.btn_extract_os.configure(state="disabled")
        self.progress_os.set(0.0)

        def on_progress(p: float, step: str):
            self.after(0, lambda: self._update_os_progress(p, step))

        def on_finished(success: bool, msg: str):
            self.after(0, lambda: self._on_os_finished(success, msg))

        self.os_manager.extract_os(
            os_slug=os_slug,
            os_name=preset_name,
            os_type=os_type,
            iso_path=iso_path,
            server_ip=server_ip,
            on_progress=on_progress,
            on_log=self.log,
            on_finished=on_finished
        )

    def _update_os_progress(self, progress: float, step_text: str):
        self.progress_os.set(progress)
        self.lbl_os_step.configure(text=step_text)

    def _on_os_finished(self, success: bool, message: str):
        self.btn_extract_os.configure(state="normal")
        self.refresh_installed_os_view()
        if success:
            messagebox.showinfo("OS Added", message)
        else:
            messagebox.showerror("Extraction Failed", message)

    def _remove_selected_os(self):
        selected_text = self.selected_remove_os_var.get()
        if not selected_text or "No OS" in selected_text:
            return

        # Extract slug from "Name (slug) - Size"
        try:
            slug = selected_text.split("(")[-1].split(")")[0]
        except Exception:
            slug = "default_windows"

        confirm = messagebox.askyesno(
            "Confirm Removal",
            f"Are you sure you want to remove [{selected_text}]?\nThis will delete its installation files and update the boot menu."
        )
        if not confirm:
            return

        choice = self.selected_interface_var.get()
        server_ip = choice.split(" - ")[1] if " - " in choice else "192.168.1.41"

        self.btn_remove_os.configure(state="disabled")
        success, msg = self.os_manager.remove_os(slug, server_ip, on_log=self.log)
        self.btn_remove_os.configure(state="normal")
        self.refresh_installed_os_view()

        if success:
            messagebox.showinfo("OS Removed", msg)
        else:
            messagebox.showerror("Error", msg)

    def _start_dep_installation(self):
        self.btn_install_deps.configure(state="disabled")
        self.log("[*] Starting automated dependency installation...")

        def on_progress(p: float, step: str):
            self.log(f"  --> {step}")

        def on_finished(success: bool, msg: str):
            self.after(0, lambda: self._on_deps_finished(success, msg))

        self.dep_installer.install_dependencies(
            on_progress=on_progress,
            on_log=self.log,
            on_finished=on_finished
        )

    def _on_deps_finished(self, success: bool, message: str):
        self.btn_install_deps.configure(state="normal")
        self.refresh_dependencies_view()
        self.refresh_installed_os_view()
        if success:
            messagebox.showinfo("Dependencies Ready", message)
        else:
            messagebox.showerror("Installation Error", message)

    def _launch_packet_sniffer(self):
        try:
            terminal = shutil.which('terminology') or shutil.which('x-terminal-emulator') or shutil.which('gnome-terminal') or 'xterm'
            cmd = [terminal, '-e', f"sudo python3 {self.base_dir / 'scripts' / 'monitor-traffic.py'}"]
            subprocess.Popen(cmd)
            self.log("[+] Launched Real-Time Packet Sniffer terminal window.")
        except Exception as e:
            self.log(f"[!] Could not launch terminal sniffer: {e}")

    def _open_boot_folder(self):
        try:
            subprocess.Popen(['xdg-open', str(self.base_dir / 'srv')])
            self.log(f"[+] Opened directory: {self.base_dir / 'srv'}")
        except Exception as e:
            self.log(f"[!] Could not open directory: {e}")

    def _clear_logs(self):
        self.log_textbox.delete("1.0", "end")
        self.log("[*] Log buffer cleared.")

    def _copy_logs(self):
        content = self.log_textbox.get("1.0", "end")
        self.clipboard_clear()
        self.clipboard_append(content)
        self.status_bar_lbl.configure(text="Logs copied to clipboard.")


def main():
    try:
        app = NetworkInstallerApp()
        app.mainloop()
    except Exception as e:
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
