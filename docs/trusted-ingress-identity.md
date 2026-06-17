# Trusted Ingress Identity Boundary

Mission Control treats actor and tenant headers as trusted only when the API is running behind an authenticated ingress layer.

## Production requirement

In production mode, requests must include:

- `x-ingress-verified: true`
- `x-actor-role: admin | reviewer | operator | auditor`
- `x-tenant-id: <customer tenant id>`

The application rejects production requests that do not include trusted-ingress verification before role enforcement runs.

## Deployment rule

Do not expose the API directly to the public internet.

The API should run on a private network behind a gateway, reverse proxy, or service mesh that performs authentication first. That boundary must strip inbound identity headers from public traffic and inject the trusted headers only after authentication and tenant resolution.

## What this protects

- prevents production mode from silently defaulting to `operator`
- prevents production mode from silently disabling tenant isolation
- makes caller-controlled role and tenant headers invalid unless the ingress layer marks the request as verified

## What remains outside the app

This application does not replace an identity provider. The upstream ingress boundary is responsible for user login, session validation, organization membership, tenant mapping, and header injection.
