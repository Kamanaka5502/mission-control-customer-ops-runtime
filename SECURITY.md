# Security Policy

Mission Control is a production-oriented customer operations runtime. Security reports should focus on issues that affect confidentiality, integrity, availability, tenant isolation, execution gating, evidence handling, replay integrity, or deployment boundary assumptions.

## Supported branch

Security review and fixes are handled against the default branch:

```text
main
```

## Reporting a vulnerability

Do not open a public issue for sensitive findings.

Report privately to the maintainer with:

- affected file or endpoint
- reproduction steps
- expected behavior
- observed behavior
- impact assessment
- suggested mitigation, if known

## Security boundaries

The runtime is designed to run behind authenticated ingress and tenant resolution infrastructure. Production mode requires:

- explicit tenant identity
- trusted ingress verification
- explicit actor role
- explicit CORS origins
- managed database configuration

The application rejects unsafe production configuration where these controls are absent.

## Non-goals

This repository does not replace a full external security stack. A complete deployment still requires an identity provider, API gateway or ingress layer, managed secrets, network boundary controls, rate limiting, logging, backup policy, and incident response process.

## Disclosure posture

Reports will be reviewed for reproducibility and material impact. Valid issues should be remediated through a pull request with tests or documented operational controls.
