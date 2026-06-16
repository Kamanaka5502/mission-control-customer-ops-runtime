import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from app.database import init_db, SessionLocal
from app.db_models import Customer, Workflow


def seed():
    init_db()
    db = SessionLocal()
    try:
        customer = db.get(Customer, "demo-customer")
        if not customer:
            db.add(Customer(id="demo-customer", name="Demo Customer", industry="operations"))

        workflow_data = [
            ("vendor-onboarding", "Vendor Onboarding", "Vendor review workflow."),
            ("payment-release", "Payment Release", "Finance review workflow."),
            ("security-exception", "Security Exception", "Security review workflow."),
        ]
        for workflow_id, name, description in workflow_data:
            if not db.get(Workflow, workflow_id):
                db.add(Workflow(id=workflow_id, customer_id="demo-customer", name=name, description=description))
        db.commit()
        print("Seeded demo customer and workflows.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
