import os
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send


WRITE_METHODS = {"POST", "PUT", "PATCH"}
DEFAULT_BODY_LIMIT_BYTES = 256 * 1024
DEFAULT_RATE_LIMIT_REQUESTS = 120
DEFAULT_RATE_LIMIT_WINDOW_SECONDS = 60
DEFAULT_TRUSTED_RATE_LIMIT_HEADER = "x-rate-limit-client"
TRUE_VALUES = {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class ApiSecuritySettings:
    max_body_bytes: int = DEFAULT_BODY_LIMIT_BYTES
    rate_limit_requests: int = DEFAULT_RATE_LIMIT_REQUESTS
    rate_limit_window_seconds: int = DEFAULT_RATE_LIMIT_WINDOW_SECONDS
    rate_limit_enabled: bool = False
    trusted_rate_limit_header: str = DEFAULT_TRUSTED_RATE_LIMIT_HEADER


def _positive_int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return value if value > 0 else default


def _enabled_env(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in TRUE_VALUES


def _production_mode() -> bool:
    return os.getenv("APP_ENV", "development").strip().lower() in {"production", "prod"}


def api_security_settings() -> ApiSecuritySettings:
    return ApiSecuritySettings(
        max_body_bytes=_positive_int_env("MAX_REQUEST_BODY_BYTES", DEFAULT_BODY_LIMIT_BYTES),
        rate_limit_requests=_positive_int_env("RATE_LIMIT_REQUESTS", DEFAULT_RATE_LIMIT_REQUESTS),
        rate_limit_window_seconds=_positive_int_env("RATE_LIMIT_WINDOW_SECONDS", DEFAULT_RATE_LIMIT_WINDOW_SECONDS),
        rate_limit_enabled=_enabled_env("RATE_LIMIT_ENABLED", default=_production_mode()),
        trusted_rate_limit_header=os.getenv("TRUSTED_RATE_LIMIT_HEADER", DEFAULT_TRUSTED_RATE_LIMIT_HEADER).strip().lower() or DEFAULT_TRUSTED_RATE_LIMIT_HEADER,
    )


async def _send_json_response(scope: Scope, receive: Receive, send: Send, *, status_code: int, content: dict[str, Any]) -> None:
    response = JSONResponse(status_code=status_code, content=content)
    await response(scope, receive, send)


class BodySizeLimitMiddleware:
    def __init__(self, app: ASGIApp, max_body_bytes: int | None = None):
        self.app = app
        self.max_body_bytes = max_body_bytes or api_security_settings().max_body_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope.get("type") != "http" or scope.get("method") not in WRITE_METHODS:
            await self.app(scope, receive, send)
            return

        headers = {key.decode("latin1").lower(): value.decode("latin1") for key, value in scope.get("headers", [])}
        raw_content_length = headers.get("content-length")
        if raw_content_length:
            try:
                content_length = int(raw_content_length)
            except ValueError:
                await _send_json_response(
                    scope,
                    receive,
                    send,
                    status_code=400,
                    content={"access": "DENIED", "reason": "Invalid Content-Length header"},
                )
                return
            if content_length > self.max_body_bytes:
                await _send_json_response(
                    scope,
                    receive,
                    send,
                    status_code=413,
                    content={
                        "access": "DENIED",
                        "reason": "Request body exceeds configured limit",
                        "max_body_bytes": self.max_body_bytes,
                    },
                )
                return

        buffered_messages: list[Message] = []
        total_body_bytes = 0
        while True:
            message = await receive()
            buffered_messages.append(message)
            if message.get("type") != "http.request":
                break

            body = message.get("body", b"") or b""
            total_body_bytes += len(body)
            if total_body_bytes > self.max_body_bytes:
                await _send_json_response(
                    scope,
                    receive,
                    send,
                    status_code=413,
                    content={
                        "access": "DENIED",
                        "reason": "Request body exceeds configured limit",
                        "max_body_bytes": self.max_body_bytes,
                    },
                )
                return

            if not message.get("more_body", False):
                break

        async def replay_receive() -> Message:
            if buffered_messages:
                return buffered_messages.pop(0)
            return {"type": "http.request", "body": b"", "more_body": False}

        await self.app(scope, replay_receive, send)


class InMemoryRateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        *,
        limit: int | None = None,
        window_seconds: int | None = None,
        enabled: bool | None = None,
        trusted_client_header: str | None = None,
    ):
        super().__init__(app)
        settings = api_security_settings()
        self.limit = limit or settings.rate_limit_requests
        self.window_seconds = window_seconds or settings.rate_limit_window_seconds
        self.enabled = settings.rate_limit_enabled if enabled is None else enabled
        self.trusted_client_header = (trusted_client_header or settings.trusted_rate_limit_header).lower()
        self._hits: dict[str, Deque[float]] = defaultdict(deque)

    def _client_key(self, request: Request) -> str:
        verified_ingress = request.headers.get("x-ingress-verified", "").strip().lower() == "true"
        if verified_ingress:
            injected_client = request.headers.get(self.trusted_client_header)
            if injected_client:
                return f"trusted:{injected_client.strip()[:128]}"
        if request.client and request.client.host:
            return f"peer:{request.client.host}"
        return "peer:unknown-client"

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Any]]):
        if not self.enabled:
            response = await call_next(request)
            response.headers["x-rate-limit-enabled"] = "false"
            response.headers["x-request-body-limit-bytes"] = str(api_security_settings().max_body_bytes)
            return response

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
                headers={"Retry-After": str(retry_after), "x-rate-limit-enabled": "true"},
            )

        hits.append(now)
        response = await call_next(request)
        response.headers["x-rate-limit-enabled"] = "true"
        response.headers["x-rate-limit-limit"] = str(self.limit)
        response.headers["x-rate-limit-window-seconds"] = str(self.window_seconds)
        response.headers["x-request-body-limit-bytes"] = str(api_security_settings().max_body_bytes)
        return response
