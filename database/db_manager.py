"""
APEX LAB Attendance System — Database Manager

Thread-safe SQLite wrapper that handles all CRUD operations for persons,
face-encodings, and attendance records.
"""

from __future__ import annotations

import datetime
import logging
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config

import numpy as np

from database.models import AttendanceRecord, FaceEncoding, Person

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Central gateway to the APEX LAB SQLite database.

    * Uses ``check_same_thread=False`` so the connection can be shared across
      threads (required for the GUI + camera pipeline).
    * Provides a ``connection()`` context-manager for transactional safety.
    """

    def __init__(self, db_path: Optional[str] = None) -> None:
        self.db_path: str = db_path or config.DATABASE_PATH
        self._lock = threading.Lock()

        # Ensure the parent directory exists
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")

        self.create_tables()
        logger.info("DatabaseManager initialised — %s", self.db_path)

    # ------------------------------------------------------------------
    # Context-manager helper
    # ------------------------------------------------------------------
    @contextmanager
    def connection(self):
        """Yield the shared connection inside a thread-lock.

        Commits on success, rolls back on exception.
        """
        with self._lock:
            try:
                yield self._conn
                self._conn.commit()
            except Exception:
                self._conn.rollback()
                raise

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------
    def create_tables(self) -> None:
        """Create the core tables if they do not already exist."""
        with self.connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS persons (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    name        TEXT    NOT NULL,
                    role        TEXT    NOT NULL DEFAULT 'member',
                    enrolled_at TEXT    NOT NULL,
                    photo_path  TEXT,
                    is_active   INTEGER NOT NULL DEFAULT 1
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS face_encodings (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    person_id   INTEGER NOT NULL,
                    encoding    BLOB    NOT NULL,
                    captured_at TEXT    NOT NULL,
                    FOREIGN KEY (person_id) REFERENCES persons(id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS attendance_log (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    person_id     INTEGER,
                    timestamp     TEXT    NOT NULL,
                    status        TEXT    NOT NULL DEFAULT 'present',
                    confidence    REAL    NOT NULL DEFAULT 0.0,
                    snapshot_path TEXT,
                    FOREIGN KEY (person_id) REFERENCES persons(id)
                )
                """
            )
        logger.debug("Tables verified / created.")

    # ------------------------------------------------------------------
    # Person CRUD
    # ------------------------------------------------------------------
    def add_person(self, name: str, role: str = "member", photo_path: Optional[str] = None) -> int:
        """Insert a new person and return their ``person_id``."""
        enrolled_at = datetime.datetime.now().isoformat()
        with self.connection() as conn:
            cursor = conn.execute(
                "INSERT INTO persons (name, role, enrolled_at, photo_path) VALUES (?, ?, ?, ?)",
                (name, role, enrolled_at, photo_path),
            )
            person_id = cursor.lastrowid
        logger.info("Added person '%s' (id=%d, role=%s)", name, person_id, role)
        return person_id

    def get_person(self, person_id: int) -> Optional[Person]:
        """Return a single Person by id, or ``None`` if not found."""
        with self.connection() as conn:
            row = conn.execute(
                "SELECT id, name, role, enrolled_at, photo_path, is_active FROM persons WHERE id = ?",
                (person_id,),
            ).fetchone()
        if row is None:
            return None
        return Person.from_row(row)

    def get_all_persons(self, active_only: bool = True) -> List[Person]:
        """Return all persons, optionally filtered to active-only."""
        query = "SELECT id, name, role, enrolled_at, photo_path, is_active FROM persons"
        if active_only:
            query += " WHERE is_active = 1"
        query += " ORDER BY name"

        with self.connection() as conn:
            rows = conn.execute(query).fetchall()
        return [Person.from_row(r) for r in rows]

    def delete_person(self, person_id: int) -> None:
        """Soft-delete a person by setting ``is_active = 0``."""
        with self.connection() as conn:
            conn.execute("UPDATE persons SET is_active = 0 WHERE id = ?", (person_id,))
        logger.info("Soft-deleted person id=%d", person_id)

    # ------------------------------------------------------------------
    # Face Encodings
    # ------------------------------------------------------------------
    def add_face_encoding(self, person_id: int, encoding_array: np.ndarray) -> int:
        """Store a face-encoding blob linked to *person_id*."""
        captured_at = datetime.datetime.now().isoformat()
        blob = encoding_array.astype(np.float64).tobytes()
        with self.connection() as conn:
            cursor = conn.execute(
                "INSERT INTO face_encodings (person_id, encoding, captured_at) VALUES (?, ?, ?)",
                (person_id, blob, captured_at),
            )
            enc_id = cursor.lastrowid
        logger.debug("Stored encoding id=%d for person_id=%d", enc_id, person_id)
        return enc_id

    def get_all_encodings(self) -> List[Tuple[int, str, np.ndarray]]:
        """Return ``[(person_id, name, encoding_array), ...]`` for active persons."""
        with self.connection() as conn:
            rows = conn.execute(
                """
                SELECT fe.person_id, p.name, fe.encoding
                FROM face_encodings fe
                JOIN persons p ON p.id = fe.person_id
                WHERE p.is_active = 1
                """
            ).fetchall()

        results: List[Tuple[int, str, np.ndarray]] = []
        for person_id, name, blob in rows:
            arr = np.frombuffer(blob, dtype=np.float64)
            results.append((person_id, name, arr))
        return results

    # ------------------------------------------------------------------
    # Attendance
    # ------------------------------------------------------------------
    def log_attendance(
        self,
        person_id: Optional[int],
        confidence: float = 0.0,
        snapshot_path: Optional[str] = None,
        status: str = "present",
    ) -> int:
        """Insert an attendance record and return its id."""
        ts = datetime.datetime.now().isoformat()
        with self.connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO attendance_log (person_id, timestamp, status, confidence, snapshot_path)
                VALUES (?, ?, ?, ?, ?)
                """,
                (person_id, ts, status, confidence, snapshot_path),
            )
            record_id = cursor.lastrowid
        logger.info(
            "Logged attendance id=%d person_id=%s status=%s conf=%.2f",
            record_id,
            person_id,
            status,
            confidence,
        )
        return record_id

    def is_already_checked_in(self, person_id: int, window_minutes: int = 30) -> bool:
        """Return ``True`` if *person_id* has a 'present' record within the last
        *window_minutes* minutes.
        """
        cutoff = (
            datetime.datetime.now() - datetime.timedelta(minutes=window_minutes)
        ).isoformat()
        with self.connection() as conn:
            row = conn.execute(
                """
                SELECT COUNT(*) FROM attendance_log
                WHERE person_id = ? AND status = 'present' AND timestamp >= ?
                """,
                (person_id, cutoff),
            ).fetchone()
        return row[0] > 0

    def get_attendance_for_week(
        self, start_date: str, end_date: str
    ) -> List[AttendanceRecord]:
        """Return attendance records whose timestamp falls within
        [*start_date*, *end_date*] (inclusive, ISO-8601 date strings).
        """
        with self.connection() as conn:
            rows = conn.execute(
                """
                SELECT id, person_id, timestamp, status, confidence, snapshot_path
                FROM attendance_log
                WHERE date(timestamp) BETWEEN date(?) AND date(?)
                ORDER BY timestamp
                """,
                (start_date, end_date),
            ).fetchall()
        return [AttendanceRecord.from_row(r) for r in rows]

    def get_unknown_entries(
        self, start_date: str, end_date: str
    ) -> List[AttendanceRecord]:
        """Return attendance records with status 'unknown' in the given date range."""
        with self.connection() as conn:
            rows = conn.execute(
                """
                SELECT id, person_id, timestamp, status, confidence, snapshot_path
                FROM attendance_log
                WHERE status = 'unknown' AND date(timestamp) BETWEEN date(?) AND date(?)
                ORDER BY timestamp
                """,
                (start_date, end_date),
            ).fetchall()
        return [AttendanceRecord.from_row(r) for r in rows]

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------
    def get_daily_stats(self, date: str) -> Dict[str, int]:
        """Return a summary dict for the given *date* (ISO-8601 date string).

        Keys: ``present_count``, ``absent_count``, ``unknown_count``,
        ``total_enrolled``.
        """
        with self.connection() as conn:
            # Total active persons
            total_enrolled = conn.execute(
                "SELECT COUNT(*) FROM persons WHERE is_active = 1"
            ).fetchone()[0]

            # Distinct persons marked present on this date
            present_count = conn.execute(
                """
                SELECT COUNT(DISTINCT person_id) FROM attendance_log
                WHERE status = 'present' AND date(timestamp) = date(?)
                """,
                (date,),
            ).fetchone()[0]

            # Unknown entries on this date
            unknown_count = conn.execute(
                """
                SELECT COUNT(*) FROM attendance_log
                WHERE status = 'unknown' AND date(timestamp) = date(?)
                """,
                (date,),
            ).fetchone()[0]

        absent_count = max(0, total_enrolled - present_count)

        stats = {
            "present_count": present_count,
            "absent_count": absent_count,
            "unknown_count": unknown_count,
            "total_enrolled": total_enrolled,
        }
        logger.debug("Daily stats for %s: %s", date, stats)
        return stats

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------
    def close(self) -> None:
        """Close the underlying SQLite connection."""
        self._conn.close()
        logger.info("Database connection closed.")
