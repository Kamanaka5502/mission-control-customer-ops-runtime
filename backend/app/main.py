import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import init_db
from app.middleware import CorrelationIdMiddleware
from app.production_settings import validate_production_settings
from app.security_headers import SecurityHeadersMiddleware
from app.routes.requests import router as requests_router
from app.routes.replay import router as replay_router
from app.routes.health import router as health_router
from app.routes.customers import router as customers_router
from app.routes.operations import router as operations_router
from app.routes.metrics import router as metrics_router
from app.routes.jobs import router as jobs_router


def cors_origins() -> list[str]:
    raw = os.getenv("CORS_ALLOW_ORIGINS")
    if not raw:
        return ["http://localhost:3000", "http://127.0.0.1:3000"]
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


validate_production_settings()

app = FastAPI(
    title="Mission Control: Customer Operations Runtime",
    version="0.7.0",
    description="Customer operations runtime with intake, persistence, review gates, controlled execution, receipts, replay, audit, metrics, dashboard APIs, production-boundary controls, authentication, and RBAC."
)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["authorization", "content-type", "x-actor-role", "x-actor-id", "x-actor-scopes", "x-tenant-id", "x-ingress-verified", "x-correlation-id"],
)


@app.on_event("startup")
def startup():
    init_db()


app.include_router(health_router, tags=["health"])
app.include_router(metrics_router, tags=["metrics"])
app.include_router(customers_router, prefix="/ops", tags=["customers-workflows"])
app.include_router(operations_router, prefix="/ops", tags=["operations"])
app.include_router(jobs_router, prefix="/ops", tags=["execution-jobs"])
app.include_router(requests_router, prefix="/requests", tags=["legacy-demo-requests"])
app.include_router(replay_router, prefix="/replay", tags=["legacy-demo-replay"])
