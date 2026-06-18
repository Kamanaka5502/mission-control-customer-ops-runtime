# Monitoring Profile

Mission Control exposes a monitoring profile for local validation and deployment readiness review.

## Endpoint

```text
GET /ops/monitoring
```

The response includes:

- service name
- generated timestamp
- environment
- health state
- database probe
- schema probe
- runtime counters
- alert checks
- incident handoff fields

## Related endpoints

```text
GET /health
GET /ready
GET /schema-version
GET /metrics
GET /ops/monitoring
```

## Health model

`healthy` means the API process is available and the database probe succeeds.

`degraded` means the API process responded but at least one required dependency probe failed.

## Alert checks

The built-in checks are intentionally simple and reviewable:

- `DATABASE_UNAVAILABLE`
- `SCHEMA_VERSION_DRIFT`
- `PENDING_REVIEW`
- `REFUSAL_EVENTS_PRESENT`

These checks are not a full observability stack. They provide repository-level evidence that the runtime exposes operational state needed for deployment review.

## Incident handoff

For any incident review, capture:

- correlation id
- request id
- timestamp
- actor id
- tenant id
- recent audit events
- current monitoring profile response
- current readiness response

## Claim boundary

This monitoring profile provides application-level status and runtime counters. Production deployment should connect these outputs to the customer-approved monitoring stack, alert routing, log retention, paging policy, and incident-management workflow.
