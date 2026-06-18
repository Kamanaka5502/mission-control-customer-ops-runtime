# Receipt Signing

Mission Control receipts are signed so reviewers can detect receipt tampering outside the live API path.

## Implemented behavior

`build_receipt` produces receipts with:

- `public_hash`
- `signature_algorithm`
- `signature_key_id`
- `signature`

The public hash is produced from canonical receipt fields. The signature is an HMAC-SHA256 over the public hash.

## Verification behavior

Verification recomputes the public hash from the receipt fields and compares it against the provided hash. It then recomputes the HMAC signature and compares it against the provided signature.

A receipt is valid only when both checks pass:

```text
hash_matches == true
signature_matches == true
```

## Tamper behavior

Changing a signed receipt field causes verification failure. Examples include changing:

- requested action
- outcome
- protected effect status
- no-bind status
- reason codes
- request snapshot hash
- evidence manifest hash

## Production boundary

The repository includes a signing adapter and verifier for reviewer evaluation. Production use still requires customer-approved key storage, rotation, revocation, access control, and incident-response procedures.
