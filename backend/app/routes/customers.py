from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.db_models import Customer, Workflow
from app.schemas import CustomerCreate, WorkflowCreate

router = APIRouter()


@router.post("/customers")
def create_customer(payload: CustomerCreate, db: Session = Depends(get_db)):
    existing = db.get(Customer, payload.id)
    if existing:
        return existing
    customer = Customer(id=payload.id, name=payload.name, industry=payload.industry)
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


@router.get("/customers")
def list_customers(db: Session = Depends(get_db)):
    return db.query(Customer).order_by(Customer.created_at.desc()).all()


@router.post("/workflows")
def create_workflow(payload: WorkflowCreate, db: Session = Depends(get_db)):
    customer = db.get(Customer, payload.customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    existing = db.get(Workflow, payload.id)
    if existing:
        return existing
    workflow = Workflow(id=payload.id, customer_id=payload.customer_id, name=payload.name, description=payload.description)
    db.add(workflow)
    db.commit()
    db.refresh(workflow)
    return workflow


@router.get("/workflows")
def list_workflows(db: Session = Depends(get_db)):
    return db.query(Workflow).order_by(Workflow.created_at.desc()).all()
