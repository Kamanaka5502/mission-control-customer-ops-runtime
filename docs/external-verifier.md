# External Receipt Verifier

Mission Control includes a standalone verifier for signed receipt JSON files.

## Purpose

The verifier lets a reviewer validate a receipt without trusting live application memory or a running API server.

## Command

```bash
python scripts/verify_external_receipt.py path/to/receipt.json
```

With an explicit verification secret:

```bash
python scripts/verify_external_receipt.py path/to/receipt.json --secret "$RECEIPT_SIGNING_SECRET"
```

## Output

The verifier prints JSON containing:

- `valid`
- `hash_matches`
- `signature_matches`
- expected public hash
- provided public hash
- signature algorithm
- signature key id

## Failure cases

The verifier exits non-zero when:

- a signed receipt field is changed
- `public_hash` no longer matches the canonical receipt fields
- the signature does not match the public hash and verifier secret

## Claim boundary

This is an external receipt-verification package, not a customer production certificate. Production use requires approved key custody, rotation, and deployment controls.
