from fastapi import APIRouter, HTTPException
from app.models import CustomerRequest, RuntimeDecision
from app.services.policy_gate import evaluate_request
from app.services.receipt import build_receipt
from app.services.store import REQUESTS, DECISIONS, RECEIPTS

router = APIRouter()


@router.post("/evaluate", response_model=RuntimeDecision)
def evaluate_customer_request(req: CustomerRequest):
    outcome, effect_status, no_bind, reason_codes = evaluate_request(req)
    receipt = build_receipt(req, outcome, effect_status, no_bind, reason_codes)

    decision = RuntimeDecision(
        request_id=req.request_id,
        workflow_id=req.workflow_id,
        outcome=outcome,
        protected_effect_status=effect_status,
        no_bind_status=no_bind,
        reason_codes=reason_codes,
        receipt_id=receipt.receipt_id,
        replay_token=receipt.replay_token,
        customer_visible_summary=(
            f"Request {req.request_id} produced {outcome}. "
            f"Protected effect status: {effect_status}."
        )
    )

    REQUESTS[req.request_id] = req
    DECISIONS[req.request_id] = decision
    RECEIPTS[receipt.receipt_id] = receipt
    return decision


@router.get("/{request_id}", response_model=RuntimeDecision)
def get_decision(request_id: str):
    if request_id not in DECISIONS:
        raise HTTPException(status_code=404, detail="Request decision not found")
    return DECISIONS[request_id]


@router.get("/{request_id}/receipt")
def get_receipt(request_id: str):
    receipt_id = f"receipt-{request_id}"
    if receipt_id not in RECEIPTS:
        raise HTTPException(status_code=404, detail="Receipt not found")
    return RECEIPTS[receipt_id]
