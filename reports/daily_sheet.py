"""Daily attendance workbook, rebuilt while the kiosk runs.

Columns: Sr. No | Name | Role | Time of entrance | In database | Purpose
"""

import logging
import os
from datetime import date, datetime

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

import config

logger = logging.getLogger(__name__)

DAILY_DIR = config.REPORTS_DIR / "daily"
HEADERS = ["Sr. No", "Name", "Role", "Time of entrance", "In database", "Purpose"]

_HEADER_FILL = PatternFill(start_color="0F3460", end_color="0F3460", fill_type="solid")
_HEADER_FONT = Font(bold=True, color="FFFFFF")
_VISITOR_FILL = PatternFill(start_color="FFF4CE", end_color="FFF4CE", fill_type="solid")
_UNKNOWN_FILL = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")
_THIN = Side(style="thin")
_BORDER = Border(left=_THIN, right=_THIN, top=_THIN, bottom=_THIN)


def build_entries(db, day: date) -> list:
    """One entry per person (first entrance), per unknown sighting, and per visitor."""
    entries = []
    seen = set()
    unknown_no = 0
    rows = db.get_day_rows(day.isoformat())
    for _id, pid, pname, prole, ts, status, _conf, _snap, vname, purpose in rows:
        when = datetime.fromisoformat(ts)
        if status == "present" and pid is not None:
            if pid in seen:
                continue
            seen.add(pid)
            entries.append((when, pname, prole or "member", "Yes", ""))
        elif status == "visitor":
            entries.append((when, f"{vname} (visitor)", "Temporary", "No", purpose or ""))
        elif status == "unknown":
            unknown_no += 1
            entries.append((when, f"Unknown #{unknown_no}", "Unregistered", "No", ""))
    return entries


def build(db, day: date = None):
    """Write today's workbook and return its path."""
    day = day or datetime.now().date()
    entries = build_entries(db, day)

    wb = Workbook()
    ws = wb.active
    ws.title = day.isoformat()
    ws.append([f"APEX LAB attendance: {day.strftime('%A, %d %B %Y')}"])
    ws.merge_cells("A1:F1")
    ws["A1"].font = Font(bold=True, size=14)

    ws.append(HEADERS)
    header_row = ws.max_row
    for cell in ws[header_row]:
        cell.font = _HEADER_FONT
        cell.fill = _HEADER_FILL
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = _BORDER

    for n, (when, name, role, in_db, purpose) in enumerate(entries, start=1):
        ws.append([n, name, role, when.strftime("%H:%M:%S"), in_db, purpose])
        fill = None
        if role == "Temporary":
            fill = _VISITOR_FILL
        elif role == "Unregistered":
            fill = _UNKNOWN_FILL
        for cell in ws[ws.max_row]:
            cell.border = _BORDER
            if fill is not None:
                cell.fill = fill

    if not entries:
        ws.append(["No entries yet today."])

    for col, width in enumerate([8, 28, 16, 18, 14, 36], start=1):
        ws.column_dimensions[get_column_letter(col)].width = width
    ws.freeze_panes = f"A{header_row + 1}"

    DAILY_DIR.mkdir(parents=True, exist_ok=True)
    path = DAILY_DIR / f"attendance_{day.isoformat()}.xlsx"
    tmp = DAILY_DIR / f"attendance_{day.isoformat()}.tmp.xlsx"
    wb.save(tmp)
    os.replace(tmp, path)  # swap in the finished file in one step
    logger.info("Daily sheet saved: %s (%d entries)", path, len(entries))
    return path
