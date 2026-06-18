# API Security Controls

Mission Control includes API boundary controls for request size and request rate.

## Body-size limit

Write requests are rejected when the `Content-Length` header exceeds the configured limit.

Default:

```text
MAX_REQUEST_BODY_BYTES=262144
```

Oversized requests return:

```text
413 Request Entity Too Large
```

## Rate limit

Requests are limited per client key within a rolling in-memory window.

Defaults:

```text
RATE_LIMIT_REQUESTS=120
RATE_LIMIT_WINDOW_SECONDS=60
```

Exceeded requests return:

```text
429 Too Many Requests
```

The response includes a `Retry-After` header.

## Headers

Successful responses include:

```text
x-rate-limit-limit
x-rate-limit-window-seconds
x-request-body-limit-bytes
```

## Deployment note

The current limiter is process-local and appropriate for repository validation, local deployment, and single-process runtime demonstration. Multi-instance production deployment should use a shared limiter or authenticated ingress gateway enforcement.

## Claim boundary

These controls harden the API boundary but do not replace customer-approved ingress policy, WAF policy, distributed rate limiting, abuse monitoring, or incident-response procedures.
