"""
APEX LAB Attendance System — Performance Benchmark
Measures face-detection speed across HOG and CNN models.

Usage:
    python scripts/benchmark.py
"""

import sys
import time
import platform
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config

import cv2
import face_recognition

try:
    import psutil
    _HAS_PSUTIL = True
except ImportError:
    _HAS_PSUTIL = False

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL, logging.INFO),
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    handlers=[
        logging.FileHandler(config.LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

TOTAL_FRAMES = 100


def _print_hardware_info():
    """Print CPU, RAM, and OS details."""
    print("\n╔══════════════════════════════════════╗")
    print("║   APEX LAB — Performance Benchmark   ║")
    print("╚══════════════════════════════════════╝\n")
    print("  Hardware Info")
    print("  ─────────────────────────────────────")
    print(f"  OS       : {platform.system()} {platform.release()} ({platform.machine()})")
    print(f"  Python   : {platform.python_version()}")
    print(f"  Processor: {platform.processor() or 'N/A'}")

    if _HAS_PSUTIL:
        cpu_count = psutil.cpu_count(logical=True)
        cpu_physical = psutil.cpu_count(logical=False)
        ram = psutil.virtual_memory()
        ram_gb = ram.total / (1024 ** 3)
        print(f"  CPU cores: {cpu_physical} physical / {cpu_count} logical")
        print(f"  RAM      : {ram_gb:.1f} GB  ({ram.percent}% used)")
    else:
        print("  (install psutil for detailed CPU/RAM info)")

    print()


def _run_benchmark(cap, model: str):
    """
    Run face detection for *TOTAL_FRAMES* frames using *model*.
    Returns a dict of timing statistics.
    """
    times = []
    face_counts = []

    print(f"  Running {model.upper()} benchmark ({TOTAL_FRAMES} frames) …")

    for i in range(TOTAL_FRAMES):
        ret, frame = cap.read()
        if not ret:
            logger.warning("Frame grab failed at frame %d", i)
            continue

        small = cv2.resize(
            frame, (0, 0),
            fx=config.PROCESS_SCALE,
            fy=config.PROCESS_SCALE,
        )
        rgb_small = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)

        t0 = time.perf_counter()
        face_locs = face_recognition.face_locations(rgb_small, model=model)
        elapsed = time.perf_counter() - t0

        times.append(elapsed)
        face_counts.append(len(face_locs))

        # Progress indicator every 25 frames
        if (i + 1) % 25 == 0:
            print(f"    … {i + 1}/{TOTAL_FRAMES} frames processed")

    if not times:
        return None

    avg_time = sum(times) / len(times)
    min_time = min(times)
    max_time = max(times)
    avg_fps = 1.0 / avg_time if avg_time > 0 else 0
    avg_faces = sum(face_counts) / len(face_counts)

    return {
        "model": model.upper(),
        "frames": len(times),
        "avg_fps": avg_fps,
        "avg_time_ms": avg_time * 1000,
        "min_time_ms": min_time * 1000,
        "max_time_ms": max_time * 1000,
        "avg_faces": avg_faces,
        "total_faces": sum(face_counts),
    }


def _print_results(stats: dict):
    """Pretty-print benchmark results."""
    print(f"\n  ┌─── {stats['model']} Results ────────────────────┐")
    print(f"  │  Frames processed : {stats['frames']:>6d}            │")
    print(f"  │  Average FPS      : {stats['avg_fps']:>9.2f}         │")
    print(f"  │  Avg detect time  : {stats['avg_time_ms']:>9.2f} ms     │")
    print(f"  │  Min detect time  : {stats['min_time_ms']:>9.2f} ms     │")
    print(f"  │  Max detect time  : {stats['max_time_ms']:>9.2f} ms     │")
    print(f"  │  Avg faces/frame  : {stats['avg_faces']:>9.2f}         │")
    print(f"  │  Total faces found: {stats['total_faces']:>6d}            │")
    print(f"  └─────────────────────────────────────┘")


def main():
    """Entry point — open camera, run benchmarks, print comparison."""
    _print_hardware_info()

    cap = cv2.VideoCapture(config.CAMERA_INDEX)
    if not cap.isOpened():
        print("  ✗ Cannot open webcam. Exiting.")
        sys.exit(1)

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.CAMERA_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.CAMERA_HEIGHT)
    cap.set(cv2.CAP_PROP_FPS, config.CAMERA_FPS)

    results = []

    # ── HOG benchmark ─────────────────────────────────────────────────────
    print("  ─────────────────────────────────────")
    hog_stats = _run_benchmark(cap, "hog")
    if hog_stats:
        _print_results(hog_stats)
        results.append(hog_stats)

    # ── CNN benchmark ─────────────────────────────────────────────────────
    print("\n  ─────────────────────────────────────")
    cnn_stats = _run_benchmark(cap, "cnn")
    if cnn_stats:
        _print_results(cnn_stats)
        results.append(cnn_stats)

    cap.release()

    # ── Comparison ────────────────────────────────────────────────────────
    if len(results) == 2:
        hog, cnn = results
        speedup = cnn["avg_time_ms"] / hog["avg_time_ms"] if hog["avg_time_ms"] > 0 else 0
        print("\n  ─── Comparison ───────────────────────")
        print(f"  HOG avg FPS : {hog['avg_fps']:.2f}")
        print(f"  CNN avg FPS : {cnn['avg_fps']:.2f}")
        print(f"  HOG is {speedup:.1f}× faster than CNN")
        if cnn["total_faces"] > hog["total_faces"]:
            print(f"  CNN detected {cnn['total_faces'] - hog['total_faces']} more faces overall")
        elif hog["total_faces"] > cnn["total_faces"]:
            print(f"  HOG detected {hog['total_faces'] - cnn['total_faces']} more faces overall")
        else:
            print("  Both models detected the same total faces")

    print("\n  ✓ Benchmark complete.\n")
    logger.info("Benchmark finished — %d model(s) tested", len(results))


if __name__ == "__main__":
    main()
