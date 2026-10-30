"""
APEX LAB Attendance System — Enroll Person
CLI script to capture face encodings from a webcam and register a new person.

Usage:
    python scripts/enroll_person.py
"""

import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config

import cv2
import face_recognition
import numpy as np

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL, logging.INFO),
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    handlers=[
        logging.FileHandler(config.LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


def _open_camera():
    """Open the webcam and configure it."""
    cap = cv2.VideoCapture(config.CAMERA_INDEX)
    if not cap.isOpened():
        logger.error("Cannot open webcam (index %d)", config.CAMERA_INDEX)
        sys.exit(1)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.CAMERA_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.CAMERA_HEIGHT)
    cap.set(cv2.CAP_PROP_FPS, config.CAMERA_FPS)
    return cap


def enroll():
    """Interactive enrollment flow."""
    # ── Collect info ──────────────────────────────────────────────────────
    print("\n╔══════════════════════════════════════╗")
    print("║   APEX LAB — Person Enrollment       ║")
    print("╚══════════════════════════════════════╝\n")

    name = input("  Full name : ").strip()
    if not name:
        print("  ✗ Name cannot be empty.")
        sys.exit(1)

    role = input("  Role      : ").strip()
    if not role:
        role = "member"

    target = config.ENCODINGS_PER_PERSON
    print(f"\n  → Need {target} captures from different angles.")
    print("  → Press SPACE to capture, Q to finish early.\n")

    # ── Prepare storage directory ─────────────────────────────────────────
    person_dir = config.KNOWN_FACES_DIR / name.replace(" ", "_")
    person_dir.mkdir(parents=True, exist_ok=True)

    # ── Open camera & capture loop ────────────────────────────────────────
    cap = _open_camera()
    encodings: list[np.ndarray] = []
    snapshots: list[Path] = []
    capture_idx = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            logger.warning("Frame grab failed — retrying…")
            continue

        display = frame.copy()

        # Draw face boxes in real-time
        small = cv2.resize(frame, (0, 0), fx=config.PROCESS_SCALE, fy=config.PROCESS_SCALE)
        rgb_small = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
        face_locs = face_recognition.face_locations(rgb_small, model=config.DETECTION_MODEL)
        scale = 1 / config.PROCESS_SCALE

        for top, right, bottom, left in face_locs:
            t, r, b, l = int(top * scale), int(right * scale), int(bottom * scale), int(left * scale)
            cv2.rectangle(display, (l, t), (r, b), (0, 230, 118), 2)

        # Status text
        status = f"Captures: {len(encodings)}/{target}  |  SPACE=capture  Q=quit"
        cv2.putText(display, status, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        cv2.imshow("APEX LAB — Enrollment", display)
        key = cv2.waitKey(1) & 0xFF

        if key == ord("q") or key == ord("Q"):
            break

        if key == ord(" "):
            # Process full-res frame for encoding
            rgb_full = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            locs = face_recognition.face_locations(rgb_full, model=config.DETECTION_MODEL)

            if len(locs) == 0:
                print("  ⚠  No face detected — try again.")
                continue
            if len(locs) > 1:
                print("  ⚠  Multiple faces detected — only one person should be in frame.")
                continue

            enc = face_recognition.face_encodings(rgb_full, locs)
            if not enc:
                print("  ⚠  Could not compute encoding — try again.")
                continue

            capture_idx += 1
            encodings.append(enc[0])

            # Save snapshot
            snap_path = person_dir / f"{capture_idx:02d}.jpg"
            cv2.imwrite(str(snap_path), frame)
            snapshots.append(snap_path)

            print(f"  ✓  Capture {len(encodings)}/{target} saved → {snap_path.name}")

            if len(encodings) >= target:
                print(f"\n  ✓  All {target} captures complete!")
                break

    cap.release()
    cv2.destroyAllWindows()

    if not encodings:
        print("  ✗ No faces captured. Enrollment aborted.")
        sys.exit(1)

    # ── Persist to database ───────────────────────────────────────────────
    from database.db_manager import DatabaseManager

    db = DatabaseManager()

    # Register the person
    photo_path = str(person_dir / "01.jpg") if snapshots else None
    person_id = db.add_person(name, role, photo_path)

    # Store each face encoding
    for encoding in encodings:
        db.add_face_encoding(person_id, encoding)

    print(f"\n  ╔══════════════════════════════════════╗")
    print(f"  ║  Enrollment Complete                  ║")
    print(f"  ╠══════════════════════════════════════╣")
    print(f"  ║  Name      : {name:<24s}║")
    print(f"  ║  Role      : {role:<24s}║")
    print(f"  ║  Person ID : {str(person_id):<24s}║")
    print(f"  ║  Encodings : {len(encodings):<24d}║")
    print(f"  ║  Photos    : {str(person_dir):<24s}║")
    print(f"  ╚══════════════════════════════════════╝\n")

    logger.info(
        "Enrolled %s (id=%s, role=%s, %d encodings)",
        name, person_id, role, len(encodings),
    )


if __name__ == "__main__":
    enroll()
