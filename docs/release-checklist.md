# Release Checklist

Use this checklist before merging or tagging a release candidate.

## Code validation

- [ ] backend tests pass
- [ ] frontend build passes
- [ ] production compose config validates
- [ ] CodeQL completes successfully
- [ ] database migrations apply cleanly

## Runtime boundary validation

- [ ] production mode rejects SQLite
- [ ] production mode requires explicit CORS origins
- [ ] production mode requires tenant enforcement
- [ ] production mode requires trusted ingress enforcement
- [ ] trusted actor role is required in production
- [ ] tenant mismatch remains denied
- [ ] closed/REFUSE requests cannot release protected action
- [ ] sensitive runtime routes emit `Cache-Control: no-store`

## Deployment validation

- [ ] API is behind authenticated ingress
- [ ] public traffic cannot directly set trusted identity headers
- [ ] tenant identity is resolved upstream
- [ ] secrets are managed outside source control
- [ ] database is managed and backed up
- [ ] logs preserve correlation ids
- [ ] rollback path is documented

## Evidence

Attach or link:

- CI run
- CodeQL run
- migration command output
- deployment configuration summary
- smoke test output
- rollback notes
