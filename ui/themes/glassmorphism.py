"""
APEX LAB Attendance System — UI Theme & Styling
Frosted dark glassmorphism styling parameters, palettes, and typography.
"""

import sys
from pathlib import Path
import customtkinter as ctk

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
import config

# Color Palette — Glassmorphic Deep Slate & Neon Accents
COLOR_BG_ROOT = "#0B0F19"         # Ultra-deep dark obsidian
COLOR_BG_PANEL = "#111827"        # Translucent dark charcoal panel
COLOR_BG_CARD = "#1F2937"         # Elevated card surface
COLOR_BG_CARD_HOVER = "#2D3748"   # Hover state
COLOR_BORDER = "#374151"          # Subtle thin border

# Accents
COLOR_ACCENT_PRIMARY = "#3B82F6"  # Electric Cobalt / Sapphire
COLOR_ACCENT_SUCCESS = "#10B981"  # Neon Emerald (Check-in / Matched)
COLOR_ACCENT_WARNING = "#F59E0B"  # Warm Amber (Already in / Processing)
COLOR_ACCENT_DANGER = "#EF4444"   # Vibrant Crimson (Unknown / Alert)
COLOR_ACCENT_CYAN = "#06B6D4"     # Cyber Cyan for metrics

# Typography colors
COLOR_TEXT_PRIMARY = "#F9FAFB"    # Crisp White
COLOR_TEXT_SECONDARY = "#9CA3AF"  # Slate Gray
COLOR_TEXT_MUTED = "#6B7280"      # Dim Gray

# Fonts (Platform independent fallbacks)
FONT_FAMILY = "Segoe UI" if sys.platform == "win32" else "DejaVu Sans"

def get_font(size: int = 13, weight: str = "normal"):
    """Return a styled CTkFont instance."""
    return ctk.CTkFont(family=FONT_FAMILY, size=size, weight=weight)

def apply_global_theme():
    """Configure CustomTkinter global appearance defaults."""
    ctk.set_appearance_mode("Dark")
    ctk.set_default_color_theme("blue")

def get_status_color(status: str) -> str:
    """Map attendance or detection status to aesthetic hex colors."""
    status_lower = status.lower()
    if status_lower in ("checked_in", "present", "matched", "active"):
        return COLOR_ACCENT_SUCCESS
    elif status_lower in ("already_in", "processing", "warning", "pending"):
        return COLOR_ACCENT_WARNING
    elif status_lower in ("unknown", "danger", "alert", "error", "absent"):
        return COLOR_ACCENT_DANGER
    return COLOR_ACCENT_PRIMARY
