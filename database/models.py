"""
APEX LAB Attendance System — Data Models

Dataclass definitions for Person, FaceEncoding, and AttendanceRecord.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field, asdict
from typing import Optional

import numpy as np


# ---------------------------------------------------------------------------
# Person
# ---------------------------------------------------------------------------
@dataclass
class Person:
    """Represents a registered individual (admin, member, or visitor)."""

    id: int
    name: str
    role: str  # "admin" | "member" | "visitor"
    enrolled_at: str  # ISO-8601 timestamp string
    photo_path: Optional[str] = None
    is_active: bool = True

    # -- helpers -------------------------------------------------------------
    def to_dict(self) -> dict:
        """Return a plain-dict representation of this Person."""
        return asdict(self)

    @classmethod
    def from_row(cls, row: tuple) -> Person:
        """Build a Person from a SQLite row tuple.

        Expected column order:
            id, name, role, enrolled_at, photo_path, is_active
        """
        return cls(
            id=row[0],
            name=row[1],
            role=row[2],
            enrolled_at=row[3],
            photo_path=row[4],
            is_active=bool(row[5]),
        )


# ---------------------------------------------------------------------------
# FaceEncoding
# ---------------------------------------------------------------------------
@dataclass
class FaceEncoding:
    """A 128-d face-recognition encoding linked to a Person."""

    id: int
    person_id: int
    encoding: np.ndarray  # 128-d float64 vector
    captured_at: str  # ISO-8601 timestamp string

    # -- helpers -------------------------------------------------------------
    def to_dict(self) -> dict:
        """Return a plain-dict representation (encoding → list)."""
        d = asdict(self)
        # numpy arrays are not JSON-serialisable; convert to list
        d["encoding"] = self.encoding.tolist()
        return d

    @classmethod
    def from_row(cls, row: tuple) -> FaceEncoding:
        """Build a FaceEncoding from a SQLite row tuple.

        Expected column order:
            id, person_id, encoding_blob, captured_at
        """
        return cls(
            id=row[0],
            person_id=row[1],
            encoding=np.frombuffer(row[2], dtype=np.float64),
            captured_at=row[3],
        )


# ---------------------------------------------------------------------------
# AttendanceRecord
# ---------------------------------------------------------------------------
@dataclass
class AttendanceRecord:
    """A single attendance log entry."""

    id: int
    person_id: Optional[int]  # None for unknown faces
    timestamp: str  # ISO-8601 timestamp string
    status: str  # "present" | "unknown" | "flagged"
    confidence: float = 0.0
    snapshot_path: Optional[str] = None

    # -- helpers -------------------------------------------------------------
    def to_dict(self) -> dict:
        """Return a plain-dict representation of this AttendanceRecord."""
        return asdict(self)

    @classmethod
    def from_row(cls, row: tuple) -> AttendanceRecord:
        """Build an AttendanceRecord from a SQLite row tuple.

        Expected column order:
            id, person_id, timestamp, status, confidence, snapshot_path
        """
        return cls(
            id=row[0],
            person_id=row[1],
            timestamp=row[2],
            status=row[3],
            confidence=row[4],
            snapshot_path=row[5],
        )
