#!/usr/bin/env python3
"""Deployment readiness checker.

This script reports whether the repository contains the expected documentation,
scripts, tests, and deployment artifacts for the all-A production-candidate lane.

By default it prints a report and exits 0 so it can be used during staged
implementation without breaking development. Use --strict to fail when required
items are missing.
"""

from __future__ import annotations

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "docs/authentication.md",
    "docs/rbac.md",
    "docs/tenant-isolation.md",
    "docs/request-snapshots.md",
    "docs/evidence-integrity.md",
    "docs/receipt-signing.md",
    "docs/external-verifier.md",
    "docs/audit-ledger.md",
    "docs/persistent-proof-store.md",
    "docs/postgres-production.md",
    "docs/api-security.md",
    "docs/execution-safety.md",
    "docs/key-management.md",
    "docs/operations-runbook.md",
    "docs/threat-model.md",
    "docs/claims-boundary.md",
    "DEPLOYMENT_READINESS.md",
]

REQUIRED_SCRIPTS = [
    "scripts/verify_receipts.py",
    "scripts/verify_external_receipt.py",
    "scripts/verify_audit_ledger.py",
]

REQUIRED_TEST_NAMES = [
    "test_auth_required_for_protected_routes",
    "test_rbac_requester_cannot_approve",
    "test_rbac_reviewer_cannot_execute_without_permission",
    "test_auditor_cannot_mutate_state",
    "test_tenant_a_cannot_read_tenant_b_request",
    "test_tenant_a_cannot_replay_tenant_b_receipt",
    "test_request_snapshot_is_immutable",
    "test_receipt_binds_snapshot_digest",
    "test_receipt_binds_evidence_manifest_digest",
    "test_receipt_signature_verifies",
    "test_tampered_receipt_fails_verification",
    "test_tampered_evidence_fails_verification",
    "test_audit_ledger_detects_edit",
    "test_audit_ledger_detects_delete",
    "test_execution_rechecks_changed_conditions",
    "test_stale_approval_refuses_execution",
    "test_revoked_authority_refuses_execution",
    "test_duplicate_execution_idempotent",
    "test_rate_limit_blocks_abuse",
    "test_production_startup_refuses_default_secret",
    "test_deployment_readiness_package_present",
]

CONFIG_HINTS = [
    "docker-compose.prod.yml",
    "backend/alembic.ini",
    "backend/migrations/env.py",
]


def exists(path: str) -> bool:
    return (ROOT / path).exists()


def collect_test_text() -> str:
    candidates = []
    for base in [ROOT / "backend" / "tests", ROOT / "tests"]:
        if base.exists():
            candidates.extend(base.rglob("test_*.py"))
    chunks = []
    for path in candidates:
        try:
            chunks.append(path.read_text(encoding="utf-8"))
        except UnicodeDecodeError:
            continue
    return "\n".join(chunks)


def section(title: str) -> None:
    print(f"\n{title}")
    print("-" * len(title))


def print_items(items: list[str], *, test_text: str | None = None) -> list[str]:
    missing: list[str] = []
    for item in items:
        if test_text is None:
            ok = exists(item)
        else:
            ok = item in test_text
        status = "OK" if ok else "MISSING"
        print(f"[{status}] {item}")
        if not ok:
            missing.append(item)
    return missing


def main() -> int:
    parser = argparse.ArgumentParser(description="Check deployment readiness artifacts.")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="exit non-zero if required readiness artifacts are missing",
    )
    args = parser.parse_args()

    missing: list[str] = []

    section("Required documentation")
    missing.extend(print_items(REQUIRED_FILES))

    section("Required verification scripts")
    missing.extend(print_items(REQUIRED_SCRIPTS))

    section("Deployment and migration hints")
    missing.extend(print_items(CONFIG_HINTS))

    section("Required A-grade test names")
    test_text = collect_test_text()
    missing.extend(print_items(REQUIRED_TEST_NAMES, test_text=test_text))

    section("Summary")
    if missing:
        print(f"Missing readiness items: {len(missing)}")
        for item in missing:
            print(f"- {item}")
        if args.strict:
            return 1
        print("\nNon-strict mode: reporting only. Use --strict to enforce.")
        return 0

    print("All readiness items are present.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
