from app.models import CustomerRequest, Outcome
from app.policy_packs.base import PolicyPack, PolicyResult


class HealthcarePolicyPack(PolicyPack):
    name = "healthcare"
    description = "Healthcare workflow policy pack for clinical or patient-impacting operational decisions."

    def evaluate(self, req: CustomerRequest) -> PolicyResult:
        reason_codes = ["POLICY_PACK_HEALTHCARE"]
        reason_codes.append("AUTHORITY_PRESENT" if req.authority_present else "AUTHORITY_MISSING")
        reason_codes.append("SCOPE_MATCHED" if req.scope_matched else "SCOPE_MISMATCH")
        reason_codes.append("EVIDENCE_PRESENT" if req.evidence_present else "EVIDENCE_MISSING")
        reason_codes.append("EVIDENCE_FRESH" if req.evidence_fresh else "EVIDENCE_STALE")
        reason_codes.append(f"RISK_{req.risk_level.upper()}")

        if not req.authority_present:
            return PolicyResult(Outcome.REFUSE, "NOT_RELEASED", True, reason_codes + ["CLINICAL_AUTHORITY_REQUIRED", "NO_BIND"])
        if not req.evidence_present or not req.evidence_fresh:
            return PolicyResult(Outcome.HOLD, "PENDING_CLINICAL_EVIDENCE_REVIEW", True, reason_codes + ["CLINICAL_EVIDENCE_REQUIRED"])
        if req.risk_level in {"medium", "high", "critical"} or req.approval_required:
            return PolicyResult(Outcome.ESCALATE, "PENDING_CLINICAL_SIGNOFF", True, reason_codes + ["CLINICAL_SIGNOFF_REQUIRED"])
        return PolicyResult(Outcome.ADMIT, "AUTHORIZED_TO_PROCEED", False, reason_codes + ["HEALTHCARE_ADMISSIBLE"])
