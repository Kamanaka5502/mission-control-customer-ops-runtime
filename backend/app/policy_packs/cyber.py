from app.models import CustomerRequest, Outcome
from app.policy_packs.base import PolicyPack, PolicyResult


class CyberPolicyPack(PolicyPack):
    name = "cyber"
    description = "Cyber workflow policy pack for privileged access, exceptions, and production-impacting changes."

    def evaluate(self, req: CustomerRequest) -> PolicyResult:
        reason_codes = ["POLICY_PACK_CYBER"]
        reason_codes.append("AUTHORITY_PRESENT" if req.authority_present else "AUTHORITY_MISSING")
        reason_codes.append("SCOPE_MATCHED" if req.scope_matched else "SCOPE_MISMATCH")
        reason_codes.append("EVIDENCE_PRESENT" if req.evidence_present else "EVIDENCE_MISSING")
        reason_codes.append("EVIDENCE_FRESH" if req.evidence_fresh else "EVIDENCE_STALE")
        reason_codes.append(f"RISK_{req.risk_level.upper()}")

        if not req.authority_present:
            return PolicyResult(Outcome.REFUSE, "NOT_RELEASED", True, reason_codes + ["CYBER_AUTHORITY_REQUIRED", "NO_BIND"])
        if req.risk_level == "critical":
            return PolicyResult(Outcome.ESCALATE, "PENDING_HIGH_AUTHORITY_REVIEW", True, reason_codes + ["CYBER_CRITICAL_ESCALATION"])
        if not req.scope_matched:
            return PolicyResult(Outcome.HOLD, "PENDING_SCOPE_REVIEW", True, reason_codes + ["CYBER_SCOPE_REVIEW_REQUIRED"])
        if not req.evidence_present or not req.evidence_fresh:
            return PolicyResult(Outcome.HOLD, "PENDING_EVIDENCE_REVIEW", True, reason_codes + ["CYBER_EVIDENCE_REVIEW_REQUIRED"])
        if req.approval_required:
            return PolicyResult(Outcome.ESCALATE, "PENDING_SECURITY_APPROVAL", True, reason_codes + ["CYBER_APPROVAL_REQUIRED"])
        return PolicyResult(Outcome.ADMIT, "AUTHORIZED_TO_PROCEED", False, reason_codes + ["CYBER_ADMISSIBLE"])
