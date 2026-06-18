#!/usr/bin/env python3
"""Verify a Mission Control receipt outside the live API process."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.services.receipt import verify_receipt_signature  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify a Mission Control signed receipt JSON file.")
    parser.add_argument("receipt", help="Path to a receipt JSON file")
    parser.add_argument(
        "--secret",
        help="Optional verifier secret. If omitted, RECEIPT_SIGNING_SECRET or the development verifier default is used.",
    )
    args = parser.parse_args()

    receipt_path = Path(args.receipt)
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    result = verify_receipt_signature(receipt, secret=args.secret)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
