"""
APEX LAB Attendance System — Alert Dialog Component
Displays an aesthetic modal alert whenever an unknown/unregistered person is detected,
showing their snapshot and prompt instructions for action.
"""

import sys
import logging
from pathlib import Path
from typing import Optional, Callable

from PIL import Image
import customtkinter as ctk

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
import config
from ui.themes import glassmorphism as theme

logger = logging.getLogger(__name__)


class AlertDialog(ctk.CTkToplevel):
    """Futuristic modal dialog triggered on unknown person detection."""

    def __init__(
        self,
        master,
        snapshot_path: Optional[str] = None,
        on_action: Optional[Callable[[str], None]] = None,
        **kwargs
    ):
        super().__init__(master, **kwargs)

        self._on_action = on_action
        self._snapshot_path = snapshot_path

        self.title("SECURITY ALERT — UNREGISTERED PERSON")
        self.geometry("460x520")
        self.resizable(False, False)
        self.configure(fg_color=theme.COLOR_BG_ROOT)

        # Stay on top and focus
        self.transient(master)
        self.grab_set()

        self._build_ui()

    def _build_ui(self):
        # Outer container with crimson border
        border_frame = ctk.CTkFrame(
            self,
            fg_color=theme.COLOR_BG_PANEL,
            corner_radius=16,
            border_width=2,
            border_color=theme.COLOR_ACCENT_DANGER,
        )
        border_frame.pack(fill="both", expand=True, padx=16, pady=16)

        # Alert header
        ctk.CTkLabel(
            border_frame,
            text="⚠️ UNKNOWN PERSON DETECTED",
            font=theme.get_font(16, "bold"),
            text_color=theme.COLOR_ACCENT_DANGER,
        ).pack(pady=(16, 4))

        ctk.CTkLabel(
            border_frame,
            text="Subject not matched with registered APEX LAB database.",
            font=theme.get_font(11, "normal"),
            text_color=theme.COLOR_TEXT_SECONDARY,
        ).pack(pady=(0, 12))

        # Snapshot Preview
        self._preview_frame = ctk.CTkFrame(
            border_frame,
            fg_color=theme.COLOR_BG_CARD,
            corner_radius=12,
            width=280,
            height=210,
        )
        self._preview_frame.pack(padx=20, pady=8)
        self._preview_frame.pack_propagate(False)

        if self._snapshot_path and Path(self._snapshot_path).exists():
            try:
                pil_img = Image.open(self._snapshot_path)
                pil_img.thumbnail((260, 190))
                ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=pil_img.size)
                lbl = ctk.CTkLabel(self._preview_frame, image=ctk_img, text="")
                lbl.pack(expand=True)
            except Exception as e:
                logger.error("Failed loading snapshot: %s", e)
                ctk.CTkLabel(self._preview_frame, text="[Snapshot Preview Unavailable]").pack(expand=True)
        else:
            ctk.CTkLabel(
                self._preview_frame,
                text="[ Snapshot Captured ]",
                font=theme.get_font(12, "italic"),
                text_color=theme.COLOR_TEXT_MUTED,
            ).pack(expand=True)

        # Instructions / Action Prompt
        ctk.CTkLabel(
            border_frame,
            text="Please specify the action to take for this subject:",
            font=theme.get_font(12, "normal"),
            text_color=theme.COLOR_TEXT_PRIMARY,
        ).pack(pady=(12, 10))

        # Action Buttons
        btn_box = ctk.CTkFrame(border_frame, fg_color="transparent")
        btn_box.pack(fill="x", padx=24, pady=(0, 16))

        btn_enroll = ctk.CTkButton(
            btn_box,
            text="👤 Register Person Now",
            font=theme.get_font(12, "bold"),
            fg_color=theme.COLOR_ACCENT_SUCCESS,
            hover_color="#059669",
            corner_radius=8,
            height=36,
            command=lambda: self._handle_choice("enroll"),
        )
        btn_enroll.pack(fill="x", pady=4)

        btn_visitor = ctk.CTkButton(
            btn_box,
            text="🏷️ Log as Temporary Visitor",
            font=theme.get_font(12, "normal"),
            fg_color=theme.COLOR_BG_CARD,
            hover_color=theme.COLOR_BG_CARD_HOVER,
            border_width=1,
            border_color=theme.COLOR_BORDER,
            corner_radius=8,
            height=32,
            command=lambda: self._handle_choice("visitor"),
        )
        btn_visitor.pack(fill="x", pady=4)

        btn_dismiss = ctk.CTkButton(
            btn_box,
            text="Dismiss Alert",
            font=theme.get_font(11, "normal"),
            fg_color="transparent",
            hover_color=theme.COLOR_BG_CARD,
            text_color=theme.COLOR_TEXT_MUTED,
            corner_radius=8,
            height=28,
            command=lambda: self._handle_choice("dismiss"),
        )
        btn_dismiss.pack(fill="x", pady=2)

    def _handle_choice(self, action: str):
        self.grab_release()
        self.destroy()
        if self._on_action:
            self._on_action(action)
