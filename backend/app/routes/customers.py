from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.db_models import Customer, Workflow
from app.schemas import CustomerCreate, WorkflowCreate
from app.services.rbac import Role, get_actor_role, require_role
from app.services.tenant_guard import get_tenant_id, require_tenant_access

router = APIRouter()


@router.post("/customers")
def create_customer(
    payload: CustomerCreate,
    db: Session = Depends(get_db),
    role: Role = Depends(get_actor_role),
    tenant_id: str | None = Depends(get_tenant_id),
):
    require_role(role, {Role.ADMIN, Role.OPERATOR})
    require_tenant_access(payload.id, tenant_id)

    existing = db.get(Customer, payload.id)
    if existing:
        require_tenant_access(existing.id, tenant_id)
        return existing

    customer = Customer(id=payload.id, name=payload.name, industry=payload.industry)
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


@router.get("/customers")
def list_customers(
    db: Session = Depends(get_db),
    role: Role = Depends(get_actor_role),
    tenant_id: str | None = Depends(get_tenant_id),
):
    require_role(role, {Role.ADMIN, Role.REVIEWER, Role.OPERATOR, Role.AUDITOR})

    query = db.query(Customer).order_by(Customer.created_at.desc())
    if tenant_id:
        query = query.filter(Customer.id == tenant_id)
    return query.all()


@router.post("/workflows")
def create_workflow(
    payload: WorkflowCreate,
    db: Session = Depends(get_db),
    role: Role = Depends(get_actor_role),
    tenant_id: str | None = Depends(get_tenant_id),
):
    require_role(role, {Role.ADMIN, Role.OPERATOR})
    require_tenant_access(payload.customer_id, tenant_id)

    customer = db.get(Customer, payload.customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    existing = db.get(Workflow, payload.id)
    if existing:
        require_tenant_access(existing.customer_id, tenant_id)
        return existing

    workflow = Workflow(
        id=payload.id,
        customer_id=payload.customer_id,
        name=payload.name,
        description=payload.description,
    )
    db.add(workflow)
    db.commit()
    db.refresh(workflow)
    return workflow


@router.get("/workflows")
def list_workflows(
    db: Session = Depends(get_db),
    role: Role = Depends(get_actor_role),
    tenant_id: str | None = Depends(get_tenant_id),
):
    require_role(role, {Role.ADMIN, Role.REVIEWER, Role.OPERATOR, Role.AUDITOR})

    query = db.query(Workflow).order_by(Workflow.created_at.desc())
    if tenant_id:
        query = query.filter(Workflow.customer_id == tenant_id)
    return query.all()
