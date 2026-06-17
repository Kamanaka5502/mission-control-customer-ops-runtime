import hashlib
import json
from app.models import CustomerRequest, Receipt, Outcome


def stable_hash(payload: dict) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def build_receipt(req: CustomerRequest, outcome: Outcome | str, effect_status: str, no_bind: bool, reason_codes: list[str]) -> Receipt:
    public_payload = {
        "request_id": req.request_id,
        "workflow_id": req.workflow_id,
        "requested_action": req.requested_action,
        "outcome": outcome,
        "effect_status": effect_status,
        "no_bind_status": no_bind,
        "reason_codes": reason_codes,
    }
    digest = stable_hash(public_payload)
    return Receipt(
        receipt_id=f"receipt-{req.request_id}",
        request_id=req.request_id,
        workflow_id=req.workflow_id,
        outcome=outcome,
        protected_effect_status=effect_status,
        no_bind_status=no_bind,
        reason_codes=reason_codes,
        replay_token=f"replay-{digest[:16]}",
        public_hash=digest,
        notice="Operational receipt for customer workflow review."
    )
