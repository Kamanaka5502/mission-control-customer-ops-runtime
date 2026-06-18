#!/usr/bin/env python3
"""Deployment certification gate.

This script separates repository readiness from production certification.
Repository checks can pass in CI. Production certification requires explicit external
or customer approval evidence for a specific deployment scope.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_REPO_FILES = [
    ".github/workflows/ci.yml",
    ".env.production.example",
    "docker-compose.prod.yml",
    "DEPLOYMENT_READINESS.md",
    "docs/claims-boundary.md",
    "docs/threat-model.md",
    "docs/operations-runbook.md",
    "docs/monitoring-profile.md",
    "docs/incident-response.md",
    "docs/postgres-ci.md",
    "docs/key-management.md",
    "docs/api-security.md",
    "docs/deployment-evidence-template.md",
    "docs/release-checklist.md",
]

REQUIRED_CI_MARKERS = [
    "backend-postgres",
    "CodeQL",
    "docker compose -f docker-compose.prod.yml config",
]

REQUIRED_APPROVAL_FIELDS = [
    "certification_status",
    "approved_scope",
    "approved_commit",
    "approver",
    "approval_date",
]

APPROVAL_SIGNALS = [
    "customer_security_approval",
    "external_audit_approval",
    "written_deployment_authorization",
]


def read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def parse_evidence(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        fields[key.strip().lower()] = value.strip()
    return fields


def truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"true", "yes", "approved", "pass", "1"}


def repository_issues() -> list[str]:
    issues: list[str] = []
    for relative in REQUIRED_REPO_FILES:
        if not (ROOT / relative).exists():
            issues.append(f"missing required file: {relative}")

    workflow_text = read(ROOT / ".github/workflows/ci.yml")
    for marker in REQUIRED_CI_MARKERS:
        if marker not in workflow_text:
            issues.append(f"missing CI marker: {marker}")

    readiness_text = read(ROOT / "DEPLOYMENT_READINESS.md")
    if "not production-certified" not in readiness_text:
        issues.append("DEPLOYMENT_READINESS.md must preserve the not-production-certified claim boundary")
    if "Production certification gate" not in readiness_text:
        issues.append("DEPLOYMENT_READINESS.md must document the production certification gate")

    return issues


def evidence_issues(evidence_file: Path | None) -> list[str]:
    if evidence_file is None:
        return ["certification evidence file is required for production certification"]
    text = read(evidence_file)
    if not text:
        return [f"certification evidence file not found or empty: {evidence_file}"]

    fields = parse_evidence(text)
    issues: list[str] = []
    for field in REQUIRED_APPROVAL_FIELDS:
        if not fields.get(field):
            issues.append(f"missing certification evidence field: {field}")

    if fields.get("certification_status", "").upper() != "APPROVED":
        issues.append("certification_status must be APPROVED")

    if not any(truthy(fields.get(signal)) for signal in APPROVAL_SIGNALS):
        issues.append("one approval signal must be true: customer_security_approval, external_audit_approval, or written_deployment_authorization")

    return issues


def print_report(title: str, issues: list[str]) -> None:
    print(title)
    print("-" * len(title))
    if not issues:
        print("OK")
        return
    for issue in issues:
        print(f"MISSING: {issue}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run deployment certification gate checks.")
    parser.add_argument("--evidence-file", type=Path, help="Path to completed deployment evidence file")
    parser.add_argument("--repo-check-only", action="store_true", help="Require repository gate checks only; does not certify production")
    parser.add_argument("--certify", action="store_true", help="Require repository checks and explicit approval evidence")
    args = parser.parse_args()

    repo_issues = repository_issues()
    print_report("Repository gate", repo_issues)

    cert_issues: list[str] = []
    if args.certify:
        cert_issues = evidence_issues(args.evidence_file)
        print()
        print_report("Certification evidence gate", cert_issues)
    elif args.evidence_file:
        cert_issues = evidence_issues(args.evidence_file)
        print()
        print_report("Certification evidence gate", cert_issues)
    else:
        print()
        print("Certification evidence gate")
        print("---------------------------")
        print("NOT CERTIFIED: no approval evidence requested or provided")

    if args.repo_check_only:
        return 1 if repo_issues else 0
    if args.certify:
        return 1 if repo_issues or cert_issues else 0

    print()
    print("Report-only mode. Use --repo-check-only for CI repository enforcement or --certify with evidence for production certification.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
