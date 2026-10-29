# APEX LAB — Face Recognition Attendance System
### Optimized for Raspberry Pi 5 Model B

An automated, edge-computing face recognition attendance kiosk featuring real-time webcam face tracking, name HUD overlay directly above detection squares, duplicate check-in prevention, automated weekly Excel report generation, and unknown subject alerts.

---

## 🛠 Hardware Architecture

- **Processor**: Raspberry Pi 5 Model B (Broadcom BCM2712 Quad-Core Cortex-A76 @ 2.4 GHz, 8GB LPDDR4X RAM recommended)
- **Camera**: USB UVC Webcam (Logitech C270, C920, or equivalent 720p/1080p 30FPS)
- **Cooling**: Official Raspberry Pi Active Cooler (essential to prevent thermal throttling during continuous face inference)
- **Power**: 27W USB-C Power Supply (5.1V / 5.0A)
- **Display**: Official 7" Touchscreen, HDMI IPS display, or Kiosk monitor

---

## 🚀 Quick Start on Raspberry Pi 5 (Bookworm 64-bit)

### 1. System Packages
Open terminal on your Raspberry Pi 5:
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-pip python3-dev build-essential cmake \
                    libopenblas-dev liblapack-dev libjpeg-dev zlib1g-dev \
                    libatlas-base-dev libavcodec-dev libavformat-dev libswscale-dev \
                    libv4l-dev libxvidcore-dev libx264-dev libgtk-3-dev \
                    python3-pil.imagetk v4l-utils
```

### 2. Python Environment Setup
```bash
cd ~
git clone <your-repo-link> APEX_LAB_attendance
cd APEX_LAB_attendance

# Create virtual environment with system site-packages (recommended for Pi 5 Bookworm)
python3 -m venv --system-site-packages venv
source venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

### 3. Verify Webcam Connection
```bash
v4l2-ctl --list-devices
```
If your webcam is index 0 (`/dev/video0`), you are ready. If it's on `/dev/video1`, specify `--cam 1` when launching.

### 4. Run the Kiosk
```bash
# Standard desktop window
python main.py

# Fullscreen Kiosk Mode (Auto-adjusts for touch or kiosk screen)
python main.py --kiosk
```

---

## 📁 System Architecture & Modules

```
APEX_LAB_attendance/
├── main.py                     # Primary entrypoint & background scheduler
├── config.py                   # Master configuration (thresholds, timings, colors)
├── requirements.txt            # Python dependencies
│
├── core/
│   ├── camera.py               # Multithreaded OpenCV camera acquisition
│   ├── detector.py             # Face detection (HOG / CNN with size filtering)
│   ├── recognizer.py           # 128-D Euclidean vector face matching
│   └── attendance.py           # Check-in logging & duplicate control rules
│
├── database/
│   ├── db_manager.py           # Thread-safe SQLite manager with WAL mode
│   ├── models.py               # Person, FaceEncoding, and AttendanceRecord schemas
│   └── apex_lab.db             # SQLite database file
│
├── ui/
│   ├── app.py                  # CustomTkinter main kiosk controller
│   ├── themes/
│   │   └── glassmorphism.py    # Dark HUD aesthetic, color palette, typography
│   └── components/
│       ├── camera_feed.py      # Live viewport with bracket HUD & Name tag above box
│       ├── status_panel.py     # Live telemetry metrics, subject card, check-in feed
│       ├── alert_dialog.py     # Unknown person alert with snapshot & action buttons
│       └── enrollment.py       # Multi-angle face capture registration flow
│
├── reports/
│   ├── excel_generator.py      # Automated 4-sheet weekly Excel workbook generator
│   └── exports/                # Exported .xlsx workbooks
│
├── scripts/
│   ├── enroll_person.py        # CLI personnel enrollment
│   ├── generate_report.py      # Manual Excel report generator
│   ├── benchmark.py            # Latency and FPS test on Raspberry Pi 5
│   └── generate_assets.py      # UI sound synthesizer
│
└── assets/sounds/              # Chime, alert, and enrollment feedback audio
```

---

## 📊 Features & Functional Highlights

1. **Precision HUD Overlays**: Name tag, confidence score, and status pill are rendered directly **ABOVE the face detection square**, preventing face occlusion.
2. **Duplicate Prevention**: Configurable `DUPLICATE_WINDOW_MINUTES` (default 30 mins) ensures members are not repeatedly logged while remaining in view.
3. **Weekly Excel Generator**: Automated 4-sheet report (Summary grid with % attendance, Daily Log, Unknown Faces log, and Analytics) created automatically every week or on-demand with one click.
4. **Unknown Person Protocol**: Consecutive unregistered detections trigger snapshot capture, acoustic alert, and interactive resolution dialog (`Register Person Now` / `Log as Visitor` / `Dismiss`).
5. **Multi-Angle Registration**: Guided registration captures 3 to 5 face angles to ensure 95%+ recognition accuracy across various orientations and lighting conditions.
6. **Raspberry Pi 5 Optimization**: Frame downscaling (`PROCESS_SCALE = 0.5`) decouples camera display FPS (~30 FPS) from recognition inference (~15–20 FPS).

---

## 🔄 Running on Startup (Systemd Service)

To make the kiosk automatically boot into full-screen mode on power-up:

1. Create a service file:
```bash
sudo nano /etc/systemd/system/apex-attendance.service
```

2. Add the following content:
```ini
[Unit]
Description=APEX LAB Attendance Kiosk
After=graphical.target

[Service]
Environment=DISPLAY=:0
Environment=XAUTHORITY=/home/pi/.Xauthority
Type=simple
User=pi
WorkingDirectory=/home/pi/APEX_LAB_attendance
ExecStart=/home/pi/APEX_LAB_attendance/venv/bin/python main.py --kiosk
Restart=always
RestartSec=5

[Install]
WantedBy=graphical.target
```

3. Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable apex-attendance.service
sudo systemctl start apex-attendance.service
```
