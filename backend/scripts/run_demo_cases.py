import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from app.models import CustomerRequest
from app.services.policy_gate import evaluate_request
from app.services.receipt import build_receipt

CASES = ROOT / "demo_cases"

for path in sorted(CASES.glob("*.json")):
    payload = json.loads(path.read_text())
    req = CustomerRequest(**payload)
    outcome, effect_status, no_bind, reason_codes = evaluate_request(req)
    receipt = build_receipt(req, outcome, effect_status, no_bind, reason_codes)

    print("=" * 80)
    print(path.name)
    print(json.dumps({
        "outcome": outcome,
        "protected_effect_status": effect_status,
        "no_bind_status": no_bind,
        "reason_codes": reason_codes,
        "receipt": receipt.model_dump()
    }, indent=2, default=str))
