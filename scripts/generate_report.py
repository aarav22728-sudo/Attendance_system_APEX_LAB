"""
APEX LAB Attendance System — Generate Weekly Report
CLI script to manually trigger an attendance report for a date range.

Usage:
    python scripts/generate_report.py
    python scripts/generate_report.py --start 2026-10-20 --end 2026-10-26
"""

import sys
import argparse
import logging
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL, logging.INFO),
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    handlers=[
        logging.FileHandler(config.LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


def parse_args():
    """Parse CLI arguments for start/end dates."""
    parser = argparse.ArgumentParser(
        description="Generate an APEX LAB weekly attendance report.",
    )
    parser.add_argument(
        "--start",
        type=str,
        default=None,
        help="Start date (YYYY-MM-DD). Defaults to 7 days ago.",
    )
    parser.add_argument(
        "--end",
        type=str,
        default=None,
        help="End date (YYYY-MM-DD). Defaults to today.",
    )
    return parser.parse_args()


def main():
    """Entry point — resolve dates, generate report, print path."""
    args = parse_args()

    today = datetime.now().date()

    if args.start:
        try:
            start_date = datetime.strptime(args.start, "%Y-%m-%d").date()
        except ValueError:
            print(f"  ✗ Invalid start date: {args.start}  (expected YYYY-MM-DD)")
            sys.exit(1)
    else:
        start_date = today - timedelta(days=6)

    if args.end:
        try:
            end_date = datetime.strptime(args.end, "%Y-%m-%d").date()
        except ValueError:
            print(f"  ✗ Invalid end date: {args.end}  (expected YYYY-MM-DD)")
            sys.exit(1)
    else:
        end_date = today

    if start_date > end_date:
        print("  ✗ Start date must be before or equal to end date.")
        sys.exit(1)

    print("\n╔══════════════════════════════════════╗")
    print("║   APEX LAB — Report Generator        ║")
    print("╚══════════════════════════════════════╝\n")
    print(f"  Period : {start_date}  →  {end_date}")
    print(f"  Days   : {(end_date - start_date).days + 1}\n")

    # ── Generate ──────────────────────────────────────────────────────────
    from database.db_manager import DatabaseManager
    from reports.excel_generator import WeeklyReportGenerator

    db = DatabaseManager()
    generator = WeeklyReportGenerator(db)

    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")

    try:
        filepath = generator.generate_report(start_str, end_str)
        print(f"  ✓  Report generated successfully!")
        print(f"  →  {filepath}\n")
        logger.info("Report generated: %s", filepath)
    except Exception:
        logger.exception("Failed to generate report")
        print("  ✗ Report generation failed — see logs for details.")
        sys.exit(1)


if __name__ == "__main__":
    main()
