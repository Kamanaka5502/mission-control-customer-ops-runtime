from copy import deepcopy
from fastapi import APIRouter, HTTPException
from app.services.store import REQUESTS, DECISIONS
from app.services.policy_gate import evaluate_request

router = APIRouter()


@router.post("/{request_id}/same-condition")
def replay_same_condition(request_id: str):
    if request_id not in REQUESTS:
        raise HTTPException(status_code=404, detail="Request not found")

    req = REQUESTS[request_id]
    prior = DECISIONS[request_id]
    outcome, effect_status, no_bind, reason_codes = evaluate_request(req)

    return {
        "request_id": request_id,
        "replay_type": "same_condition",
        "prior_outcome": prior.outcome,
        "observed_outcome": outcome,
        "matched": prior.outcome == outcome,
        "protected_effect_status": effect_status,
        "no_bind_status": no_bind,
        "reason_codes": reason_codes
    }


@router.post("/{request_id}/changed-condition")
def replay_changed_condition(request_id: str):
    if request_id not in REQUESTS:
        raise HTTPException(status_code=404, detail="Request not found")

    changed = deepcopy(REQUESTS[request_id])
    changed.authority_present = False
    changed.evidence_fresh = False
    changed.risk_level = "high"

    outcome, effect_status, no_bind, reason_codes = evaluate_request(changed)

    return {
        "request_id": request_id,
        "replay_type": "changed_condition",
        "changed_conditions": ["authority_removed", "evidence_stale", "risk_high"],
        "observed_outcome": outcome,
        "protected_effect_status": effect_status,
        "no_bind_status": no_bind,
        "reason_codes": reason_codes,
        "customer_visible_proof": "Changed conditions do not inherit the previous authorization posture."
    }
