"""
APEX LAB Attendance System — Camera Manager
Handles camera capture with a background thread for responsive frame access.
"""

import sys
import logging
import threading
import time
from pathlib import Path

import cv2
import numpy as np

# ---------------------------------------------------------------------------
# Config import (project root may not be on sys.path yet)
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config

logger = logging.getLogger(__name__)


class CameraManager:
    """Thread-safe camera wrapper with continuous background capture."""

    def __init__(
        self,
        camera_index: int = config.CAMERA_INDEX,
        width: int = config.CAMERA_WIDTH,
        height: int = config.CAMERA_HEIGHT,
    ):
        self._camera_index = camera_index
        self._width = width
        self._height = height

        self._cap: cv2.VideoCapture | None = None
        self._frame: np.ndarray | None = None
        self._lock = threading.Lock()
        self._running = False
        self._thread: threading.Thread | None = None

        logger.info(
            "CameraManager initialised (index=%s, %sx%s)",
            camera_index, width, height,
        )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def start(self) -> bool:
        """Open the camera and start the background capture thread."""
        if self._running:
            logger.warning("Camera is already running.")
            return True

        self._cap = cv2.VideoCapture(self._camera_index)
        if not self._cap.isOpened():
            logger.error("Failed to open camera index %s", self._camera_index)
            return False

        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self._width)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self._height)
        self._cap.set(cv2.CAP_PROP_FPS, config.CAMERA_FPS)

        self._running = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()
        logger.info("Camera started — background capture thread running.")
        return True

    def release(self) -> None:
        """Stop the background thread and release the camera."""
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=3.0)
            self._thread = None
        if self._cap is not None:
            self._cap.release()
            self._cap = None
        with self._lock:
            self._frame = None
        logger.info("Camera released.")

    def is_opened(self) -> bool:
        """Return True if the camera device is currently open."""
        return self._cap is not None and self._cap.isOpened()

    # ------------------------------------------------------------------
    # Frame access
    # ------------------------------------------------------------------
    def read_frame(self) -> tuple[bool, np.ndarray | None]:
        """Return the latest frame captured by the background thread.

        Returns
        -------
        (success, frame) — *frame* is a BGR numpy array or ``None``.
        """
        with self._lock:
            if self._frame is None:
                return False, None
            return True, self._frame.copy()

    def get_processed_frame(self) -> np.ndarray | None:
        """Return a downscaled RGB frame suitable for face processing.

        The frame is resized by ``config.PROCESS_SCALE`` and converted from
        BGR to RGB (as required by the *face_recognition* library).
        """
        ok, frame = self.read_frame()
        if not ok or frame is None:
            return None

        scale = config.PROCESS_SCALE
        small = cv2.resize(
            frame,
            (0, 0),
            fx=scale,
            fy=scale,
            interpolation=cv2.INTER_LINEAR,
        )
        rgb = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
        return rgb

    def get_display_frame(self) -> np.ndarray | None:
        """Return the frame at display resolution (config.DISPLAY_SCALE)."""
        ok, frame = self.read_frame()
        if not ok or frame is None:
            return None

        scale = config.DISPLAY_SCALE
        if scale == 1.0:
            return frame

        display = cv2.resize(
            frame,
            (0, 0),
            fx=scale,
            fy=scale,
            interpolation=cv2.INTER_LINEAR,
        )
        return display

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------
    def _capture_loop(self) -> None:
        """Continuously grab frames in the background."""
        logger.debug("Capture loop started.")
        while self._running:
            if self._cap is None or not self._cap.isOpened():
                time.sleep(0.01)
                continue

            ret, frame = self._cap.read()
            if not ret:
                logger.warning("Failed to read frame from camera.")
                time.sleep(0.01)
                continue

            with self._lock:
                self._frame = frame

        logger.debug("Capture loop stopped.")
