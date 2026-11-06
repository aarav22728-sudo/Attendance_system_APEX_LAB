"""Keeps unknown-face snapshots within a retention period and a size limit."""

import logging
from datetime import datetime, timedelta
from pathlib import Path

import config

logger = logging.getLogger(__name__)


def enforce_snapshot_policy() -> dict:
    """Delete snapshots older than the retention period, then the oldest
    ones until the folder is under the size limit."""
    folder = Path(config.UNKNOWN_CAPTURES_DIR)
    if not folder.exists():
        return {"deleted": 0, "size_mb": 0.0}

    cutoff = datetime.now() - timedelta(days=config.UNKNOWN_RETENTION_DAYS)
    files = sorted((f for f in folder.glob("*.jpg") if f.is_file()), key=lambda f: f.stat().st_mtime)
    deleted = 0

    for f in list(files):
        if datetime.fromtimestamp(f.stat().st_mtime) < cutoff:
            f.unlink()
            files.remove(f)
            deleted += 1

    cap_bytes = config.UNKNOWN_CAPTURES_MAX_MB * 1024 ** 2
    total = sum(f.stat().st_size for f in files)
    while files and total > cap_bytes:
        oldest = files.pop(0)
        size = oldest.stat().st_size
        oldest.unlink()
        total -= size
        deleted += 1

    if deleted:
        logger.info("Snapshot cleanup: removed %d old image(s)", deleted)
    return {"deleted": deleted, "size_mb": total / 1024 ** 2}
