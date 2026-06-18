#!/usr/bin/env python3
"""Verify an exported Mission Control proof bundle JSON file."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.services.proof_store import verify_proof_bundle  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify a Mission Control proof bundle JSON file.")
    parser.add_argument("bundle", help="Path to a proof bundle JSON file")
    args = parser.parse_args()

    bundle = json.loads(Path(args.bundle).read_text(encoding="utf-8"))
    result = verify_proof_bundle(bundle)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
