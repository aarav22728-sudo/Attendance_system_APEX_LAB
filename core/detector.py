"""
APEX LAB Attendance System — Face Detector
Wraps the *face_recognition* library for detection and encoding extraction.
"""

import sys
import logging
from pathlib import Path

import numpy as np
import face_recognition

# ---------------------------------------------------------------------------
# Config import
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config

logger = logging.getLogger(__name__)


class FaceDetector:
    """Detect faces and extract 128-D encodings from RGB frames."""

    def __init__(self, model: str = config.DETECTION_MODEL):
        """
        Parameters
        ----------
        model : str
            Detection model — ``"hog"`` (fast, CPU-only) or ``"cnn"``
            (more accurate, requires GPU / dlib CUDA build).
        """
        if model not in ("hog", "cnn"):
            raise ValueError(f"Invalid detection model: {model!r}. Use 'hog' or 'cnn'.")
        self._model = model
        logger.info("FaceDetector initialised (model=%s, min_face_size=%s)",
                     model, config.MIN_FACE_SIZE)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def detect_faces(self, rgb_frame: np.ndarray) -> list[tuple[int, int, int, int]]:
        """Detect face locations in an RGB frame.

        Parameters
        ----------
        rgb_frame : numpy.ndarray
            Image in RGB colour order.

        Returns
        -------
        list of (top, right, bottom, left) tuples — one per detected face.
        Faces smaller than ``config.MIN_FACE_SIZE`` are filtered out.
        """
        if rgb_frame is None or rgb_frame.size == 0:
            logger.debug("detect_faces called with empty frame.")
            return []

        locations = face_recognition.face_locations(rgb_frame, model=self._model)
        filtered = self._filter_small_faces(locations)

        logger.debug(
            "Detected %d face(s), %d after size filter.",
            len(locations), len(filtered),
        )
        return filtered

    def extract_encodings(
        self,
        rgb_frame: np.ndarray,
        face_locations: list[tuple[int, int, int, int]],
    ) -> list[np.ndarray]:
        """Extract 128-D face encodings for the given face locations.

        Parameters
        ----------
        rgb_frame : numpy.ndarray
            Image in RGB colour order.
        face_locations : list
            Locations returned by :meth:`detect_faces`.

        Returns
        -------
        list of numpy.ndarray, each of shape ``(128,)``.
        """
        if not face_locations:
            return []

        encodings = face_recognition.face_encodings(rgb_frame, face_locations)
        logger.debug("Extracted %d encoding(s).", len(encodings))
        return encodings

    def detect_and_encode(
        self, rgb_frame: np.ndarray,
    ) -> list[tuple[tuple[int, int, int, int], np.ndarray]]:
        """Detect faces and return ``(location, encoding)`` pairs.

        Convenience method combining :meth:`detect_faces` and
        :meth:`extract_encodings`.

        Returns
        -------
        list of (face_location, encoding) tuples.
        """
        locations = self.detect_faces(rgb_frame)
        if not locations:
            return []

        encodings = self.extract_encodings(rgb_frame, locations)

        # Pair only where both location and encoding exist
        pairs = list(zip(locations, encodings))
        logger.debug("detect_and_encode produced %d pair(s).", len(pairs))
        return pairs

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _filter_small_faces(
        self, locations: list[tuple[int, int, int, int]],
    ) -> list[tuple[int, int, int, int]]:
        """Remove faces whose bounding box is smaller than MIN_FACE_SIZE."""
        min_size = config.MIN_FACE_SIZE
        result: list[tuple[int, int, int, int]] = []
        for top, right, bottom, left in locations:
            width = right - left
            height = bottom - top
            if width >= min_size and height >= min_size:
                result.append((top, right, bottom, left))
            else:
                logger.debug(
                    "Filtered tiny face (%dx%d) at (%d,%d).",
                    width, height, left, top,
                )
        return result
