"""
Generate basic UI feedback sounds for APEX LAB Kiosk.
Produces:
- assets/sounds/match.wav    (pleasant two-tone chime)
- assets/sounds/unknown.wav  (warning alert tone)
- assets/sounds/enrolled.wav (success confirmation chime)
"""

import math
import wave
import struct
from pathlib import Path

SOUNDS_DIR = Path(__file__).resolve().parent.parent / "assets" / "sounds"
SOUNDS_DIR.mkdir(parents=True, exist_ok=True)


def create_tone(filename: str, frequencies: list[float], duration_sec: float = 0.25):
    filepath = SOUNDS_DIR / filename
    sample_rate = 44100
    n_samples = int(sample_rate * duration_sec)

    with wave.open(str(filepath), "w") as wav:
        wav.setnchannels(1)        # Mono
        wav.setsampwidth(2)        # 16-bit
        wav.setframerate(sample_rate)

        for i in range(n_samples):
            t = i / sample_rate
            # Smooth envelope (fade in and fade out)
            envelope = math.sin(math.pi * (i / n_samples))
            val = 0.0
            for freq in frequencies:
                val += math.sin(2.0 * math.pi * freq * t)
            val = (val / len(frequencies)) * envelope * 24000.0
            wav.writeframesraw(struct.pack("<h", int(val)))

    print(f"Created sound: {filepath}")


if __name__ == "__main__":
    create_tone("match.wav", [587.33, 880.0], 0.22)       # D5 -> A5 chime
    create_tone("unknown.wav", [330.0, 293.66], 0.35)     # Lower warning tone
    create_tone("enrolled.wav", [523.25, 659.25, 783.99], 0.4) # C Major triad
