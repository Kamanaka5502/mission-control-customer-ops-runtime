from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.responses import JSONResponse

from app.api_security import BodySizeLimitMiddleware, InMemoryRateLimitMiddleware


def body_limit_client(max_body_bytes: int = 16) -> TestClient:
    app = FastAPI()
    app.add_middleware(BodySizeLimitMiddleware, max_body_bytes=max_body_bytes)

    @app.post("/intake")
    async def intake():
        return {"status": "ok"}

    return TestClient(app)


def rate_limit_client(limit: int = 2, window_seconds: int = 60, enabled: bool = True) -> TestClient:
    app = FastAPI()
    app.add_middleware(InMemoryRateLimitMiddleware, limit=limit, window_seconds=window_seconds, enabled=enabled)

    @app.get("/health")
    async def health():
        return JSONResponse({"status": "ok"})

    return TestClient(app)


def test_body_size_limit_rejects_oversized_request():
    client = body_limit_client(max_body_bytes=16)

    response = client.post(
        "/intake",
        content=b"x" * 32,
        headers={"content-type": "application/octet-stream"},
    )

    assert response.status_code == 413
    assert response.json()["access"] == "DENIED"
    assert response.json()["reason"] == "Request body exceeds configured limit"


def test_body_size_limit_accepts_request_within_limit():
    client = body_limit_client(max_body_bytes=16)

    response = client.post(
        "/intake",
        content=b"x" * 8,
        headers={"content-type": "application/octet-stream"},
    )

    assert response.status_code == 200


def test_rate_limit_blocks_excess_requests_when_enabled():
    client = rate_limit_client(limit=2, window_seconds=60, enabled=True)

    assert client.get("/health", headers={"x-forwarded-for": "203.0.113.10"}).status_code == 200
    assert client.get("/health", headers={"x-forwarded-for": "203.0.113.10"}).status_code == 200
    response = client.get("/health", headers={"x-forwarded-for": "203.0.113.10"})

    assert response.status_code == 429
    assert response.json()["access"] == "DENIED"
    assert response.headers["Retry-After"]


def test_rate_limit_is_client_scoped_when_enabled():
    client = rate_limit_client(limit=1, window_seconds=60, enabled=True)

    assert client.get("/health", headers={"x-forwarded-for": "203.0.113.20"}).status_code == 200
    assert client.get("/health", headers={"x-forwarded-for": "203.0.113.21"}).status_code == 200
    assert client.get("/health", headers={"x-forwarded-for": "203.0.113.20"}).status_code == 429


def test_rate_limit_can_be_disabled_for_local_test_runtime():
    client = rate_limit_client(limit=1, window_seconds=60, enabled=False)

    assert client.get("/health", headers={"x-forwarded-for": "203.0.113.30"}).status_code == 200
    assert client.get("/health", headers={"x-forwarded-for": "203.0.113.30"}).status_code == 200
    assert client.get("/health", headers={"x-forwarded-for": "203.0.113.30"}).headers["x-rate-limit-enabled"] == "false"
