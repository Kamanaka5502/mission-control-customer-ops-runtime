import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "certify_deployment.py"


def test_repository_deployment_gate_passes():
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--repo-check-only"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Repository gate" in result.stdout


def test_certification_requires_approval_evidence():
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--certify"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert "certification evidence file is required" in result.stdout


def test_certification_accepts_explicit_approved_evidence(tmp_path):
    evidence = tmp_path / "deployment-evidence.md"
    evidence.write_text(
        "\n".join(
            [
                "certification_status: APPROVED",
                "approved_scope: test deployment scope",
                "approved_commit: abc123",
                "approver: test approver",
                "approval_date: 2026-06-18",
                "customer_security_approval: true",
                "external_audit_approval: false",
                "written_deployment_authorization: false",
            ]
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--certify", "--evidence-file", str(evidence)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Certification evidence gate" in result.stdout
