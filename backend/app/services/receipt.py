import hashlib
import hmac
import json
import os
from app.models import CustomerRequest, Receipt, Outcome


def _truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def receipt_signing_required() -> bool:
    app_env = os.getenv("APP_ENV", "development").strip().lower()
    return app_env in {"production", "prod"} or _truthy(os.getenv("REQUIRE_SIGNED_RECEIPTS"))


def stable_hash(payload: dict) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def sign_hash(public_hash: str) -> str:
    secret = os.getenv("RECEIPT_SIGNING_SECRET")
    if not secret:
        if receipt_signing_required():
            raise RuntimeError("RECEIPT_SIGNING_SECRET must be configured when signed receipt enforcement is enabled.")
        return "UNSIGNED_DEV_MODE"

    return hmac.new(secret.encode("utf-8"), public_hash.encode("utf-8"), hashlib.sha256).hexdigest()


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
        signature=sign_hash(digest),
        notice="Operational receipt for customer workflow review."
    )
