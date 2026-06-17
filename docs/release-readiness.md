# Release Readiness Notes

This repository is a production-oriented runtime prototype. Before public deployment, keep the claims bounded to implemented controls.

Required release controls:

- authenticated access at the edge
- explicit actor identity rather than trusted demo headers
- explicit tenant boundary on customer-owned resources
- signed receipts with managed deployment secrets
- hashed evidence payload manifests
- no execution path for refused requests
- passing backend and frontend CI
- PostgreSQL deployment profile
- migration-managed schema changes

This document separates implemented runtime behavior from deployment requirements so the repository does not overclaim its posture.
