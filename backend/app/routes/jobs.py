from datetime import datetime
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.db_models import Decision, ExecutionJob, OperationRequest
from app.services.audit import record_event
from app.services.rbac import Role, get_actor_role, require_role
from app.services.tenant_guard import get_tenant_id, get_request_for_tenant

router = APIRouter()


def job_to_dict(job: ExecutionJob):
    return {
        "id": job.id,
        "request_id": job.request_id,
        "status": job.status,
        "worker_id": job.worker_id,
        "failure_reason": job.failure_reason,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
    }


def get_job_for_tenant(db: Session, job_id: str, tenant_id: str | None) -> ExecutionJob:
    job = db.get(ExecutionJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Execution job not found")
    get_request_for_tenant(db, job.request_id, tenant_id)
    return job


@router.post("/jobs/{request_id}/queue")
def queue_execution_job(
    request_id: str,
    db: Session = Depends(get_db),
    role: Role = Depends(get_actor_role),
    tenant_id: str | None = Depends(get_tenant_id),
):
    require_role(role, {Role.ADMIN, Role.OPERATOR})

    operation = get_request_for_tenant(db, request_id, tenant_id)
    decision = db.query(Decision).filter(Decision.request_id == request_id).first()
    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")

    allowed_statuses = {"ready_to_execute", "approved_for_execution"}
    if operation.lifecycle_status not in allowed_statuses:
        job = ExecutionJob(
            id=f"job-{uuid4().hex[:12]}",
            request_id=request_id,
            status="BLOCKED",
            failure_reason="Request is not in an executable lifecycle state.",
        )
        db.add(job)
        db.commit()
        record_event(db, request_id, "execution_job_blocked", actor=role.value, detail={"job_id": job.id})
        return job_to_dict(job)

    if decision.outcome != "ADMIT" and operation.lifecycle_status != "approved_for_execution":
        job = ExecutionJob(
            id=f"job-{uuid4().hex[:12]}",
            request_id=request_id,
            status="BLOCKED",
            failure_reason="Runtime decision is not executable without review approval.",
        )
        db.add(job)
        db.commit()
        record_event(db, request_id, "execution_job_blocked", actor=role.value, detail={"job_id": job.id})
        return job_to_dict(job)

    job = ExecutionJob(
        id=f"job-{uuid4().hex[:12]}",
        request_id=request_id,
        status="QUEUED",
    )
    operation.lifecycle_status = "queued_for_execution"
    db.add(job)
    db.commit()
    record_event(db, request_id, "execution_job_queued", actor=role.value, detail={"job_id": job.id})
    return job_to_dict(job)


@router.get("/jobs")
def list_execution_jobs(
    db: Session = Depends(get_db),
    role: Role = Depends(get_actor_role),
    tenant_id: str | None = Depends(get_tenant_id),
):
    require_role(role, {Role.ADMIN, Role.REVIEWER, Role.OPERATOR, Role.AUDITOR})
    query = db.query(ExecutionJob).join(OperationRequest, ExecutionJob.request_id == OperationRequest.id)
    if tenant_id:
        query = query.filter(OperationRequest.customer_id == tenant_id)
    jobs = query.order_by(ExecutionJob.created_at.desc()).all()
    return [job_to_dict(job) for job in jobs]


@router.get("/jobs/{job_id}")
def get_execution_job(
    job_id: str,
    db: Session = Depends(get_db),
    role: Role = Depends(get_actor_role),
    tenant_id: str | None = Depends(get_tenant_id),
):
    require_role(role, {Role.ADMIN, Role.REVIEWER, Role.OPERATOR, Role.AUDITOR})
    job = get_job_for_tenant(db, job_id, tenant_id)
    return job_to_dict(job)


@router.post("/jobs/{job_id}/claim")
def claim_execution_job(
    job_id: str,
    worker_id: str = "worker-local",
    db: Session = Depends(get_db),
    role: Role = Depends(get_actor_role),
    tenant_id: str | None = Depends(get_tenant_id),
):
    require_role(role, {Role.ADMIN, Role.OPERATOR})

    job = get_job_for_tenant(db, job_id, tenant_id)
    if job.status != "QUEUED":
        raise HTTPException(status_code=409, detail="Only QUEUED jobs can be claimed")

    job.status = "RUNNING"
    job.worker_id = worker_id
    job.started_at = datetime.utcnow()
    db.commit()
    record_event(db, job.request_id, "execution_job_running", actor=role.value, detail={"job_id": job.id, "worker_id": worker_id})
    return job_to_dict(job)


@router.post("/jobs/{job_id}/complete")
def complete_execution_job(
    job_id: str,
    db: Session = Depends(get_db),
    role: Role = Depends(get_actor_role),
    tenant_id: str | None = Depends(get_tenant_id),
):
    require_role(role, {Role.ADMIN, Role.OPERATOR})

    job = get_job_for_tenant(db, job_id, tenant_id)
    if job.status != "RUNNING":
        raise HTTPException(status_code=409, detail="Only RUNNING jobs can be completed")

    operation = get_request_for_tenant(db, job.request_id, tenant_id)
    job.status = "COMPLETED"
    job.completed_at = datetime.utcnow()
    operation.lifecycle_status = "executed"
    db.commit()
    record_event(db, job.request_id, "execution_job_completed", actor=role.value, detail={"job_id": job.id})
    return job_to_dict(job)


@router.post("/jobs/{job_id}/fail")
def fail_execution_job(
    job_id: str,
    failure_reason: str = "Execution failed",
    db: Session = Depends(get_db),
    role: Role = Depends(get_actor_role),
    tenant_id: str | None = Depends(get_tenant_id),
):
    require_role(role, {Role.ADMIN, Role.OPERATOR})

    job = get_job_for_tenant(db, job_id, tenant_id)
    if job.status not in {"QUEUED", "RUNNING"}:
        raise HTTPException(status_code=409, detail="Only QUEUED or RUNNING jobs can fail")

    job.status = "FAILED"
    job.failure_reason = failure_reason
    job.completed_at = datetime.utcnow()
    db.commit()
    record_event(db, job.request_id, "execution_job_failed", actor=role.value, detail={"job_id": job.id, "failure_reason": failure_reason})
    return job_to_dict(job)
