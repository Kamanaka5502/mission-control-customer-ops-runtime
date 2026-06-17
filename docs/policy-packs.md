# Policy Packs

Policy packs make Mission Control adaptable across customer workflow domains.

Instead of one hardcoded rule path, the runtime can select a policy pack based on workflow type.

```text
workflow_id
  -> policy pack registry
  -> domain policy evaluation
  -> ADMIT / HOLD / ESCALATE / REFUSE
  -> receipt + replay + audit
```

## Included packs

- `cyber` — privileged access, production exceptions, security-impacting workflows
- `finance` — payment release, vendor approval, value-transfer workflows
- `healthcare` — clinical review and patient-impacting operational workflows

## Registry

Policy packs are registered in:

```text
backend/app/policy_packs/registry.py
```

Workflow mapping:

```text
security-exception -> cyber
payment-release -> finance
vendor-onboarding -> finance
clinical-review -> healthcare
```

## Forward-deployed value

This lets a deployed engineer adapt the runtime to a customer environment without rewriting the platform core.

New customers can receive new packs while preserving the same operational path:

```text
intake -> evidence -> policy pack -> review -> execution guard -> receipt -> replay -> audit
```
