from fastapi import FastAPI
from app.routes.requests import router as requests_router
from app.routes.replay import router as replay_router
from app.routes.health import router as health_router

app = FastAPI(
    title="Mission Control: Customer Operations Runtime",
    version="0.1.0",
    description="Customer operations runtime with request intake, approval gates, receipts, and replay."
)

app.include_router(health_router, tags=["health"])
app.include_router(requests_router, prefix="/requests", tags=["requests"])
app.include_router(replay_router, prefix="/replay", tags=["replay"])
