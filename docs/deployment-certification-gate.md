# Deployment Certification Gate

Mission Control separates repository readiness from production certification.

## Repository gate

The repository gate checks that required controls, docs, CI entries, and claim-boundary files are present.

Run:

```bash
python scripts/certify_deployment.py --repo-check-only
```

This is safe for CI because it does not certify a deployment. It only proves that the repository contains the expected readiness package.

## Certification gate

Production certification requires a completed evidence file for a specific deployment scope.

Run:

```bash
python scripts/certify_deployment.py --certify --evidence-file <completed-evidence-file>
```

The evidence file must include:

```text
certification_status: APPROVED
approved_scope: <specific deployment scope>
approved_commit: <commit sha>
approver: <person or approving authority>
approval_date: <date>
```

It must also include at least one approval signal:

```text
customer_security_approval: true
external_audit_approval: true
written_deployment_authorization: true
```

## Required claim boundary

Until certification evidence is complete, use:

```text
production-candidate operational runtime
```

Do not use:

```text
production certified
customer approved
externally audited
SOC2 ready
```

unless there is written evidence supporting that exact claim for the exact deployment scope.

## CI behavior

CI runs the repository gate only:

```text
deployment-certification-gate
```

That job must pass before merge. It confirms the gate exists and required repository evidence is present, but it does not certify production.
