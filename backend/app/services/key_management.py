import os
from dataclasses import dataclass


DEFAULT_SECRET_VALUES = {
    "",
    "change-me",
    "changeme",
    "dev-secret",
    "default",
    "secret",
    "replace_with_32_plus_character_random_secret",
    "development-receipt-secret-not-for-production",
}
MIN_SECRET_LENGTH = 32


@dataclass(frozen=True)
class KeyMaterial:
    key_id: str
    secret: str


def _clean(value: str | None) -> str:
    return (value or "").strip()


def is_safe_secret(secret: str | None) -> bool:
    value = _clean(secret)
    return len(value) >= MIN_SECRET_LENGTH and value.lower() not in DEFAULT_SECRET_VALUES


def current_auth_secret() -> str:
    return os.getenv("AUTH_TOKEN_SECRET", "")


def previous_auth_secrets() -> list[str]:
    raw = os.getenv("AUTH_TOKEN_PREVIOUS_SECRETS", "")
    return [item.strip() for item in raw.split(",") if item.strip()]


def auth_verification_secrets() -> list[str]:
    secrets = [_clean(current_auth_secret())]
    secrets.extend(previous_auth_secrets())
    return [secret for secret in secrets if secret]


def current_receipt_key_id() -> str:
    return os.getenv("RECEIPT_SIGNING_KEY_ID", "development-receipt-key").strip() or "development-receipt-key"


def current_receipt_secret() -> str:
    return os.getenv("RECEIPT_SIGNING_SECRET", "development-receipt-secret-not-for-production")


def previous_receipt_keys() -> dict[str, str]:
    raw = os.getenv("RECEIPT_SIGNING_PREVIOUS_KEYS", "")
    keys: dict[str, str] = {}
    for item in [part.strip() for part in raw.split(",") if part.strip()]:
        if ":" not in item:
            continue
        key_id, secret = item.split(":", 1)
        key_id = key_id.strip()
        secret = secret.strip()
        if key_id and secret:
            keys[key_id] = secret
    return keys


def receipt_secret_for_key_id(key_id: str | None) -> str | None:
    candidate = _clean(key_id)
    if candidate == current_receipt_key_id():
        return current_receipt_secret()
    return previous_receipt_keys().get(candidate)


def receipt_verification_keys() -> dict[str, str]:
    keys = dict(previous_receipt_keys())
    keys[current_receipt_key_id()] = current_receipt_secret()
    return keys


def validate_key_settings() -> list[str]:
    issues: list[str] = []

    auth_current = _clean(current_auth_secret())
    if not is_safe_secret(auth_current):
        issues.append("AUTH_TOKEN_SECRET must be set to a non-default value of at least 32 characters")

    auth_previous = previous_auth_secrets()
    for index, secret in enumerate(auth_previous, start=1):
        if not is_safe_secret(secret):
            issues.append(f"AUTH_TOKEN_PREVIOUS_SECRETS item {index} must be non-default and at least 32 characters")
        if secret == auth_current:
            issues.append(f"AUTH_TOKEN_PREVIOUS_SECRETS item {index} must not duplicate AUTH_TOKEN_SECRET")

    receipt_current_key_id = current_receipt_key_id()
    receipt_current_secret = _clean(current_receipt_secret())
    if not receipt_current_key_id or receipt_current_key_id == "development-receipt-key":
        issues.append("RECEIPT_SIGNING_KEY_ID must be explicit and non-default")
    if not is_safe_secret(receipt_current_secret):
        issues.append("RECEIPT_SIGNING_SECRET must be set to a non-default value of at least 32 characters")

    previous_receipts = previous_receipt_keys()
    for key_id, secret in previous_receipts.items():
        if key_id == receipt_current_key_id:
            issues.append(f"RECEIPT_SIGNING_PREVIOUS_KEYS entry {key_id} must not duplicate RECEIPT_SIGNING_KEY_ID")
        if not is_safe_secret(secret):
            issues.append(f"RECEIPT_SIGNING_PREVIOUS_KEYS entry {key_id} must use a non-default secret of at least 32 characters")
        if secret == receipt_current_secret:
            issues.append(f"RECEIPT_SIGNING_PREVIOUS_KEYS entry {key_id} must not duplicate RECEIPT_SIGNING_SECRET")

    raw_previous_receipts = os.getenv("RECEIPT_SIGNING_PREVIOUS_KEYS", "")
    malformed_receipt_entries = [entry.strip() for entry in raw_previous_receipts.split(",") if entry.strip() and ":" not in entry]
    for entry in malformed_receipt_entries:
        issues.append(f"RECEIPT_SIGNING_PREVIOUS_KEYS entry {entry} must use key_id:secret format")

    return issues
