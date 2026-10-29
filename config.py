"""
APEX LAB Attendance System — Configuration
All tuneable constants live here. Adjust for your environment.
"""

import os
from pathlib import Path

# ──────────────────────────────────────────────
# Paths
# ──────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "database" / "apex_lab.db"
KNOWN_FACES_DIR = BASE_DIR / "data" / "known_faces"
UNKNOWN_CAPTURES_DIR = BASE_DIR / "data" / "unknown_captures"
ENCODINGS_CACHE_PATH = BASE_DIR / "data" / "encodings_cache.pkl"
REPORTS_DIR = BASE_DIR / "reports" / "exports"

# Ensure directories exist
for _dir in [KNOWN_FACES_DIR, UNKNOWN_CAPTURES_DIR, REPORTS_DIR]:
    _dir.mkdir(parents=True, exist_ok=True)

# ──────────────────────────────────────────────
# Camera
# ──────────────────────────────────────────────
CAMERA_INDEX = 0                  # USB webcam index (0 = default)
CAMERA_WIDTH = 640                # Capture width
CAMERA_HEIGHT = 480               # Capture height
CAMERA_FPS = 30                   # Requested FPS from webcam
PROCESS_SCALE = 0.5               # Downscale factor for face processing
DISPLAY_SCALE = 1.0               # Display scale (1.0 = full capture res)

# ──────────────────────────────────────────────
# Face Detection & Recognition
# ──────────────────────────────────────────────
DETECTION_MODEL = "hog"           # "hog" (fast, CPU) or "cnn" (accurate, GPU)
MATCH_TOLERANCE = 0.45            # Lower = stricter matching (0.0–1.0)
MIN_FACE_SIZE = 40                # Minimum face size in pixels to consider
CONSECUTIVE_UNKNOWN_THRESHOLD = 3 # Frames before triggering unknown alert
ENCODINGS_PER_PERSON = 5          # Recommended captures during enrollment
RECOGNITION_INTERVAL = 3          # Process every Nth frame for recognition

# ──────────────────────────────────────────────
# Attendance Rules
# ──────────────────────────────────────────────
DUPLICATE_WINDOW_MINUTES = 30     # Minutes before same person can re-check-in
EXPECTED_CHECKIN_TIME = "09:00"   # HH:MM — for late arrival tracking
WORK_DAYS = [0, 1, 2, 3, 4]      # Monday=0 through Friday=4
ABSENT_FLAG_DAYS = 3              # Flag person missing this many consecutive days

# ──────────────────────────────────────────────
# Excel Reports
# ──────────────────────────────────────────────
REPORT_DAY = "sunday"             # Day to auto-generate weekly report
REPORT_TIME = "23:59"             # Time to generate report
REPORT_FILENAME_FORMAT = "APEX_LAB_attendance_{start}_{end}.xlsx"

# ──────────────────────────────────────────────
# UI
# ──────────────────────────────────────────────
APP_TITLE = "APEX LAB — Attendance System"
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720
THEME_MODE = "dark"               # "dark" or "light"
ACCENT_COLOR_MATCH = "#00E676"    # Green — successful match
ACCENT_COLOR_PROCESSING = "#FFB300"  # Amber — processing
ACCENT_COLOR_UNKNOWN = "#FF1744"  # Red — unknown person
ACCENT_COLOR_PRIMARY = "#448AFF"  # Blue — primary accent
BG_COLOR_DARK = "#1A1A2E"         # Deep dark blue-black
BG_COLOR_PANEL = "#16213E"        # Panel background
BG_COLOR_CARD = "#0F3460"         # Card background
TEXT_COLOR_PRIMARY = "#E8E8E8"    # Main text
TEXT_COLOR_SECONDARY = "#A0A0B0"  # Secondary text

# ──────────────────────────────────────────────
# Audio
# ──────────────────────────────────────────────
ENABLE_SOUND = True
SOUND_MATCH = BASE_DIR / "assets" / "sounds" / "match.wav"
SOUND_UNKNOWN = BASE_DIR / "assets" / "sounds" / "unknown.wav"
SOUND_ENROLLED = BASE_DIR / "assets" / "sounds" / "enrolled.wav"

# ──────────────────────────────────────────────
# Logging
# ──────────────────────────────────────────────
LOG_LEVEL = "INFO"
LOG_FILE = BASE_DIR / "logs" / "apex_lab.log"
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
