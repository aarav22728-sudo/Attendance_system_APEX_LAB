"""Admin PIN protection for face registration.
Only a salted PBKDF2 hash is stored, never the PIN itself."""

import hashlib
import hmac
import json
import os
import secrets
from pathlib import Path

PIN_FILE = Path(__file__).resolve().parent.parent / "data" / "admin_pin.json"
ITERATIONS = 200_000


def pin_is_set() -> bool:
    return PIN_FILE.exists()


def _hash(pin: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", pin.encode(), salt, ITERATIONS)


def set_pin(pin: str) -> None:
    if not pin.isdigit() or not 4 <= len(pin) <= 8:
        raise ValueError("PIN must be 4 to 8 digits.")
    salt = secrets.token_bytes(16)
    PIN_FILE.parent.mkdir(parents=True, exist_ok=True)
    PIN_FILE.write_text(json.dumps({"salt": salt.hex(), "hash": _hash(pin, salt).hex()}))
    os.chmod(PIN_FILE, 0o600)


def verify_pin(pin: str) -> bool:
    if not PIN_FILE.exists():
        return False
    data = json.loads(PIN_FILE.read_text())
    expected = bytes.fromhex(data["hash"])
    return hmac.compare_digest(_hash(pin, bytes.fromhex(data["salt"])), expected)
