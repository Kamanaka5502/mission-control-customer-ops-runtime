# Authentication

Mission Control uses a staged authentication model.

Local development may use role headers for demos and tests. Production-candidate mode requires signed bearer tokens and refuses unsafe production startup when auth is not enabled or when the token secret is missing/default.

## Auth modes

### Development header mode

When `AUTH_REQUIRED` is not enabled and `APP_ENV` is not production, routes may accept:

- `x-actor-role`
- `x-actor-id`
- `x-actor-scopes`

This mode exists for local development and backward-compatible demos only.

### Bearer token mode

Bearer token mode is active when either is true:

- `APP_ENV=production`
- `AUTH_REQUIRED=true`

Protected routes then require:

```text
Authorization: Bearer <signed-token>
```

The token is a compact signed payload:

```text
base64url(canonical-json-payload).base64url(hmac-sha256-signature)
```

The payload includes:

- `sub`: actor id
- `role`: actor role
- `tenant_id`: optional tenant binding
- `scopes`: optional service-account scopes
- `exp`: optional expiry timestamp

## Signing secret

The token signer uses:

```text
AUTH_TOKEN_SECRET
```

Production startup refuses to run if:

- `AUTH_REQUIRED` is not enabled
- `AUTH_TOKEN_SECRET` is missing
- `AUTH_TOKEN_SECRET` is a default placeholder
- `AUTH_TOKEN_SECRET` is shorter than 32 characters

## Protected route behavior

When auth is required:

- missing bearer token returns `401`
- malformed token returns `401`
- invalid signature returns `401`
- expired token returns `401`
- invalid role returns `403`
- valid token with insufficient permission returns `403`

## Service accounts

Service accounts use the `service_account` role and explicit scopes.

Allowed service-account permission families are intentionally limited:

- `request:create`
- `evidence:attach`
- `request:read`
- `receipt:read`
- `replay:run`
- `audit:read`
- `dashboard:read`
- `execution_job:read`
- `execution_job:write`

Service accounts cannot review requests or directly release protected effects unless a later, explicitly scoped machine-action path is added and tested.

## Production boundary

Authentication is not the only production boundary. Production mode also requires:

- trusted ingress verification
- tenant header enforcement
- explicit CORS origins
- non-SQLite database configuration

See also:

- `docs/rbac.md`
- `docs/trusted-ingress-identity.md`
- `DEPLOYMENT_READINESS.md`
