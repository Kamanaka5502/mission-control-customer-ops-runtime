# Key Management

Mission Control uses explicit runtime keys for two signing paths:

- bearer-token authentication
- receipt and proof-bundle signatures

## Current signing material

Production requires non-default values of at least 32 characters for:

```text
AUTH_TOKEN_SECRET
RECEIPT_SIGNING_SECRET
```

Production also requires an explicit receipt signing key id:

```text
RECEIPT_SIGNING_KEY_ID
```

The receipt key id is embedded in receipts and proof bundles so verifiers can identify the correct verification key.

## Verify-only compatibility slots

During a planned key change, configure previous values as verify-only material:

```text
AUTH_TOKEN_PREVIOUS_SECRETS=old-auth-material
RECEIPT_SIGNING_PREVIOUS_KEYS=old-receipt-key:old-receipt-material
```

The runtime signs new tokens, receipts, and proof bundles with the current values. It can verify older artifacts with configured previous values.

## Receipt and proof verification

Receipt verification uses the `signature_key_id` embedded in the receipt.

Proof-bundle verification uses the `proof_signature_key_id` embedded in the bundle.

If the key id is unknown, verification fails closed.

## Planned key-change sequence

1. Add the current value to the matching previous-key setting.
2. Set a new current value and, for receipts, a new `RECEIPT_SIGNING_KEY_ID`.
3. Deploy.
4. Confirm new artifacts use the new key id.
5. Keep previous values only for the artifact lifetime that must still verify.
6. Remove previous values after the compatibility window ends.

## Production validation

Production startup rejects:

- empty/default signing values
- values shorter than 32 characters
- default receipt key id
- duplicate current and previous values
- malformed receipt previous-key entries

## Claim boundary

This repository validates runtime key configuration and supports planned verification compatibility. It does not replace customer-approved secret management, KMS/HSM policy, emergency key revocation, or organization-specific retention requirements.
