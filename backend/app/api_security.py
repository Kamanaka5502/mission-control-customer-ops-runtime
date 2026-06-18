import os
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


WRITE_METHODS = {"POST", "PUT", "PATCH"}
DEFAULT_BODY_LIMIT_BYTES = 256 * 1024
DEFAULT_RATE_LIMIT_REQUESTS = 120
DEFAULT_RATE_LIMIT_WINDOW_SECONDS = 60


@dataclass(frozen=True)
class ApiSecuritySettings:
    max_body_bytes: int = DEFAULT_BODY_LIMIT_BYTES
    rate_limit_requests: int = DEFAULT_RATE_LIMIT_REQUESTS
    rate_limit_window_seconds: int = DEFAULT_RATE_LIMIT_WINDOW_SECONDS


def _positive_int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return value if value > 0 else default


def api_security_settings() -> ApiSecuritySettings:
    return ApiSecuritySettings(
        max_body_bytes=_positive_int_env("MAX_REQUEST_BODY_BYTES", DEFAULT_BODY_LIMIT_BYTES),
        rate_limit_requests=_positive_int_env("RATE_LIMIT_REQUESTS", DEFAULT_RATE_LIMIT_REQUESTS),
        rate_limit_window_seconds=_positive_int_env("RATE_LIMIT_WINDOW_SECONDS", DEFAULT_RATE_LIMIT_WINDOW_SECONDS),
    )


class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_body_bytes: int | None = None):
        super().__init__(app)
        self.max_body_bytes = max_body_bytes or api_security_settings().max_body_bytes

    async def dispatch(self, request: Request, call_next):
        if request.method in WRITE_METHODS:
            raw_content_length = request.headers.get("content-length")
            if raw_content_length:
                try:
                    content_length = int(raw_content_length)
                except ValueError:
                    return JSONResponse(
                        status_code=400,
                        content={"access": "DENIED", "reason": "Invalid Content-Length header"},
                    )
                if content_length > self.max_body_bytes:
                    return JSONResponse(
                        status_code=413,
                        content={
                            "access": "DENIED",
                            "reason": "Request body exceeds configured limit",
                            "max_body_bytes": self.max_body_bytes,
                        },
                    )
        return await call_next(request)


class InMemoryRateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        *,
        limit: int | None = None,
        window_seconds: int | None = None,
    ):
        super().__init__(app)
        settings = api_security_settings()
        self.limit = limit or settings.rate_limit_requests
        self.window_seconds = window_seconds or settings.rate_limit_window_seconds
        self._hits: dict[str, Deque[float]] = defaultdict(deque)

    def _client_key(self, request: Request) -> str:
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        if request.client and request.client.host:
            return request.client.host
        return "unknown-client"

    async def dispatch(self, request: Request, call_next):
        key = self._client_key(request)
        now = time.monotonic()
        cutoff = now - self.window_seconds
        hits = self._hits[key]

        while hits and hits[0] <= cutoff:
            hits.popleft()

        if len(hits) >= self.limit:
            retry_after = max(1, int(self.window_seconds - (now - hits[0])))
            return JSONResponse(
                status_code=429,
                content={
                    "access": "DENIED",
                    "reason": "Rate limit exceeded",
                    "rate_limit_requests": self.limit,
                    "rate_limit_window_seconds": self.window_seconds,
                },
                headers={"Retry-After": str(retry_after)},
            )

        hits.append(now)
        response = await call_next(request)
        response.headers["x-rate-limit-limit"] = str(self.limit)
        response.headers["x-rate-limit-window-seconds"] = str(self.window_seconds)
        response.headers["x-request-body-limit-bytes"] = str(api_security_settings().max_body_bytes)
        return response
