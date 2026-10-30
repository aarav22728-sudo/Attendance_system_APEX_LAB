"""
APEX LAB Attendance System — Attendance Manager
Processes recognition results and logs check-in events.
"""

import sys
import logging
from datetime import datetime, timedelta
from pathlib import Path

import cv2
import numpy as np

# ---------------------------------------------------------------------------
# Config import
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config

logger = logging.getLogger(__name__)


class AttendanceManager:
    """Track attendance state and log check-in events via the database."""

    def __init__(self, db_manager, recognizer):
        """
        Parameters
        ----------
        db_manager : DatabaseManager
            Provides ``log_attendance()``, ``is_checked_in()``, and
            ``get_today_stats()`` methods.
        recognizer : FaceRecognizer
            (Kept for reference; not called directly by this class.)
        """
        self._db = db_manager
        self._recognizer = recognizer

        # Unknown-person tracking -------------------------------------------
        self._unknown_counter: int = 0

        logger.info("AttendanceManager initialised.")

    # ------------------------------------------------------------------
    # Core workflow
    # ------------------------------------------------------------------
    def process_recognition(
        self,
        person_id: int | None,
        name: str,
        confidence: float,
        frame: np.ndarray,
    ) -> dict:
        """Decide what action to take after a face is recognised.

        Parameters
        ----------
        person_id : int or None
            Database ID of the recognised person, or ``None`` for unknown.
        name : str
            Display name (``"Unknown"`` when *person_id* is ``None``).
        confidence : float
            Recognition confidence in ``[0, 1]``.
        frame : numpy.ndarray
            Current camera frame (BGR) — used for snapshot capture.

        Returns
        -------
        dict with at least a ``"status"`` key:
            * ``"checked_in"`` — attendance logged successfully.
            * ``"already_in"`` — person already checked in within the
              duplicate window.
            * ``"unknown"`` — face not recognised.
        """
        now = datetime.now()

        # ----- Known person -------------------------------------------------
        if person_id is not None:
            # Reset unknown streak whenever a known face appears
            self._unknown_counter = 0

            if self._is_duplicate(person_id, now):
                logger.debug(
                    "%s (id=%s) already checked in within %d min window.",
                    name, person_id, config.DUPLICATE_WINDOW_MINUTES,
                )
                return {
                    "status": "already_in",
                    "name": name,
                    "person_id": person_id,
                    "confidence": confidence,
                }

            # Log new check-in
            self._db.log_attendance(
                person_id=person_id,
                confidence=confidence,
                snapshot_path=None,
                status="present",
            )
            logger.info(
                "CHECK-IN: %s (id=%s) at %s (confidence=%.4f)",
                name, person_id, now.strftime("%H:%M:%S"), confidence,
            )
            return {
                "status": "checked_in",
                "name": name,
                "person_id": person_id,
                "time": now.strftime("%H:%M:%S"),
                "confidence": confidence,
            }

        # ----- Unknown person -----------------------------------------------
        self._unknown_counter += 1
        logger.debug("Unknown counter: %d", self._unknown_counter)

        result: dict = {
            "status": "unknown",
            "unknown_count": self._unknown_counter,
            "confidence": confidence,
        }

        if self._unknown_counter >= config.CONSECUTIVE_UNKNOWN_THRESHOLD:
            snapshot_path = self.capture_snapshot(frame, prefix="unknown")
            result["snapshot"] = snapshot_path
            try:
                self._db.log_attendance(
                    person_id=None,
                    confidence=confidence,
                    snapshot_path=snapshot_path,
                    status="unknown",
                )
            except Exception:
                logger.exception("Failed to log unknown face to database.")
            logger.info(
                "Unknown threshold reached (%d) — snapshot saved: %s",
                self._unknown_counter, snapshot_path,
            )
            # Reset so we don't flood with snapshots
            self._unknown_counter = 0

        return result

    # ------------------------------------------------------------------
    # Snapshot capture
    # ------------------------------------------------------------------
    def capture_snapshot(
        self,
        frame: np.ndarray,
        prefix: str = "unknown",
    ) -> str:
        """Save a snapshot of the current frame to the unknown captures dir.

        Parameters
        ----------
        frame : numpy.ndarray
            BGR image from the camera.
        prefix : str
            Filename prefix (e.g. ``"unknown"``).

        Returns
        -------
        Absolute path of the saved image file.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"{prefix}_{timestamp}.jpg"
        save_path = config.UNKNOWN_CAPTURES_DIR / filename

        config.UNKNOWN_CAPTURES_DIR.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(save_path), frame)
        logger.debug("Snapshot saved: %s", save_path)
        return str(save_path)

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------
    def get_today_stats(self) -> dict:
        """Return summary statistics for today's attendance.

        Returns
        -------
        dict with keys: present_count, absent_count, unknown_count, total_enrolled
        """
        try:
            today_str = datetime.now().date().isoformat()
            return self._db.get_daily_stats(today_str)
        except Exception:
            logger.exception("Failed to retrieve today's stats.")
            return {
                "present_count": 0,
                "absent_count": 0,
                "unknown_count": 0,
                "total_enrolled": 0,
                "error": True,
            }

    # ------------------------------------------------------------------
    # Unknown counter management
    # ------------------------------------------------------------------
    def reset_unknown_counter(self) -> None:
        """Reset the consecutive-unknown-frame counter.

        Call this when the unknown person leaves the frame so that a fresh
        streak starts on the next unknown appearance.
        """
        if self._unknown_counter > 0:
            logger.debug(
                "Unknown counter reset (was %d).", self._unknown_counter
            )
        self._unknown_counter = 0

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _is_duplicate(self, person_id: int, now: datetime) -> bool:
        """Check whether *person_id* has already checked in within the
        duplicate window defined by ``config.DUPLICATE_WINDOW_MINUTES``.
        """
        try:
            return self._db.is_already_checked_in(
                person_id, window_minutes=config.DUPLICATE_WINDOW_MINUTES
            )
        except Exception:
            logger.exception(
                "Error checking duplicate status for person_id=%s.", person_id
            )
            # Fail-safe: treat as duplicate to avoid spamming entries
            return True
