# Deployment Evidence Template

Use this template to record external deployment evidence. This document is intentionally separate from source code because A++ posture requires operational proof from the real environment.

## Deployment summary

- environment:
- deployment date:
- deployed commit:
- operator:
- API base URL:
- frontend URL:

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
CORS_ALLOW_ORIGINS=<explicit deployed origin>
```

## Validation commands

```bash
curl <api-base-url>/health
curl <api-base-url>/ready
curl <api-base-url>/schema-version
```

## Boundary smoke tests

- [ ] request without trusted ingress identity is denied
- [ ] request without tenant id is denied
- [ ] request with tenant mismatch is denied
- [ ] invalid actor role is denied
- [ ] REFUSE outcome cannot release protected action
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
