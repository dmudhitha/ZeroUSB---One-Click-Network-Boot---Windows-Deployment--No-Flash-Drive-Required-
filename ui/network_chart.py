import tkinter as tk
from typing import Dict, List, Any
import customtkinter as ctk
from ui.theme import THEME

class NetworkTrafficChart(ctk.CTkFrame):
    """
    Real-time rolling area/line chart widget displaying network throughput (TX/RX)
    with dynamic auto-scaling and visual stage flow breakdown.
    """
    def __init__(self, parent, **kwargs):
        super().__init__(parent, fg_color=THEME["card_bg"], corner_radius=10, border_width=1, border_color=THEME["card_border"], **kwargs)

        self._create_header_and_metrics()
        self._create_canvas()
        self._create_protocol_stages()

    def _create_header_and_metrics(self):
        # Header Row
        header_row = ctk.CTkFrame(self, fg_color="transparent")
        header_row.pack(fill="x", padx=16, pady=(12, 6))

        title_lbl = ctk.CTkLabel(
            header_row,
            text="📊 Real-Time Network Data Flow & Throughput",
            font=ctk.CTkFont(family="Inter", size=14, weight="bold"),
            text_color=THEME["text_primary"]
        )
        title_lbl.pack(side="left")

        # Metric Badges
        metrics_row = ctk.CTkFrame(self, fg_color="transparent")
        metrics_row.pack(fill="x", padx=16, pady=(0, 10))

        self.card_tx = self._create_metric_pill(metrics_row, "Outgoing (TX / Server ➔ Client):", "0.0 KB/s", THEME["success"])
        self.card_rx = self._create_metric_pill(metrics_row, "Incoming (RX):", "0.0 KB/s", THEME["accent"])
        self.card_peak = self._create_metric_pill(metrics_row, "Peak Speed:", "0.0 KB/s", THEME["warning"])
        self.card_total = self._create_metric_pill(metrics_row, "Total Transferred:", "0.0 MB", THEME["text_primary"])

    def _create_metric_pill(self, parent, label: str, val: str, color: str):
        box = ctk.CTkFrame(parent, fg_color=THEME["surface"], corner_radius=8, border_width=1, border_color=THEME["card_border"])
        box.pack(side="left", fill="x", expand=True, padx=4)

        lbl = ctk.CTkLabel(box, text=label, font=ctk.CTkFont(family="Inter", size=10), text_color=THEME["text_muted"])
        lbl.pack(anchor="w", padx=10, pady=(6, 1))

        val_lbl = ctk.CTkLabel(box, text=val, font=ctk.CTkFont(family="Inter", size=13, weight="bold"), text_color=color)
        val_lbl.pack(anchor="w", padx=10, pady=(0, 6))
        return val_lbl

    def _create_canvas(self):
        canvas_container = ctk.CTkFrame(self, fg_color=THEME["console_bg"], corner_radius=8, border_width=1, border_color=THEME["card_border"])
        canvas_container.pack(fill="both", expand=True, padx=16, pady=(0, 10))

        self.canvas = tk.Canvas(
            canvas_container,
            bg=THEME["console_bg"],
            highlightthickness=0,
            bd=0,
            height=160
        )
        self.canvas.pack(fill="both", expand=True, padx=6, pady=6)
        self.canvas.bind("<Configure>", lambda event: self.redraw())

        # Internal state
        self.history_tx: List[float] = []
        self.history_rx: List[float] = []

    def _create_protocol_stages(self):
        stage_frame = ctk.CTkFrame(self, fg_color=THEME["surface"], corner_radius=8, border_width=1, border_color=THEME["card_border"])
        stage_frame.pack(fill="x", padx=16, pady=(0, 12))

        ctk.CTkLabel(
            stage_frame,
            text="Active Network Pipeline Stage:",
            font=ctk.CTkFont(family="Inter", size=11, weight="bold"),
            text_color=THEME["text_secondary"]
        ).pack(side="left", padx=12, pady=6)

        self.stages = {}
        for key, name, desc in [
            ('dhcp', '1. ProxyDHCP', 'Port 4011'),
            ('tftp', '2. TFTP Bootloader', 'Port 69 (ipxe.efi)'),
            ('http', '3. HTTP WinPE', 'Port 8080 (boot.wim)'),
            ('samba', '4. Samba Setup', 'Port 445 (install.wim)'),
        ]:
            pill = ctk.CTkLabel(
                stage_frame,
                text=f"{name} ({desc})",
                font=ctk.CTkFont(family="Inter", size=10),
                text_color=THEME["text_muted"],
                fg_color=THEME["card_bg"],
                corner_radius=6,
                padx=8,
                pady=3
            )
            pill.pack(side="left", padx=4, pady=6)
            self.stages[key] = pill

    def update_metrics(self, stats: Dict[str, Any]):
        tx_speed = stats.get("tx_speed", 0.0)
        rx_speed = stats.get("rx_speed", 0.0)
        peak_tx = stats.get("peak_tx", 0.0)
        total_tx = stats.get("total_tx", 0)

        self.history_tx = stats.get("history_tx", [])
        self.history_rx = stats.get("history_rx", [])

        # Update metric labels
        self.card_tx.configure(text=self._format_speed(tx_speed))
        self.card_rx.configure(text=self._format_speed(rx_speed))
        self.card_peak.configure(text=self._format_speed(peak_tx))
        self.card_total.configure(text=self._format_size(total_tx))

        # Dynamic Stage Highlight based on throughput
        # If speed > 10MB/s -> either HTTP WinPE streaming or Samba Windows Setup
        if tx_speed > 2 * 1024 * 1024:
            self._set_stage_active('http')
            self._set_stage_active('samba')
        elif tx_speed > 50 * 1024:
            self._set_stage_active('tftp')
        else:
            self._reset_stages()

        self.redraw()

    def _set_stage_active(self, active_key: str):
        for key, widget in self.stages.items():
            if key == active_key:
                widget.configure(text_color="#ffffff", fg_color=THEME["success"])
            else:
                widget.configure(text_color=THEME["text_muted"], fg_color=THEME["card_bg"])

    def _reset_stages(self):
        for widget in self.stages.values():
            widget.configure(text_color=THEME["text_muted"], fg_color=THEME["card_bg"])

    def redraw(self):
        self.canvas.delete("all")
        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()

        if width <= 10 or height <= 10:
            return

        # Margins
        pad_left = 55
        pad_right = 15
        pad_top = 15
        pad_bottom = 25

        plot_w = max(10, width - pad_left - pad_right)
        plot_h = max(10, height - pad_top - pad_bottom)

        # Compute max scale (dynamic auto-range)
        max_val = max([max(self.history_tx or [0]), max(self.history_rx or [0]), 1024 * 50])  # Minimum 50 KB/s scale
        max_val = max_val * 1.2  # 20% headroom

        # Draw Grid Lines
        grid_color = "#1e293b"
        text_color = "#64748b"

        # 4 Horizontal grid levels
        for i in range(4):
            y = pad_top + (plot_h / 3) * i
            level_val = max_val * (1 - (i / 3))
            self.canvas.create_line(pad_left, y, pad_left + plot_w, y, fill=grid_color, dash=(2, 4))
            self.canvas.create_text(
                pad_left - 8, y,
                text=self._format_speed(level_val),
                anchor="e",
                fill=text_color,
                font=("Inter", 9)
            )

        # Time labels on X Axis
        self.canvas.create_text(pad_left, pad_top + plot_h + 12, text="60s ago", anchor="w", fill=text_color, font=("Inter", 9))
        self.canvas.create_text(pad_left + plot_w / 2, pad_top + plot_h + 12, text="30s ago", anchor="center", fill=text_color, font=("Inter", 9))
        self.canvas.create_text(pad_left + plot_w, pad_top + plot_h + 12, text="Now", anchor="e", fill=text_color, font=("Inter", 9))

        # Plot Upload / TX (Server to Client) Area & Line
        self._plot_series(self.history_tx, pad_left, pad_top, plot_w, plot_h, max_val, line_color="#10b981", fill_color="#064e3b")

        # Plot Download / RX Line
        self._plot_series(self.history_rx, pad_left, pad_top, plot_w, plot_h, max_val, line_color="#38bdf8", fill_color=None)

    def _plot_series(self, data: List[float], x0: int, y0: int, w: int, h: int, max_val: float, line_color: str, fill_color: str = None):
        if not data or len(data) < 2:
            return

        points = []
        n = len(data)
        dx = w / (n - 1)

        for i, val in enumerate(data):
            x = x0 + i * dx
            norm = min(1.0, max(0.0, val / max_val))
            y = y0 + h - (norm * h)
            points.append((x, y))

        # Fill Polygon if requested
        if fill_color:
            poly_points = [x0, y0 + h]
            for x, y in points:
                poly_points.extend([x, y])
            poly_points.extend([x0 + w, y0 + h])
            self.canvas.create_polygon(poly_points, fill=fill_color, outline="", stipple="gray50")

        # Draw smooth connecting line
        flat_points = []
        for x, y in points:
            flat_points.extend([x, y])

        self.canvas.create_line(flat_points, fill=line_color, width=2, smooth=True)

    def _format_speed(self, b_per_sec: float) -> str:
        if b_per_sec < 1024:
            return f"{b_per_sec:.0f} B/s"
        elif b_per_sec < 1024 * 1024:
            return f"{b_per_sec / 1024:.1f} KB/s"
        elif b_per_sec < 1024 * 1024 * 1024:
            return f"{b_per_sec / (1024 * 1024):.1f} MB/s"
        else:
            return f"{b_per_sec / (1024 * 1024 * 1024):.2f} GB/s"

    def _format_size(self, num_bytes: int) -> str:
        if num_bytes < 1024:
            return f"{num_bytes} B"
        elif num_bytes < 1024 * 1024:
            return f"{num_bytes / 1024:.1f} KB"
        elif num_bytes < 1024 * 1024 * 1024:
            return f"{num_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{num_bytes / (1024 * 1024 * 1024):.2f} GB"
