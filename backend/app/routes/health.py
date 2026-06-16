from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health():
    return {
        "status": "ok",
        "service": "mission-control-customer-ops-runtime",
        "mode": "customer-operations-platform"
    }
