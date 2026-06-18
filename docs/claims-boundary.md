# Claims Boundary

Mission Control is a customer-operations execution-control runtime. Its value is in making operational movement explicit, reviewable, replayable, and auditable.

This document defines what the repository may claim, what it may not claim, and what must be proven before stronger production or customer-deployment claims are made.

## Allowed positioning

Mission Control may be described as:

- a production-candidate customer-operations runtime for controlled execution
- a customer-ops operational boundary runtime
- a buyer-demo and deployment-readiness system
- a runtime for workflow intake, evidence-aware review, controlled execution, receipt, replay, audit, and dashboard visibility
- a fail-closed execution-gate pattern for operational requests
- a repo-level hardened implementation with remaining production certification gates

## Current implemented claim lane

At repository level, Mission Control demonstrates:

- structured workflow intake
- request evaluation into `ADMIT`, `HOLD`, `ESCALATE`, or `REFUSE`
- review routing and lifecycle transitions
- controlled execution gating
- persisted receipts and replay endpoints
- audit trail visibility
- tenant header enforcement in production mode
- trusted-ingress requirement in production mode
- production setting validation
- defensive response headers
- schema versioning and migration path
- CI and CodeQL gates
- documented release and deployment-evidence process

## Production-candidate claim lane

Mission Control should only be described as a production-candidate runtime when the relevant controls are implemented, tested, and documented. The all-A target includes:

- authenticated intake and protected runtime mutation
- role-based access control
- tenant-scoped authorization across every runtime object
- immutable request snapshots
- evidence manifest integrity
- signed receipts with external verification
- tamper-evident audit ledger
- persistent receipt, replay, and proof bundle storage
- PostgreSQL-backed production profile
- endpoint-level API hardening
- execution safety checks at the moment of release
- production key management
- incident-response and operations procedures
- deployment readiness checklist

## Disallowed claims

Mission Control must not claim:

- full dimensional Elyria/VERITA stack custody
- true-zero formation custody
- full consequence-boundary authority
- production certification before audit, customer approval, or equivalent security review
- legal, medical, financial, or regulated authority
- customer deployment readiness without written scope and deployment evidence
- private Elyria/VERITA kernel exposure
- that unfinished roadmap items are implemented

## What Mission Control proves

When demonstrated honestly, this repository proves:

- controlled intake
- evidence-aware review path
- explicit runtime outcomes
- fail-closed execution gate behavior
- no protected effect on `REFUSE`
- receipt and replay surface
- audit trail visibility
- dashboard-based operational clarity
- tenant-aware runtime behavior where implemented

## What Mission Control does not prove by itself

This repository does not, by itself, prove:

- full production certification
- full external deployment hardening
- full identity-provider integration
- full customer security approval
- full legal, medical, or financial authority
- full Elyria/VERITA kernel protection
- dimensional consequence-boundary custody
- complete proof-chain custody without signed receipts and tamper-evident audit ledger implementation

## README language rule

The README must distinguish between:

1. implemented controls,
2. production-candidate roadmap controls, and
3. disallowed claims.

Any future README update must avoid implying that planned controls are already implemented.
