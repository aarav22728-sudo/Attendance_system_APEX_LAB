"""Set or change the admin PIN required for face registration.
Usage: python scripts/set_pin.py"""

import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core import pin as pin_auth


def main() -> int:
    if pin_auth.pin_is_set():
        if not pin_auth.verify_pin(getpass.getpass("Current PIN: ")):
            print("Incorrect PIN. No changes made.")
            return 1
    new = getpass.getpass("New PIN (4-8 digits): ")
    if new != getpass.getpass("Repeat new PIN: "):
        print("PINs do not match. No changes made.")
        return 1
    try:
        pin_auth.set_pin(new)
    except ValueError as e:
        print(e)
        return 1
    print("Admin PIN saved.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
