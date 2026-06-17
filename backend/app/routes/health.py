import os
from fastapi import APIRouter, HTTPException
from sqlalchemy import text
from app.database import SessionLocal

router = APIRouter()

SERVICE_NAME = "mission-control-customer-ops-runtime"
SCHEMA_HEAD = "20260617_0001"


@router.get("/health")
def health():
    return {
        "status": "ok",
        "service": SERVICE_NAME,
        "mode": os.getenv("APP_MODE", "customer-operations-platform"),
        "environment": os.getenv("APP_ENV", "development"),
    }


@router.get("/ready")
def readiness():
    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "not_ready",
                "service": SERVICE_NAME,
                "database": "unavailable",
            },
        ) from exc
    finally:
        db.close()

    return {
        "status": "ready",
        "service": SERVICE_NAME,
        "database": "available",
    }


@router.get("/schema-version")
def schema_version():
    db = SessionLocal()
    try:
        current = db.execute(text("SELECT version_num FROM alembic_version")).scalar_one_or_none()
    except Exception:
        current = None
    finally:
        db.close()

    return {
        "service": SERVICE_NAME,
        "schema_head": SCHEMA_HEAD,
        "schema_version": current,
        "migration_managed": current is not None,
        "up_to_date": current == SCHEMA_HEAD,
    }
