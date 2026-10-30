"""
APEX LAB Attendance System — Face Recognizer
Matches incoming face encodings against a cached database of known faces.
"""

import sys
import logging
import pickle
from pathlib import Path

import numpy as np
import face_recognition

# ---------------------------------------------------------------------------
# Config import
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config

logger = logging.getLogger(__name__)


class FaceRecognizer:
    """Compare face encodings against known faces stored in the database."""

    def __init__(self, db_manager):
        """
        Parameters
        ----------
        db_manager : DatabaseManager
            An instance that provides ``get_all_encodings()`` returning a list
            of ``(person_id, name, encoding_blob)`` tuples.
        """
        self._db = db_manager

        # In-memory cache ---------------------------------------------------
        self._person_ids: list[int] = []
        self._names: list[str] = []
        self._encodings: np.ndarray | None = None  # shape (N, 128)

        logger.info("FaceRecognizer initialised.")

    # ------------------------------------------------------------------
    # Loading known faces
    # ------------------------------------------------------------------
    def load_known_faces(self) -> int:
        """Load all face encodings from the database into memory.

        Returns the number of encodings loaded.
        """
        # Try the on-disk pickle cache first for faster startup
        if self._load_cache():
            logger.info(
                "Loaded %d encoding(s) from cache file.", len(self._person_ids)
            )
            return len(self._person_ids)

        return self._load_from_db()

    def reload(self) -> int:
        """Refresh in-memory encodings from the database (ignores cache).

        Returns the number of encodings loaded.
        """
        count = self._load_from_db()
        self.save_cache()
        return count

    # ------------------------------------------------------------------
    # Recognition
    # ------------------------------------------------------------------
    def recognize(
        self, face_encoding: np.ndarray,
    ) -> tuple[int | None, str, float]:
        """Identify a single face encoding.

        Parameters
        ----------
        face_encoding : numpy.ndarray
            A 128-D face encoding.

        Returns
        -------
        (person_id, name, confidence)
            ``person_id`` is ``None`` and ``name`` is ``"Unknown"`` when no
            match is found within ``config.MATCH_TOLERANCE``.
            ``confidence`` is ``1.0 - distance`` for the best match.
        """
        if self._encodings is None or len(self._encodings) == 0:
            logger.debug("No known encodings to compare against.")
            return None, "Unknown", 0.0

        distances = face_recognition.face_distance(self._encodings, face_encoding)
        best_idx = int(np.argmin(distances))
        best_distance = float(distances[best_idx])
        confidence = round(1.0 - best_distance, 4)

        if best_distance < config.MATCH_TOLERANCE:
            person_id = self._person_ids[best_idx]
            name = self._names[best_idx]
            logger.debug(
                "Match: %s (id=%s) distance=%.4f confidence=%.4f",
                name, person_id, best_distance, confidence,
            )
            return person_id, name, confidence

        logger.debug(
            "No match — best distance %.4f exceeds tolerance %.2f.",
            best_distance, config.MATCH_TOLERANCE,
        )
        return None, "Unknown", confidence

    def recognize_multiple(
        self, face_encodings: list[np.ndarray],
    ) -> list[tuple[int | None, str, float]]:
        """Identify multiple face encodings.

        Returns a list of ``(person_id, name, confidence)`` tuples, one per
        input encoding.
        """
        return [self.recognize(enc) for enc in face_encodings]

    # ------------------------------------------------------------------
    # Cache persistence
    # ------------------------------------------------------------------
    def save_cache(self) -> bool:
        """Pickle the current in-memory encodings to disk for fast reload."""
        cache_path: Path = config.ENCODINGS_CACHE_PATH
        try:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "person_ids": self._person_ids,
                "names": self._names,
                "encodings": self._encodings,
            }
            with open(cache_path, "wb") as fh:
                pickle.dump(data, fh, protocol=pickle.HIGHEST_PROTOCOL)
            logger.info("Encodings cache saved to %s", cache_path)
            return True
        except Exception:
            logger.exception("Failed to save encodings cache.")
            return False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _load_cache(self) -> bool:
        """Attempt to load encodings from the pickle cache file."""
        cache_path: Path = config.ENCODINGS_CACHE_PATH
        if not cache_path.exists():
            return False

        try:
            with open(cache_path, "rb") as fh:
                data = pickle.load(fh)  # noqa: S301 — trusted local cache
            self._person_ids = data["person_ids"]
            self._names = data["names"]
            self._encodings = data["encodings"]
            return True
        except Exception:
            logger.exception("Failed to load encodings cache; will reload from DB.")
            return False

    def load_cache(self) -> bool:
        """Public wrapper to load from pickle cache. Returns True on success."""
        return self._load_cache()

    def _load_from_db(self) -> int:
        """Load encodings from the database via ``db_manager``."""
        rows = self._db.get_all_encodings()  # [(person_id, name, blob), ...]

        person_ids: list[int] = []
        names: list[str] = []
        encodings: list[np.ndarray] = []

        for person_id, name, blob in rows:
            try:
                enc = np.frombuffer(blob, dtype=np.float64)
                if enc.shape != (128,):
                    logger.warning(
                        "Skipping malformed encoding for %s (id=%s): shape=%s",
                        name, person_id, enc.shape,
                    )
                    continue
                person_ids.append(person_id)
                names.append(name)
                encodings.append(enc)
            except Exception:
                logger.exception(
                    "Error decoding blob for %s (id=%s).", name, person_id
                )

        self._person_ids = person_ids
        self._names = names
        self._encodings = np.array(encodings) if encodings else np.empty((0, 128))

        logger.info("Loaded %d encoding(s) from database.", len(person_ids))
        return len(person_ids)
