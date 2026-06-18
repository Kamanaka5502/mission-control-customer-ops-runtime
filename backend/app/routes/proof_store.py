from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.proof_store import build_proof_bundle, load_proof_bundle, persist_proof_bundle, verify_proof_bundle
from app.services.rbac import Actor, get_actor, require_permission
from app.services.tenant_guard import get_request_for_tenant, get_tenant_id

router = APIRouter()


@router.post("/requests/{request_id}/proof-bundle")
def export_request_proof_bundle(
    request_id: str,
    db: Session = Depends(get_db),
    actor: Actor = Depends(get_actor),
    tenant_id: str | None = Depends(get_tenant_id),
):
    require_permission(actor, "audit:read")
    get_request_for_tenant(db, request_id, tenant_id)
    bundle = build_proof_bundle(db, request_id)
    storage = persist_proof_bundle(bundle)
    return {
        "request_id": request_id,
        "proof_hash": bundle["proof_hash"],
        "storage": storage,
        "verification": verify_proof_bundle(bundle),
    }


@router.get("/requests/{request_id}/proof-bundle")
def read_request_proof_bundle(
    request_id: str,
    db: Session = Depends(get_db),
    actor: Actor = Depends(get_actor),
    tenant_id: str | None = Depends(get_tenant_id),
):
    require_permission(actor, "audit:read")
    get_request_for_tenant(db, request_id, tenant_id)
    try:
        bundle = load_proof_bundle(request_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Proof bundle not found") from exc
    return bundle


@router.get("/requests/{request_id}/proof-bundle/verify")
def verify_request_proof_bundle(
    request_id: str,
    db: Session = Depends(get_db),
    actor: Actor = Depends(get_actor),
    tenant_id: str | None = Depends(get_tenant_id),
):
    require_permission(actor, "audit:read")
    get_request_for_tenant(db, request_id, tenant_id)
    try:
        bundle = load_proof_bundle(request_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Proof bundle not found") from exc
    return {
        "request_id": request_id,
        "verification": verify_proof_bundle(bundle),
    }
