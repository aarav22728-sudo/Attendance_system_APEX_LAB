"""
APEX LAB Attendance System — Status & Analytics Panel
Glassmorphism dashboard sidebar displaying real-time metrics,
last recognized subject card, and live check-in telemetry.
"""

import sys
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

import customtkinter as ctk

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
import config
from ui.themes import glassmorphism as theme

logger = logging.getLogger(__name__)


class StatusPanel(ctk.CTkFrame):
    """Sleek dark HUD panel showing attendance telemetry."""

    def __init__(self, master, on_enroll_click=None, on_report_click=None, **kwargs):
        super().__init__(
            master,
            fg_color=theme.COLOR_BG_PANEL,
            corner_radius=16,
            border_width=1,
            border_color=theme.COLOR_BORDER,
            **kwargs
        )

        self._on_enroll = on_enroll_click
        self._on_report = on_report_click

        self._build_header()
        self._build_last_recognized_card()
        self._build_metrics_grid()
        self._build_live_feed()
        self._build_quick_actions()

    # ------------------------------------------------------------------
    # UI Layout Construction
    # ------------------------------------------------------------------
    def _build_header(self):
        """APEX LAB branding header."""
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=16, pady=(16, 12))

        title_label = ctk.CTkLabel(
            header_frame,
            text="APEX LAB",
            font=theme.get_font(20, "bold"),
            text_color=theme.COLOR_TEXT_PRIMARY,
        )
        title_label.pack(side="left")

        self._badge = ctk.CTkLabel(
            header_frame,
            text="● LIVE MONITOR",
            font=theme.get_font(10, "bold"),
            text_color=theme.COLOR_ACCENT_SUCCESS,
            fg_color=theme.COLOR_BG_CARD,
            corner_radius=8,
            padx=8,
            pady=2,
        )
        self._badge.pack(side="right")

    def _build_last_recognized_card(self):
        """Card highlighting the most recently detected person."""
        self._card = ctk.CTkFrame(
            self,
            fg_color=theme.COLOR_BG_CARD,
            corner_radius=12,
            border_width=1,
            border_color=theme.COLOR_BORDER,
        )
        self._card.pack(fill="x", padx=16, pady=8)

        # Card header label
        card_title = ctk.CTkLabel(
            self._card,
            text="LAST RECOGNIZED SUBJECT",
            font=theme.get_font(10, "bold"),
            text_color=theme.COLOR_TEXT_MUTED,
        )
        card_title.pack(anchor="w", padx=14, pady=(12, 2))

        # Subject Name
        self._subject_name = ctk.CTkLabel(
            self._card,
            text="Awaiting Subject...",
            font=theme.get_font(18, "bold"),
            text_color=theme.COLOR_TEXT_PRIMARY,
        )
        self._subject_name.pack(anchor="w", padx=14, pady=(0, 4))

        # Meta row: Role + Time
        meta_row = ctk.CTkFrame(self._card, fg_color="transparent")
        meta_row.pack(fill="x", padx=14, pady=(0, 8))

        self._role_badge = ctk.CTkLabel(
            meta_row,
            text="ROLE: —",
            font=theme.get_font(11, "bold"),
            text_color=theme.COLOR_TEXT_SECONDARY,
        )
        self._role_badge.pack(side="left")

        self._timestamp_lbl = ctk.CTkLabel(
            meta_row,
            text="TIME: —",
            font=theme.get_font(11, "normal"),
            text_color=theme.COLOR_TEXT_MUTED,
        )
        self._timestamp_lbl.pack(side="right")

        # Action status pill
        self._status_pill = ctk.CTkLabel(
            self._card,
            text="READY",
            font=theme.get_font(11, "bold"),
            text_color=theme.COLOR_TEXT_PRIMARY,
            fg_color=theme.COLOR_BORDER,
            corner_radius=6,
            pady=4,
        )
        self._status_pill.pack(fill="x", padx=14, pady=(0, 12))

    def _build_metrics_grid(self):
        """Attendance summary counts."""
        grid_container = ctk.CTkFrame(self, fg_color="transparent")
        grid_container.pack(fill="x", padx=16, pady=6)

        # Configure columns
        grid_container.columnconfigure(0, weight=1)
        grid_container.columnconfigure(1, weight=1)
        grid_container.columnconfigure(2, weight=1)

        # Present metric
        self._metric_present = self._create_metric_box(
            grid_container, "PRESENT", "0", theme.COLOR_ACCENT_SUCCESS, 0
        )
        # Absent metric
        self._metric_absent = self._create_metric_box(
            grid_container, "ABSENT", "0", theme.COLOR_ACCENT_WARNING, 1
        )
        # Unknown alerts
        self._metric_unknown = self._create_metric_box(
            grid_container, "UNREGISTERED", "0", theme.COLOR_ACCENT_DANGER, 2
        )

    def _create_metric_box(self, parent, title, initial_val, accent_color, col):
        frame = ctk.CTkFrame(
            parent,
            fg_color=theme.COLOR_BG_CARD,
            corner_radius=10,
            border_width=1,
            border_color=theme.COLOR_BORDER,
        )
        frame.grid(row=0, column=col, padx=3, pady=2, sticky="nsew")

        lbl_title = ctk.CTkLabel(
            frame,
            text=title,
            font=theme.get_font(9, "bold"),
            text_color=theme.COLOR_TEXT_MUTED,
        )
        lbl_title.pack(pady=(8, 0))

        val_label = ctk.CTkLabel(
            frame,
            text=initial_val,
            font=theme.get_font(16, "bold"),
            text_color=accent_color,
        )
        val_label.pack(pady=(0, 8))
        return val_label

    def _build_live_feed(self):
        """Scrollable list of today's check-ins."""
        feed_header = ctk.CTkFrame(self, fg_color="transparent")
        feed_header.pack(fill="x", padx=16, pady=(12, 4))

        ctk.CTkLabel(
            feed_header,
            text="LIVE CHECK-IN FEED",
            font=theme.get_font(11, "bold"),
            text_color=theme.COLOR_TEXT_SECONDARY,
        ).pack(side="left")

        self._feed_scroll = ctk.CTkScrollableFrame(
            self,
            fg_color=theme.COLOR_BG_CARD,
            corner_radius=10,
            border_width=1,
            border_color=theme.COLOR_BORDER,
            height=160,
        )
        self._feed_scroll.pack(fill="both", expand=True, padx=16, pady=4)

        self._empty_feed_label = ctk.CTkLabel(
            self._feed_scroll,
            text="No scans recorded yet today",
            font=theme.get_font(11, "italic"),
            text_color=theme.COLOR_TEXT_MUTED,
        )
        self._empty_feed_label.pack(pady=20)
        self._feed_item_count = 0

    def _build_quick_actions(self):
        """Bottom action buttons (Enroll Person & Export Weekly Report)."""
        action_frame = ctk.CTkFrame(self, fg_color="transparent")
        action_frame.pack(fill="x", padx=16, pady=(8, 16))

        btn_enroll = ctk.CTkButton(
            action_frame,
            text="➕ Register Face",
            font=theme.get_font(12, "bold"),
            fg_color=theme.COLOR_ACCENT_PRIMARY,
            hover_color="#2563EB",
            corner_radius=8,
            height=36,
            command=self._on_enroll,
        )
        btn_enroll.pack(fill="x", pady=3)

        btn_report = ctk.CTkButton(
            action_frame,
            text="📊 Export Excel Report",
            font=theme.get_font(12, "normal"),
            fg_color=theme.COLOR_BG_CARD,
            hover_color=theme.COLOR_BG_CARD_HOVER,
            border_width=1,
            border_color=theme.COLOR_BORDER,
            corner_radius=8,
            height=32,
            command=self._on_report,
        )
        btn_report.pack(fill="x", pady=3)

    # ------------------------------------------------------------------
    # Public Update Methods
    # ------------------------------------------------------------------
    def update_last_recognized(
        self,
        name: str,
        role: str,
        timestamp: str,
        confidence: float,
        status: str,
    ):
        """Update the Last Recognized card with live telemetry."""
        color = theme.get_status_color(status)
        self._subject_name.configure(text=name)
        self._role_badge.configure(text=f"ROLE: {role.upper()}")
        self._timestamp_lbl.configure(text=f"TIME: {timestamp}")

        if status == "checked_in":
            pill_text = f"✔ CHECKED IN ({int(confidence * 100)}%)"
        elif status == "already_in":
            pill_text = "ℹ ALREADY CHECKED IN"
        elif status == "unknown":
            pill_text = "⚠ UNREGISTERED PERSON"
        else:
            pill_text = status.upper()

        self._status_pill.configure(
            text=pill_text,
            fg_color=color,
            text_color="#FFFFFF",
        )
        self._card.configure(border_color=color)

    def update_stats(self, present: int, absent: int, unknown: int, total: int):
        """Update metrics numbers."""
        self._metric_present.configure(text=str(present))
        self._metric_absent.configure(text=str(absent))
        self._metric_unknown.configure(text=str(unknown))

    def add_activity_log(self, name: str, timestamp: str, status: str):
        """Append a scan item into the live feed."""
        if self._empty_feed_label.winfo_exists():
            self._empty_feed_label.destroy()

        color = theme.get_status_color(status)

        row = ctk.CTkFrame(self._feed_scroll, fg_color="transparent")
        row.pack(fill="x", pady=2)

        dot = ctk.CTkLabel(
            row,
            text="●",
            font=theme.get_font(12, "bold"),
            text_color=color,
            width=14,
        )
        dot.pack(side="left")

        name_lbl = ctk.CTkLabel(
            row,
            text=name,
            font=theme.get_font(11, "bold"),
            text_color=theme.COLOR_TEXT_PRIMARY,
        )
        name_lbl.pack(side="left", padx=4)

        time_lbl = ctk.CTkLabel(
            row,
            text=timestamp,
            font=theme.get_font(10, "normal"),
            text_color=theme.COLOR_TEXT_MUTED,
        )
        time_lbl.pack(side="right", padx=6)

        self._feed_item_count += 1
