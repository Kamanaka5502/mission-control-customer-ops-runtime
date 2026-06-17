# Release Readiness Notes

This repository is a production-oriented runtime prototype. Before public deployment, keep the claims bounded to implemented controls.

## Implemented in this hardening pass

- explicit tenant filtering for execution job list/read/claim/complete/fail paths
- closed request controls: REFUSE outcomes remain closed and are not approvable through review
- closed request execution guard: closed requests return BLOCKED instead of releasing protected action
- closed request job guard: closed requests queue as BLOCKED jobs
- canonical receipt hashing for stable replay verification
- CI backend command uses an explicit module path
- regression tests for tenant job boundary and closed request boundary

## Required before external production deployment

- real authentication at the ingress layer
- signed actor identity instead of trusted demo headers
- managed secret storage for receipt signing keys
- migration-managed schema changes
- PostgreSQL production deployment profile
- environment-specific CORS configuration
- structured log sink and retention policy
- rate limiting and abuse controls at the edge
- dependency scanning and container scanning

This document separates implemented runtime behavior from deployment requirements so the repository does not overclaim its posture.
