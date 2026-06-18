# Deployment Evidence Template

Use this template to record external deployment evidence. This document is intentionally separate from source code because production certification requires operational proof from the real environment.

## Deployment summary

- environment:
- deployment date:
- deployed commit:
- operator:
- API base URL:
- frontend URL:

## Certification gate fields

These fields are machine-checkable by `scripts/certify_deployment.py`.

```text
certification_status: HOLD
approved_scope:
approved_commit:
approver:
approval_date:
customer_security_approval: false
external_audit_approval: false
written_deployment_authorization: false
```

Set `certification_status: APPROVED` only when the deployment scope has customer security approval, external audit approval, or equivalent written deployment authorization.

## External controls

- identity provider:
- ingress / API gateway:
- tenant resolution source:
- secrets manager:
- database service:
- logging destination:
- backup policy:
- rate limiting / WAF:

## Configuration proof

Record evidence that production mode is using required controls:

```text
APP_ENV=production
REQUIRE_TENANT_HEADER=true
REQUIRE_TRUSTED_INGRESS=true
AUTH_REQUIRED=true
CORS_ALLOW_ORIGINS=<explicit deployed origin>
RECEIPT_SIGNING_KEY_ID=<explicit key id>
```

## Validation commands

```bash
curl <api-base-url>/health
curl <api-base-url>/ready
curl <api-base-url>/schema-version
curl <api-base-url>/ops/monitoring
```

## Boundary smoke tests

- [ ] request without trusted ingress identity is denied
- [ ] request without tenant id is denied
- [ ] request with tenant mismatch is denied
- [ ] invalid actor role is denied
- [ ] REFUSE outcome cannot release protected action
- [ ] receipt verification succeeds
- [ ] proof bundle verification succeeds
- [ ] audit ledger verification succeeds
- [ ] correlation id appears in logs

## Rollback evidence

- rollback command or procedure:
- last known good commit:
- database rollback posture:
- operator notes:

## Result

```text
PASS / FAIL / HOLD
```

## Notes

Document assumptions, exclusions, and next action.
