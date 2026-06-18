# Execution Idempotency and Final Checks

Mission Control treats execution as a controlled one-way lifecycle transition.

## Behavior

When a request is released through:

```text
POST /ops/requests/{request_id}/execute
```

Mission Control performs final checks before changing the lifecycle state to `executed`.

The request can execute only when:

- a decision exists
- the decision is not `REFUSE`
- the lifecycle state is executable
- escalated or held requests have the required review state
- the current runtime evaluation still matches the stored decision outcome
- the current protected-effect status still matches the stored decision
- the current no-bind status still matches the stored decision

## Idempotent repeat behavior

After the first successful execution, repeated calls return the stored execution result with:

```json
{
  "idempotent_replay": true
}
```

Repeated calls do not create a second `execution_completed` event.

Instead, they record:

```text
execution_idempotent_replay
```

## Internal metadata

The stored execution result is kept under internal request metadata:

```text
execution_control
```

This internal metadata is excluded from request snapshot hashing so execution bookkeeping does not invalidate the original request snapshot.

## Claim boundary

This provides route-level execution idempotency for the repository runtime. Production deployments that run multiple API instances should add database-level locking, queue-level uniqueness, or an external idempotency store before claiming distributed exactly-once execution.
