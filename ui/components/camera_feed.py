"""
APEX LAB Attendance System — Camera Feed Component
Displays responsive video stream with aesthetic face tracking boxes,
status badges, and names rendered directly ABOVE the detection square.
"""

import sys
import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple

import cv2
import numpy as np
from PIL import Image
import customtkinter as ctk

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
import config
from ui.themes import glassmorphism as theme

logger = logging.getLogger(__name__)


class CameraFeedWidget(ctk.CTkFrame):
    """Interactive camera viewport with high-aesthetic HUD overlay."""

    def __init__(self, master, **kwargs):
        super().__init__(
            master,
            fg_color=theme.COLOR_BG_PANEL,
            corner_radius=16,
            border_width=1,
            border_color=theme.COLOR_BORDER,
            **kwargs
        )

        self._image_label = ctk.CTkLabel(
            self,
            text="Initializing Camera Stream...",
            text_color=theme.COLOR_TEXT_SECONDARY,
            font=theme.get_font(15, "bold")
        )
        self._image_label.pack(fill="both", expand=True, padx=8, pady=8)

        # Current target display dimensions
        self._target_width = 720
        self._target_height = 540

    def set_display_dimensions(self, width: int, height: int):
        """Update target render dimensions for responsive scaling."""
        self._target_width = max(320, width)
        self._target_height = max(240, height)

    def render_frame(
        self,
        bgr_frame: np.ndarray,
        detections: List[Dict[str, Any]],
        coord_scale: float = 1.0,
    ):
        """
        Draw visual HUD bounding box and name tag above the detection square,
        then display onto the CustomTkinter label.

        Parameters
        ----------
        bgr_frame : np.ndarray
            The full resolution raw frame (BGR).
        detections : list of dict
            Each dict has:
            - 'location': (top, right, bottom, left)
            - 'name': str
            - 'status': 'matched' | 'unknown' | 'already_in'
            - 'confidence': float (optional)
        coord_scale : float
            Multiply coordinates by this factor if detection was performed on downscaled frame.
        """
        if bgr_frame is None or bgr_frame.size == 0:
            return

        annotated_frame = bgr_frame.copy()

        # Render each detection HUD overlay
        for det in detections:
            top, right, bottom, left = det["location"]

            # Scale back up to native frame coordinates
            top = int(top * coord_scale)
            right = int(right * coord_scale)
            bottom = int(bottom * coord_scale)
            left = int(left * coord_scale)

            name = det.get("name", "Unknown")
            status = det.get("status", "unknown")
            confidence = det.get("confidence", 0.0)

            is_known = status in ("matched", "checked_in", "already_in")

            # Colors in BGR for OpenCV
            # Matched = Neon Emerald (BGR: 129, 185, 16), Unknown = Neon Red (BGR: 68, 68, 239)
            if is_known:
                box_color = (80, 220, 100)      # Neon Green BGR
                text_bg_color = (35, 120, 50)   # Dark Green fill
            else:
                box_color = (60, 60, 245)       # Electric Red BGR
                text_bg_color = (30, 30, 150)   # Dark Red fill

            # 1. Sleek Detection Bounding Box with Bracket Accents
            self._draw_aesthetic_box(annotated_frame, left, top, right, bottom, box_color)

            # 2. Display Name & Badge strictly ABOVE the detection square
            display_text = f" {name.upper()} "
            if confidence > 0 and is_known:
                display_text += f"[{int(confidence * 100)}%]"
            elif not is_known:
                display_text += "[UNREGISTERED]"

            self._draw_name_tag_above_box(
                annotated_frame,
                left,
                top,
                right,
                display_text,
                box_color,
                text_bg_color,
            )

        # Convert OpenCV BGR to RGB for PIL & CTkImage
        rgb_frame = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)
        h, w, _ = rgb_frame.shape

        # Scale maintaining aspect ratio to fit viewport
        scale_w = self._target_width / w
        scale_h = self._target_height / h
        fit_scale = min(scale_w, scale_h)
        new_w = max(1, int(w * fit_scale))
        new_h = max(1, int(h * fit_scale))

        resized_img = cv2.resize(rgb_frame, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
        pil_img = Image.fromarray(resized_img)

        ctk_image = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(new_w, new_h))
        self._image_label.configure(image=ctk_image, text="")

    def _draw_aesthetic_box(
        self,
        img: np.ndarray,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        color: Tuple[int, int, int],
    ):
        """Draw a futuristic framed bounding box with corner accent brackets."""
        # Thin boundary
        cv2.rectangle(img, (x1, y1), (x2, y2), color, 1, cv2.LINE_AA)

        # Corner bracket lengths
        w = x2 - x1
        h = y2 - y1
        line_len = max(10, min(int(w * 0.22), int(h * 0.22)))
        thick = 3

        # Top-Left
        cv2.line(img, (x1, y1), (x1 + line_len, y1), color, thick, cv2.LINE_AA)
        cv2.line(img, (x1, y1), (x1, y1 + line_len), color, thick, cv2.LINE_AA)

        # Top-Right
        cv2.line(img, (x2, y1), (x2 - line_len, y1), color, thick, cv2.LINE_AA)
        cv2.line(img, (x2, y1), (x2, y1 + line_len), color, thick, cv2.LINE_AA)

        # Bottom-Left
        cv2.line(img, (x1, y2), (x1 + line_len, y2), color, thick, cv2.LINE_AA)
        cv2.line(img, (x1, y2), (x1, y2 - line_len), color, thick, cv2.LINE_AA)

        # Bottom-Right
        cv2.line(img, (x2, y2), (x2 - line_len, y2), color, thick, cv2.LINE_AA)
        cv2.line(img, (x2, y2), (x2, y2 - line_len), color, thick, cv2.LINE_AA)

    def _draw_name_tag_above_box(
        self,
        img: np.ndarray,
        x1: int,
        y1: int,
        x2: int,
        text: str,
        border_color: Tuple[int, int, int],
        bg_color: Tuple[int, int, int],
    ):
        """
        Draw a chic pill / badge ABOVE the bounding box (y1).
        If y1 is too close to top edge, place inside with slight offset.
        """
        font = cv2.FONT_HERSHEY_DUPLEX
        font_scale = 0.55
        thickness = 1

        (text_w, text_h), baseline = cv2.getTextSize(text, font, font_scale, thickness)

        pill_pad_x = 8
        pill_pad_y = 6
        total_w = text_w + (pill_pad_x * 2)
        total_h = text_h + baseline + (pill_pad_y * 2)

        # Position above box
        tag_y2 = y1 - 6
        tag_y1 = tag_y2 - total_h

        # Edge fallback if face is at the extreme top of camera
        if tag_y1 < 4:
            tag_y1 = y1 + 6
            tag_y2 = tag_y1 + total_h

        tag_x1 = x1
        tag_x2 = tag_x1 + total_w

        # Ensure inside frame bounds
        h_frame, w_frame, _ = img.shape
        if tag_x2 > w_frame - 4:
            tag_x2 = w_frame - 4
            tag_x1 = max(4, tag_x2 - total_w)

        # Filled badge background
        cv2.rectangle(img, (tag_x1, tag_y1), (tag_x2, tag_y2), bg_color, -1)
        # Accent border
        cv2.rectangle(img, (tag_x1, tag_y1), (tag_x2, tag_y2), border_color, 1, cv2.LINE_AA)

        # Text rendering (Crisp White BGR: 255, 255, 255)
        text_x = tag_x1 + pill_pad_x
        text_y = tag_y1 + pill_pad_y + text_h
        cv2.putText(
            img,
            text,
            (text_x, text_y),
            font,
            font_scale,
            (255, 255, 255),
            thickness,
            cv2.LINE_AA,
        )
