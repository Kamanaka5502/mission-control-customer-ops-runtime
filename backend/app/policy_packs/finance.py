from app.models import CustomerRequest, Outcome
from app.policy_packs.base import PolicyPack, PolicyResult


class FinancePolicyPack(PolicyPack):
    name = "finance"
    description = "Finance workflow policy pack for payment and value-transfer operations."

    def evaluate(self, req: CustomerRequest) -> PolicyResult:
        reason_codes = ["POLICY_PACK_FINANCE"]
        reason_codes.append("AUTHORITY_PRESENT" if req.authority_present else "AUTHORITY_MISSING")
        reason_codes.append("SCOPE_MATCHED" if req.scope_matched else "SCOPE_MISMATCH")
        reason_codes.append("EVIDENCE_PRESENT" if req.evidence_present else "EVIDENCE_MISSING")
        reason_codes.append("EVIDENCE_FRESH" if req.evidence_fresh else "EVIDENCE_STALE")
        reason_codes.append(f"RISK_{req.risk_level.upper()}")

        if not req.authority_present:
            return PolicyResult(Outcome.REFUSE, "NOT_RELEASED", True, reason_codes + ["FINANCE_AUTHORITY_REQUIRED", "NO_BIND"])
        if req.risk_level in {"high", "critical"} or req.approval_required:
            return PolicyResult(Outcome.ESCALATE, "PENDING_FINANCE_APPROVAL", True, reason_codes + ["FINANCE_REVIEW_REQUIRED"])
        if not req.evidence_present or not req.evidence_fresh:
            return PolicyResult(Outcome.HOLD, "PENDING_EVIDENCE_REVIEW", True, reason_codes + ["FINANCE_EVIDENCE_REVIEW_REQUIRED"])
        return PolicyResult(Outcome.ADMIT, "AUTHORIZED_TO_PROCEED", False, reason_codes + ["FINANCE_ADMISSIBLE"])
