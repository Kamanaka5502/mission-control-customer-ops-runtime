from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import init_db
from app.middleware import CorrelationIdMiddleware
from app.routes.requests import router as requests_router
from app.routes.replay import router as replay_router
from app.routes.health import router as health_router
from app.routes.customers import router as customers_router
from app.routes.operations import router as operations_router
from app.routes.metrics import router as metrics_router

app = FastAPI(
    title="Mission Control: Customer Operations Runtime",
    version="0.4.0",
    description="Customer operations runtime with intake, persistence, review gates, controlled execution, receipts, replay, audit, metrics, and dashboard APIs."
)

app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    init_db()


app.include_router(health_router, tags=["health"])
app.include_router(metrics_router, tags=["metrics"])
app.include_router(customers_router, prefix="/ops", tags=["customers-workflows"])
app.include_router(operations_router, prefix="/ops", tags=["operations"])
app.include_router(requests_router, prefix="/requests", tags=["legacy-demo-requests"])
app.include_router(replay_router, prefix="/replay", tags=["legacy-demo-replay"])
