"""Health checks for the kiosk: camera, Pi temperature, disk space and snapshot storage."""

import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

import config

# Optional overrides can be added to config.py; these defaults apply otherwise
DISK_WARN_FREE_GB = getattr(config, "DISK_WARN_FREE_GB", 2.0)
TEMP_WARN_C = getattr(config, "TEMP_WARN_C", 75.0)
SNAPSHOT_CAP_MB = getattr(config, "UNKNOWN_CAPTURES_MAX_MB", 500)


@dataclass
class HealthReport:
    camera_ok: bool
    cpu_temp_c: Optional[float]
    disk_free_gb: float
    snapshots_mb: float
    warnings: List[str] = field(default_factory=list)


def cpu_temp_c() -> Optional[float]:
    """Read the Pi's CPU temperature in Celsius, or None if unavailable."""
    try:
        return int(Path("/sys/class/thermal/thermal_zone0/temp").read_text()) / 1000
    except Exception:
        return None


def folder_size_mb(folder) -> float:
    folder = Path(folder)
    if not folder.exists():
        return 0.0
    return sum(f.stat().st_size for f in folder.rglob("*") if f.is_file()) / (1024 ** 2)


def check(camera_ok: bool) -> HealthReport:
    temp = cpu_temp_c()
    free_gb = shutil.disk_usage("/").free / (1024 ** 3)
    snap_mb = folder_size_mb(config.UNKNOWN_CAPTURES_DIR)

    warnings = []
    if not camera_ok:
        warnings.append("Camera disconnected")
    if temp is not None and temp >= TEMP_WARN_C:
        warnings.append(f"Pi hot: {temp:.0f} C")
    if free_gb < DISK_WARN_FREE_GB:
        warnings.append(f"Low disk: {free_gb:.1f} GB free")
    if snap_mb >= SNAPSHOT_CAP_MB * 0.9:
        warnings.append(f"Snapshots: {snap_mb:.0f} MB")

    return HealthReport(camera_ok, temp, free_gb, snap_mb, warnings)
