"""
APEX LAB Attendance System — Face Enrollment Dialog
Guided interactive modal to register new personnel with multi-angle face scans.
"""

import sys
import logging
from pathlib import Path
from typing import List, Optional, Callable

import cv2
import numpy as np
from PIL import Image
import customtkinter as ctk

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
import config
from ui.themes import glassmorphism as theme

logger = logging.getLogger(__name__)


class EnrollmentDialog(ctk.CTkToplevel):
    """High-aesthetic multi-angle face capture and enrollment dialog."""

    def __init__(
        self,
        master,
        camera_manager,
        detector,
        db_manager,
        recognizer,
        on_enrolled: Optional[Callable[[str], None]] = None,
        **kwargs
    ):
        super().__init__(master, **kwargs)

        self._camera = camera_manager
        self._detector = detector
        self._db = db_manager
        self._recognizer = recognizer
        self._on_enrolled = on_enrolled

        self.title("APEX LAB — PERSONNEL ENROLLMENT")
        self.geometry("680x740")
        self.resizable(False, False)
        self.configure(fg_color=theme.COLOR_BG_ROOT)

        self.transient(master)
        self.grab_set()

        self._captured_encodings: List[np.ndarray] = []
        self._captured_frames: List[np.ndarray] = []
        self._is_running = True

        self._build_ui()
        self._update_preview()

    def _build_ui(self):
        container = ctk.CTkFrame(
            self,
            fg_color=theme.COLOR_BG_PANEL,
            corner_radius=16,
            border_width=1,
            border_color=theme.COLOR_BORDER,
        )
        container.pack(fill="both", expand=True, padx=16, pady=16)

        # Header
        ctk.CTkLabel(
            container,
            text="👤 NEW PERSONNEL REGISTRATION",
            font=theme.get_font(18, "bold"),
            text_color=theme.COLOR_TEXT_PRIMARY,
        ).pack(pady=(16, 4))

        ctk.CTkLabel(
            container,
            text="Capture 3 to 5 face angles (Front, Slight Left, Slight Right, With/Without Glasses).",
            font=theme.get_font(11, "normal"),
            text_color=theme.COLOR_TEXT_SECONDARY,
        ).pack(pady=(0, 12))

        # Inputs Form
        form_frame = ctk.CTkFrame(container, fg_color="transparent")
        form_frame.pack(fill="x", padx=24, pady=4)

        # Name
        ctk.CTkLabel(
            form_frame,
            text="Full Name:",
            font=theme.get_font(12, "bold"),
            text_color=theme.COLOR_TEXT_PRIMARY,
        ).grid(row=0, column=0, sticky="w", padx=6, pady=4)

        self._entry_name = ctk.CTkEntry(
            form_frame,
            placeholder_text="e.g. Dr. Alex Mercer",
            width=260,
            font=theme.get_font(12),
            fg_color=theme.COLOR_BG_CARD,
            border_color=theme.COLOR_BORDER,
        )
        self._entry_name.grid(row=0, column=1, padx=6, pady=4)

        # Role
        ctk.CTkLabel(
            form_frame,
            text="Role / Designation:",
            font=theme.get_font(12, "bold"),
            text_color=theme.COLOR_TEXT_PRIMARY,
        ).grid(row=0, column=2, sticky="w", padx=(16, 6), pady=4)

        self._role_combo = ctk.CTkComboBox(
            form_frame,
            values=["member", "admin", "visitor", "researcher"],
            width=140,
            font=theme.get_font(12),
            fg_color=theme.COLOR_BG_CARD,
            border_color=theme.COLOR_BORDER,
        )
        self._role_combo.set("member")
        self._role_combo.grid(row=0, column=3, padx=6, pady=4)

        # Live Camera Viewport
        self._preview_label = ctk.CTkLabel(
            container,
            text="Initializing Preview...",
            fg_color=theme.COLOR_BG_ROOT,
            corner_radius=12,
            width=500,
            height=340,
        )
        self._preview_label.pack(pady=12)

        # Progress / Angle Count Pill
        self._progress_label = ctk.CTkLabel(
            container,
            text="Scans Captured: 0 / 5  (Minimum 3 required)",
            font=theme.get_font(12, "bold"),
            text_color=theme.COLOR_ACCENT_WARNING,
        )
        self._progress_label.pack(pady=4)

        # Status Message
        self._msg_label = ctk.CTkLabel(
            container,
            text="Center your face inside the frame and press 'Capture Angle'.",
            font=theme.get_font(11, "italic"),
            text_color=theme.COLOR_TEXT_SECONDARY,
        )
        self._msg_label.pack(pady=2)

        # Actions Buttons
        btn_box = ctk.CTkFrame(container, fg_color="transparent")
        btn_box.pack(fill="x", padx=24, pady=(12, 16))

        self._btn_capture = ctk.CTkButton(
            btn_box,
            text="📸 Capture Angle",
            font=theme.get_font(13, "bold"),
            fg_color=theme.COLOR_ACCENT_PRIMARY,
            hover_color="#2563EB",
            corner_radius=8,
            height=38,
            command=self._capture_angle,
        )
        self._btn_capture.pack(side="left", expand=True, fill="x", padx=4)

        self._btn_save = ctk.CTkButton(
            btn_box,
            text="💾 Save & Register",
            font=theme.get_font(13, "bold"),
            fg_color=theme.COLOR_ACCENT_SUCCESS,
            hover_color="#059669",
            state="disabled",
            corner_radius=8,
            height=38,
            command=self._save_person,
        )
        self._btn_save.pack(side="left", expand=True, fill="x", padx=4)

        btn_cancel = ctk.CTkButton(
            btn_box,
            text="Cancel",
            font=theme.get_font(12, "normal"),
            fg_color=theme.COLOR_BG_CARD,
            hover_color=theme.COLOR_BG_CARD_HOVER,
            corner_radius=8,
            height=38,
            width=90,
            command=self._close,
        )
        btn_cancel.pack(side="left", padx=4)

    def _update_preview(self):
        """Draw live preview with detected face box."""
        if not self._is_running:
            return

        ok, frame = self._camera.read_frame()
        if ok and frame is not None:
            display_frame = frame.copy()
            # Fast face detection on half-scale
            small_rgb = cv2.resize(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB), (0, 0), fx=0.5, fy=0.5)
            locations = self._detector.detect_faces(small_rgb)

            # Draw green guide box if face found
            for top, right, bottom, left in locations:
                top, right, bottom, left = top * 2, right * 2, bottom * 2, left * 2
                cv2.rectangle(display_frame, (left, top), (right, bottom), (80, 220, 100), 2)
                cv2.putText(
                    display_frame,
                    "FACE DETECTED",
                    (left, max(20, top - 8)),
                    cv2.FONT_HERSHEY_DUPLEX,
                    0.5,
                    (80, 220, 100),
                    1,
                    cv2.LINE_AA,
                )

            # Resize to fit preview viewport
            rgb_display = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
            h, w, _ = rgb_display.shape
            scale = min(500 / w, 340 / h)
            nw, nh = int(w * scale), int(h * scale)
            resized = cv2.resize(rgb_display, (nw, nh), interpolation=cv2.INTER_LINEAR)
            pil_img = Image.fromarray(resized)
            ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(nw, nh))
            self._preview_label.configure(image=ctk_img, text="")

        self.after(40, self._update_preview)

    def _capture_angle(self):
        """Capture current face frame and extract 128-D encoding."""
        ok, frame = self._camera.read_frame()
        if not ok or frame is None:
            self._msg_label.configure(text="⚠️ Camera read failed. Try again.", text_color=theme.COLOR_ACCENT_DANGER)
            return

        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        locations = self._detector.detect_faces(rgb_frame)

        if not locations:
            self._msg_label.configure(
                text="⚠️ No face detected. Look directly at camera and ensure good lighting.",
                text_color=theme.COLOR_ACCENT_WARNING,
            )
            return

        encodings = self._detector.extract_encodings(rgb_frame, locations)
        if not encodings:
            self._msg_label.configure(text="⚠️ Could not compute face encoding. Please try again.", text_color=theme.COLOR_ACCENT_WARNING)
            return

        # Take first detected face
        self._captured_encodings.append(encodings[0])
        self._captured_frames.append(frame)

        count = len(self._captured_encodings)
        self._progress_label.configure(
            text=f"Scans Captured: {count} / 5  ({'Ready to Save' if count >= 3 else 'Minimum 3 required'})",
            text_color=theme.COLOR_ACCENT_SUCCESS if count >= 3 else theme.COLOR_ACCENT_WARNING,
        )

        self._msg_label.configure(
            text=f"✔ Angle {count} captured successfully! Move slightly for next angle.",
            text_color=theme.COLOR_ACCENT_SUCCESS,
        )

        if count >= 3:
            self._btn_save.configure(state="normal")
        if count >= 5:
            self._btn_capture.configure(state="disabled")

    def _save_person(self):
        """Save person to database and refresh memory cache."""
        name = self._entry_name.get().strip()
        role = self._role_combo.get().strip()

        if not name:
            self._msg_label.configure(text="⚠️ Please enter the person's full name.", text_color=theme.COLOR_ACCENT_DANGER)
            self._entry_name.focus()
            return

        if len(self._captured_encodings) < 1:
            self._msg_label.configure(text="⚠️ At least 1 capture required.", text_color=theme.COLOR_ACCENT_DANGER)
            return

        # Save reference photo
        person_dir = config.KNOWN_FACES_DIR / name.replace(" ", "_").lower()
        person_dir.mkdir(parents=True, exist_ok=True)
        photo_path = str(person_dir / "profile.jpg")
        cv2.imwrite(photo_path, self._captured_frames[0])

        try:
            # Insert person
            person_id = self._db.add_person(name=name, role=role, photo_path=photo_path)

            # Insert encodings
            for enc in self._captured_encodings:
                self._db.add_face_encoding(person_id, enc)

            # Reload recognizer cache
            self._recognizer.reload()

            logger.info("Successfully registered person %s (id=%s) with %d encodings", name, person_id, len(self._captured_encodings))

            if self._on_enrolled:
                self._on_enrolled(name)

            self._close()

        except Exception as e:
            logger.exception("Failed to register person: %s", e)
            self._msg_label.configure(text=f"Database error: {e}", text_color=theme.COLOR_ACCENT_DANGER)

    def _close(self):
        self._is_running = False
        self.grab_release()
        self.destroy()
