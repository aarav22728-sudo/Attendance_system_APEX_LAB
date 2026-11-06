"""Audit log: records important actions (startup, enrollments, admin access)
in the same SQLite database, so you can see who did what and when."""

import logging
import sqlite3
import threading
from datetime import datetime
from typing import List, Optional, Tuple

import config

logger = logging.getLogger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS audit_log (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    actor     TEXT NOT NULL,
    action    TEXT NOT NULL,
    details   TEXT
)
"""


class AuditLog:
    def __init__(self, db_path: Optional[str] = None):
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(str(db_path or config.DATABASE_PATH), check_same_thread=False)
        with self._lock:
            self._conn.execute(_SCHEMA)
            self._conn.commit()

    def record(self, action: str, details: str = "", actor: str = "system") -> None:
        """Add one audit entry. Never raises, so an audit problem cannot stop the kiosk."""
        try:
            with self._lock:
                self._conn.execute(
                    "INSERT INTO audit_log (timestamp, actor, action, details) VALUES (?, ?, ?, ?)",
                    (datetime.now().isoformat(timespec="seconds"), actor, action, details),
                )
                self._conn.commit()
        except Exception:
            logger.exception("Could not write audit entry: %s", action)

    def recent(self, limit: int = 50) -> List[Tuple]:
        with self._lock:
            return self._conn.execute(
                "SELECT timestamp, actor, action, details FROM audit_log ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
