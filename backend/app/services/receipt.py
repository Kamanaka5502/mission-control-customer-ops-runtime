import hashlib
import hmac
import json
from typing import Any

from app.models import CustomerRequest, Outcome, Receipt
from app.services.key_management import current_receipt_key_id, current_receipt_secret, receipt_secret_for_key_id


SIGNATURE_ALGORITHM = "hmac-sha256"
REQUIRED_SIGNED_FIELDS = {
    "request_id",
    "workflow_id",
    "requested_action",
    "outcome",
    "protected_effect_status",
    "no_bind_status",
    "reason_codes",
    "public_hash",
    "signature",
}


def stable_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def receipt_key_id() -> str:
    return current_receipt_key_id()


def receipt_secret() -> str:
    return current_receipt_secret()


def _outcome_value(outcome: Outcome | str) -> str:
    return outcome.value if isinstance(outcome, Outcome) else str(outcome)


def receipt_public_payload(
    *,
    request_id: str,
    workflow_id: str,
    requested_action: str,
    outcome: Outcome | str,
    effect_status: str,
    no_bind: bool,
    reason_codes: list[str],
    request_snapshot_hash: str | None = None,
    evidence_manifest_hash: str | None = None,
) -> dict[str, Any]:
    return {
        "request_id": request_id,
        "workflow_id": workflow_id,
        "requested_action": requested_action,
        "outcome": _outcome_value(outcome),
        "effect_status": effect_status,
        "no_bind_status": no_bind,
        "reason_codes": reason_codes,
        "request_snapshot_hash": request_snapshot_hash,
        "evidence_manifest_hash": evidence_manifest_hash,
    }


def sign_public_hash(public_hash: str, *, secret: str | None = None) -> str:
    key = (secret if secret is not None else receipt_secret()).encode("utf-8")
    return hmac.new(key, public_hash.encode("ascii"), hashlib.sha256).hexdigest()


def verify_public_hash_signature(public_hash: str, signature: str, key_id: str | None) -> dict[str, Any]:
    secret = receipt_secret_for_key_id(key_id)
    if not secret:
        return {
            "valid": False,
            "signature_matches": False,
            "reason": "unknown_signature_key_id",
            "signature_algorithm": SIGNATURE_ALGORITHM,
            "signature_key_id": key_id,
        }
    expected_signature = sign_public_hash(public_hash, secret=secret)
    signature_matches = hmac.compare_digest(expected_signature, str(signature or ""))
    return {
        "valid": signature_matches,
        "signature_matches": signature_matches,
        "signature_algorithm": SIGNATURE_ALGORITHM,
        "signature_key_id": key_id,
    }


def build_receipt(
    req: CustomerRequest,
    outcome: Outcome | str,
    effect_status: str,
    no_bind: bool,
    reason_codes: list[str],
    *,
    request_snapshot_hash: str | None = None,
    evidence_manifest_hash: str | None = None,
) -> Receipt:
    public_payload = receipt_public_payload(
        request_id=req.request_id,
        workflow_id=req.workflow_id,
        requested_action=req.requested_action,
        outcome=outcome,
        effect_status=effect_status,
        no_bind=no_bind,
        reason_codes=reason_codes,
        request_snapshot_hash=request_snapshot_hash,
        evidence_manifest_hash=evidence_manifest_hash,
    )
    digest = stable_hash(public_payload)
    return Receipt(
        receipt_id=f"receipt-{req.request_id}",
        request_id=req.request_id,
        workflow_id=req.workflow_id,
        requested_action=req.requested_action,
        outcome=outcome,
        protected_effect_status=effect_status,
        no_bind_status=no_bind,
        reason_codes=reason_codes,
        replay_token=f"replay-{digest[:16]}",
        public_hash=digest,
        notice="Operational receipt for customer workflow review.",
        request_snapshot_hash=request_snapshot_hash,
        evidence_manifest_hash=evidence_manifest_hash,
        signature_algorithm=SIGNATURE_ALGORITHM,
        signature_key_id=receipt_key_id(),
        signature=sign_public_hash(digest),
    )


def verify_receipt_signature(receipt: dict[str, Any], *, secret: str | None = None) -> dict[str, Any]:
    missing_fields = sorted(field for field in REQUIRED_SIGNED_FIELDS if field not in receipt)
    if missing_fields:
        return {
            "valid": False,
            "hash_matches": False,
            "signature_matches": False,
            "reason": "missing_required_signed_fields",
            "missing_fields": missing_fields,
            "expected_public_hash": None,
            "provided_public_hash": str(receipt.get("public_hash") or ""),
            "signature_algorithm": receipt.get("signature_algorithm"),
            "signature_key_id": receipt.get("signature_key_id"),
        }

    no_bind_status = receipt.get("no_bind_status")
    if not isinstance(no_bind_status, bool):
        return {
            "valid": False,
            "hash_matches": False,
            "signature_matches": False,
            "reason": "invalid_no_bind_status",
            "expected_public_hash": None,
            "provided_public_hash": str(receipt.get("public_hash") or ""),
            "signature_algorithm": receipt.get("signature_algorithm"),
            "signature_key_id": receipt.get("signature_key_id"),
        }

    public_payload = receipt_public_payload(
        request_id=str(receipt["request_id"]),
        workflow_id=str(receipt["workflow_id"]),
        requested_action=str(receipt["requested_action"]),
        outcome=str(receipt["outcome"]),
        effect_status=str(receipt["protected_effect_status"]),
        no_bind=no_bind_status,
        reason_codes=list(receipt.get("reason_codes") or []),
        request_snapshot_hash=receipt.get("request_snapshot_hash"),
        evidence_manifest_hash=receipt.get("evidence_manifest_hash"),
    )
    expected_hash = stable_hash(public_payload)
    provided_hash = str(receipt.get("public_hash") or "")
    provided_signature = str(receipt.get("signature") or "")
    signature_key_id = str(receipt.get("signature_key_id") or "")

    hash_matches = hmac.compare_digest(expected_hash, provided_hash)
    if secret is not None:
        expected_signature = sign_public_hash(expected_hash, secret=secret)
        signature_matches = hmac.compare_digest(expected_signature, provided_signature)
        reason = None
    else:
        signature_result = verify_public_hash_signature(expected_hash, provided_signature, signature_key_id)
        signature_matches = bool(signature_result.get("signature_matches"))
        reason = signature_result.get("reason")

    return {
        "valid": hash_matches and signature_matches,
        "hash_matches": hash_matches,
        "signature_matches": signature_matches,
        "reason": reason,
        "expected_public_hash": expected_hash,
        "provided_public_hash": provided_hash,
        "signature_algorithm": receipt.get("signature_algorithm"),
        "signature_key_id": receipt.get("signature_key_id"),
    }
