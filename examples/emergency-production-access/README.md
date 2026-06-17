# Example: Emergency Production Access

This example shows a concrete customer workflow moving through the runtime.

## Scenario

A customer requests temporary emergency access to a production system during an active incident.

## Files

- `request.json` — customer request intake
- `evidence.json` — incident evidence payload
- `decision-output.json` — runtime decision result
- `receipt.json` — receipt artifact
- `replay-same-condition.json` — replay under unchanged conditions
- `replay-changed-condition.json` — replay after authority/evidence conditions change

## Lifecycle

```text
request submitted
  -> evidence attached
  -> runtime detects critical risk
  -> outcome ESCALATE
  -> reviewer approves
  -> controlled execution releases only after lifecycle permits
  -> receipt generated
  -> same-condition replay matches
  -> changed-condition replay refuses inherited authorization posture
  -> audit trail preserves material events
```

## Why it matters

This is the class of workflow where a normal approval log is not enough. The system must know whether the request still has standing at the moment execution is attempted.
