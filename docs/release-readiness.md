# Release Readiness Notes

This repository is a production-oriented runtime prototype. Before public deployment, keep the claims bounded to implemented controls.

## Implemented controls

- explicit tenant filtering for execution job list/read/claim/complete/fail paths
- production mode requires explicit actor role instead of silently defaulting to operator
- production mode requires explicit tenant header instead of silently disabling tenant isolation
- production mode requires trusted ingress verification before actor role is accepted
- closed request controls: REFUSE outcomes remain closed and are not approvable through review
- closed request execution guard: closed requests return BLOCKED instead of releasing protected action
- closed request job guard: closed requests queue as BLOCKED jobs
- canonical receipt hashing for stable replay verification
- CI backend command uses an explicit module path
- PostgreSQL driver dependency is available for non-SQLite deployments
- production compose profile is present for API, frontend, and PostgreSQL
- regression tests cover tenant job boundary, closed request boundary, production guard behavior, and trusted ingress behavior

## Required before external production deployment

- deploy API on a private network behind authenticated ingress
- configure ingress to provide verified actor role and tenant id after authentication
- managed deployment credentials
- migration-managed schema changes
- environment-specific CORS allowlist
- structured log sink and retention policy
- rate limiting and abuse controls at the edge
- dependency scanning and container scanning

This document separates implemented runtime behavior from deployment requirements so the repository does not overclaim its posture.
