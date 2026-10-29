"""
APEX LAB Attendance System — Main Entrypoint
Run this script to launch the APEX LAB kiosk attendance application on Raspberry Pi 5.

Usage:
    python main.py                  # Standard desktop window
    python main.py --kiosk          # Fullscreen Kiosk mode (ideal for RPi 5 Touch Display)
    python main.py --no-cam         # Simulation mode without camera hardware
"""

import sys
import logging
import argparse
from datetime import datetime, timedelta
from pathlib import Path

# Configure paths
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))
import config

# Setup logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(config.LOG_FILE, encoding="utf-8"),
    ],
)
logger = logging.getLogger("APEX_LAB")


def setup_background_scheduler(db_manager):
    """Start APScheduler background job to auto-generate Excel reports weekly."""
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from reports.excel_generator import WeeklyReportGenerator

        scheduler = BackgroundScheduler(daemon=True)
        report_gen = WeeklyReportGenerator(db_manager)

        def generate_weekly_job():
            today = datetime.now().date()
            start_date = (today - timedelta(days=6)).isoformat()
            end_date = today.isoformat()
            logger.info("Executing scheduled weekly attendance report (%s to %s)...", start_date, end_date)
            try:
                path = report_gen.generate_report(start_date=start_date, end_date=end_date)
                logger.info("Scheduled report generated: %s", path)
            except Exception:
                logger.exception("Scheduled report generation failed.")

        # Parse configured day & time
        day_of_week = config.REPORT_DAY[:3].lower()  # e.g. "sun"
        hour, minute = map(int, config.REPORT_TIME.split(":"))

        scheduler.add_job(
            generate_weekly_job,
            "cron",
            day_of_week=day_of_week,
            hour=hour,
            minute=minute,
        )
        scheduler.start()
        logger.info("Background scheduler started (Weekly report on %s at %s).", config.REPORT_DAY, config.REPORT_TIME)
        return scheduler

    except ImportError:
        logger.warning("APScheduler not installed — weekly auto-report scheduler disabled.")
        return None
    except Exception as e:
        logger.warning("Could not start background scheduler: %s", e)
        return None


def main():
    parser = argparse.ArgumentParser(description="APEX LAB Face Recognition Attendance System")
    parser.add_argument("--kiosk", action="store_true", help="Launch in fullscreen kiosk mode")
    parser.add_argument("--cam", type=int, default=config.CAMERA_INDEX, help="Webcam device index")
    args = parser.parse_args()

    if args.cam != config.CAMERA_INDEX:
        config.CAMERA_INDEX = args.cam

    logger.info("=" * 60)
    logger.info("  APEX LAB — Face Recognition Attendance System")
    logger.info("  Target Hardware: Raspberry Pi 5 Model B")
    logger.info("=" * 60)

    from ui.app import AttendanceApp

    app = AttendanceApp()

    if args.kiosk:
        logger.info("Entering Kiosk (Fullscreen) Mode...")
        app.attributes("-fullscreen", True)

    # Start weekly scheduler
    scheduler = setup_background_scheduler(app.db)

    try:
        app.mainloop()
    except KeyboardInterrupt:
        logger.info("Termination signal received. Exiting...")
    finally:
        if scheduler and scheduler.running:
            scheduler.shutdown(wait=False)
        logger.info("APEX LAB shutdown complete.")


if __name__ == "__main__":
    main()
