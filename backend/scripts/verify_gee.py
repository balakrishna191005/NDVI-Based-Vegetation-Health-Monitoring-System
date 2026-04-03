"""
Verify Earth Engine credentials from backend/.env (run from repo root or backend).

  cd backend
  python scripts/verify_gee.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure backend package is importable
_BACKEND = Path(__file__).resolve().parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from dotenv import load_dotenv

load_dotenv(_BACKEND / ".env")

import ee  # noqa: E402

from app.services.gee_service import initialize_gee  # noqa: E402


def main() -> None:
    print("Initializing Earth Engine...")
    initialize_gee()
    one = ee.Number(1).getInfo()
    print("ee.Number(1).getInfo() =", one)
    print("OK — Earth Engine is reachable with your current configuration.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("FAILED:", e)
        sys.exit(1)
