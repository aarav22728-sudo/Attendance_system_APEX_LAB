"""
APEX LAB Attendance System — Main Application Window
Coordinates webcam acquisition, face recognition engine,
real-time HUD rendering, and telemetry logging.
"""

import sys
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional

import cv2
import numpy as np
import customtkinter as ctk

# Ensure root package resolution
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config
from ui.themes import glassmorphism as theme
from ui.components.camera_feed import CameraFeedWidget
from ui.components.status_panel import StatusPanel
from ui.components.alert_dialog import AlertDialog
from ui.components.enrollment import EnrollmentDialog

from core.camera import CameraManager
from core.detector import FaceDetector
from core.recognizer import FaceRecognizer
from core.attendance import AttendanceManager
from database.db_manager import DatabaseManager
from reports.excel_generator import WeeklyReportGenerator

logger = logging.getLogger(__name__)

# Optional sound engine
try:
    import pygame
    pygame.mixer.init()
    AUDIO_AVAILABLE = True
except Exception:
    AUDIO_AVAILABLE = False


class AttendanceApp(ctk.CTk):
    """Primary APEX LAB Attendance Kiosk application."""

    def __init__(self):
        super().__init__()

        # Window Configuration
        self.title(config.APP_TITLE)
        self.geometry(f"{config.WINDOW_WIDTH}x{config.WINDOW_HEIGHT}")
        self.minsize(1024, 600)
        self.configure(fg_color=theme.COLOR_BG_ROOT)

        theme.apply_global_theme()

        logger.info("Initializing APEX LAB core subsystems...")

        # Core Subsystems
        self.db = DatabaseManager(config.DATABASE_PATH)
        self.camera = CameraManager(
            camera_index=config.CAMERA_INDEX,
            width=config.CAMERA_WIDTH,
            height=config.CAMERA_HEIGHT,
        )
        self.detector = FaceDetector(model=config.DETECTION_MODEL)
        self.recognizer = FaceRecognizer(self.db)
        self.attendance = AttendanceManager(self.db, self.recognizer)
        self.report_gen = WeeklyReportGenerator(self.db)

        # Preload known face encodings
        enrolled_count = self.recognizer.load_known_faces()
        logger.info("Loaded %d active face encodings into memory.", enrolled_count)

        # Recognition cycle state
        self._frame_count = 0
        self._current_detections: List[Dict[str, Any]] = []
        self._is_active = True
        self._alert_active = False

        # Build UI Layout
        self._build_layout()

        # Start Camera
        if not self.camera.start():
            logger.error("Could not start camera on index %s", config.CAMERA_INDEX)
            self._status_bar_sys.configure(
                text="● CAMERA ERROR — CHECK WEBCAM CONNECTION",
                text_color=theme.COLOR_ACCENT_DANGER,
            )

        # Start loops
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._tick_clock()
        self._video_loop()
        self._refresh_stats()

    # ------------------------------------------------------------------
    # UI Layout Construction
    # ------------------------------------------------------------------
    def _build_layout(self):
        # 1. Main Viewport Container (Split Left / Right)
        content_frame = ctk.CTkFrame(self, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, padx=16, pady=(16, 8))

        # Left Column: Camera Feed Viewport (65%)
        self.camera_widget = CameraFeedWidget(content_frame)
        self.camera_widget.pack(side="left", fill="both", expand=True, padx=(0, 10))

        # Right Column: Analytics & Control Panel (35%)
        self.status_panel = StatusPanel(
            content_frame,
            width=380,
            on_enroll_click=self._open_enrollment,
            on_report_click=self._export_report_now,
        )
        self.status_panel.pack(side="right", fill="both", expand=False)
        self.status_panel.pack_propagate(False)

        # 2. Bottom Glassmorphic Status Bar
        status_bar = ctk.CTkFrame(
            self,
            fg_color=theme.COLOR_BG_PANEL,
            height=36,
            corner_radius=8,
            border_width=1,
            border_color=theme.COLOR_BORDER,
        )
        status_bar.pack(fill="x", padx=16, pady=(0, 10))

        # Status text left: RPi 5 Hardware & Active Status
        self._status_bar_sys = ctk.CTkLabel(
            status_bar,
            text="● RASPBERRY PI 5 — CORE INFERENCE ACTIVE",
            font=theme.get_font(11, "bold"),
            text_color=theme.COLOR_ACCENT_SUCCESS,
        )
        self._status_bar_sys.pack(side="left", padx=14)

        # Notification / Info center
        self._status_bar_info = ctk.CTkLabel(
            status_bar,
            text=f"Database: {self.db.get_person.__name__} ready | Model: {config.DETECTION_MODEL.upper()}",
            font=theme.get_font(11, "normal"),
            text_color=theme.COLOR_TEXT_MUTED,
        )
        self._status_bar_info.pack(side="left", padx=20)

        # Real-time clock right
        self._status_bar_clock = ctk.CTkLabel(
            status_bar,
            text="--:--:--",
            font=theme.get_font(11, "bold"),
            text_color=theme.COLOR_TEXT_PRIMARY,
        )
        self._status_bar_clock.pack(side="right", padx=14)

    # ------------------------------------------------------------------
    # Real-Time Main Processing Loop
    # ------------------------------------------------------------------
    def _video_loop(self):
        """High-efficiency camera acquisition & face recognition cycle."""
        if not self._is_active:
            return

        ok, raw_frame = self.camera.read_frame()

        if ok and raw_frame is not None:
            self._frame_count += 1

            # Run recognition inference every Nth frame for responsiveness
            if self._frame_count % config.RECOGNITION_INTERVAL == 0:
                self._run_recognition_pipeline(raw_frame)

            # Update camera viewport HUD
            # Detection was performed on downscaled frame, so scale back by 1/PROCESS_SCALE
            coord_scale = 1.0 / config.PROCESS_SCALE
            self.camera_widget.render_frame(
                raw_frame,
                self._current_detections,
                coord_scale=coord_scale,
            )

        # Schedule next frame ~30 FPS
        self.after(33, self._video_loop)

    def _run_recognition_pipeline(self, raw_frame: np.ndarray):
        """Downscale frame, detect faces, match encodings, and take action."""
        scale = config.PROCESS_SCALE
        small_frame = cv2.resize(raw_frame, (0, 0), fx=scale, fy=scale, interpolation=cv2.INTER_LINEAR)
        rgb_small = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

        # 1. Detect locations
        face_locations = self.detector.detect_faces(rgb_small)

        if not face_locations:
            self.attendance.reset_unknown_counter()
            self._current_detections = []
            return

        # 2. Extract 128-D encodings
        encodings = self.detector.extract_encodings(rgb_small, face_locations)

        new_detections = []

        for loc, enc in zip(face_locations, encodings):
            person_id, name, confidence = self.recognizer.recognize(enc)

            # Process attendance event
            result = self.attendance.process_recognition(
                person_id=person_id,
                name=name,
                confidence=confidence,
                frame=raw_frame,
            )

            status = result.get("status", "unknown")
            now_str = datetime.now().strftime("%H:%M:%S")

            # Matched person handling
            if person_id is not None:
                role = "member"
                p = self.db.get_person(person_id)
                if p:
                    role = p.role

                # Update status card
                self.status_panel.update_last_recognized(
                    name=name,
                    role=role,
                    timestamp=now_str,
                    confidence=confidence,
                    status=status,
                )

                if status == "checked_in":
                    self.status_panel.add_activity_log(name, now_str, status)
                    self._play_sound("match")
                    self._refresh_stats()

            else:
                # Unknown person detected
                self.status_panel.update_last_recognized(
                    name="Unknown Person",
                    role="Visitor / Unregistered",
                    timestamp=now_str,
                    confidence=confidence,
                    status="unknown",
                )

                # Check if unknown threshold reached & alert should pop
                if result.get("snapshot") and not self._alert_active:
                    self._play_sound("unknown")
                    self._show_unknown_alert(result.get("snapshot"))
                    self._refresh_stats()

            new_detections.append({
                "location": loc,
                "name": name,
                "status": status,
                "confidence": confidence,
            })

        self._current_detections = new_detections

    # ------------------------------------------------------------------
    # Actions & Dialogs
    # ------------------------------------------------------------------
    def _show_unknown_alert(self, snapshot_path: str):
        """Display modal alert for unknown subject."""
        self._alert_active = True

        def on_action(choice: str):
            self._alert_active = False
            if choice == "enroll":
                self._open_enrollment()
            elif choice == "visitor":
                self.status_panel.add_activity_log("Temporary Visitor", datetime.now().strftime("%H:%M:%S"), "warning")

        AlertDialog(self, snapshot_path=snapshot_path, on_action=on_action)

    def _open_enrollment(self):
        """Launch the guided face registration window."""
        def on_enrolled(name: str):
            self._status_bar_info.configure(
                text=f"✔ Registered {name} into APEX LAB database.",
                text_color=theme.COLOR_ACCENT_SUCCESS,
            )
            self._refresh_stats()
            self._play_sound("enrolled")

        EnrollmentDialog(
            self,
            camera_manager=self.camera,
            detector=self.detector,
            db_manager=self.db,
            recognizer=self.recognizer,
            on_enrolled=on_enrolled,
        )

    def _export_report_now(self):
        """Manually trigger weekly Excel report generation."""
        try:
            today = datetime.now().date()
            start_date = (today - timedelta(days=6)).isoformat()
            end_date = today.isoformat()
            # Generate report using WeeklyReportGenerator
            file_path = self.report_gen.generate_report(start_date=start_date, end_date=end_date)
            self._status_bar_info.configure(
                text=f"✔ Weekly Report Exported: {Path(file_path).name}",
                text_color=theme.COLOR_ACCENT_SUCCESS,
            )
            logger.info("Report exported: %s", file_path)
        except Exception as e:
            logger.exception("Error exporting report: %s", e)
            self._status_bar_info.configure(
                text=f"⚠️ Export error: {e}",
                text_color=theme.COLOR_ACCENT_DANGER,
            )

    def _refresh_stats(self):
        """Update telemetry counts from the database."""
        try:
            today_str = datetime.now().date().isoformat()
            stats = self.db.get_daily_stats(today_str)
            self.status_panel.update_stats(
                present=stats["present_count"],
                absent=stats["absent_count"],
                unknown=stats["unknown_count"],
                total=stats["total_enrolled"],
            )
        except Exception as e:
            logger.warning("Could not refresh stats: %s", e)

    def _tick_clock(self):
        """Tick the real-time clock and date display."""
        if not self._is_active:
            return
        now = datetime.now()
        self._status_bar_clock.configure(text=now.strftime("%a %d %b | %I:%M:%S %p"))
        self.after(1000, self._tick_clock)

    def _play_sound(self, sound_type: str):
        """Play feedback sound if audio is enabled."""
        if not config.ENABLE_SOUND or not AUDIO_AVAILABLE:
            return
        try:
            sound_map = {
                "match": config.SOUND_MATCH,
                "unknown": config.SOUND_UNKNOWN,
                "enrolled": config.SOUND_ENROLLED,
            }
            snd_file = sound_map.get(sound_type)
            if snd_file and Path(snd_file).exists():
                pygame.mixer.Sound(str(snd_file)).play()
        except Exception as e:
            logger.debug("Sound play error: %s", e)

    def _on_close(self):
        """Gracefully release hardware and database resources."""
        logger.info("Closing APEX LAB Attendance System...")
        self._is_active = False
        try:
            self.camera.release()
        except Exception:
            pass
        try:
            self.db.close()
        except Exception:
            pass
        self.destroy()
