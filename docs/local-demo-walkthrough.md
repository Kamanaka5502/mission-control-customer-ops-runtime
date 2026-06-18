# Local Demo Walkthrough

This walkthrough is the recommended path for recording the README demo GIF.

## Start the stack

From the repository root:

```bash
docker compose up --build
```

Open:

```text
Frontend: http://localhost:3000
API docs: http://localhost:8000/docs
Health: http://localhost:8000/health
```

## Run the scripted walkthrough

In a second terminal:

```bash
python scripts/local_demo_walkthrough.py
```

The script creates a fresh demo customer, workflow, and request, then exercises:

```text
customer -> workflow -> request evaluation -> evidence -> review -> execution -> receipt -> replay -> audit verification -> proof bundle -> dashboard
```

## GIF capture sequence

Recommended 20-40 second recording path:

```text
1. Show dashboard landing state.
2. Submit or display the generated demo request.
3. Show runtime decision: ESCALATE for critical-risk emergency access.
4. Approve review.
5. Release controlled execution.
6. Open receipt and replay result.
7. Open audit verification and proof bundle verification.
8. Return to dashboard summary.
```

Recommended output path:

```text
assets/demo-walkthrough.gif
```

## Proof points to show

During capture, highlight:

- request is structured and persisted
- critical-risk request escalates before release
- review approval changes lifecycle state
- execution is controlled by lifecycle state
- receipt is generated
- same-condition replay matches
- changed-condition replay refuses inherited authorization posture
- audit ledger verifies
- proof bundle verifies
- dashboard summarizes runtime state

## Claim boundary

The local walkthrough demonstrates repository functionality in a local runtime. It is not production certification, customer deployment approval, external audit, or live customer evidence retention.
