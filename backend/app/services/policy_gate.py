from app.models import CustomerRequest, Outcome


def evaluate_request(req: CustomerRequest):
    reason_codes = []

    reason_codes.append("AUTHORITY_PRESENT" if req.authority_present else "AUTHORITY_MISSING")
    reason_codes.append("SCOPE_MATCHED" if req.scope_matched else "SCOPE_MISMATCH")
    reason_codes.append("EVIDENCE_PRESENT" if req.evidence_present else "EVIDENCE_MISSING")
    reason_codes.append("EVIDENCE_FRESH" if req.evidence_fresh else "EVIDENCE_STALE")
    reason_codes.append(f"RISK_{req.risk_level.upper()}")

    if req.risk_level == "critical":
        return Outcome.ESCALATE, "PENDING_HIGH_AUTHORITY_REVIEW", True, reason_codes + ["CRITICAL_RISK_ESCALATION"]

    if not req.authority_present:
        return Outcome.REFUSE, "NOT_RELEASED", True, reason_codes + ["NO_BIND"]

    if not req.scope_matched:
        return Outcome.HOLD, "PENDING_SCOPE_REVIEW", True, reason_codes + ["SCOPE_REVIEW_REQUIRED"]

    if not req.evidence_present or not req.evidence_fresh:
        return Outcome.HOLD, "PENDING_EVIDENCE_REVIEW", True, reason_codes + ["EVIDENCE_REVIEW_REQUIRED"]

    if req.approval_required:
        return Outcome.ESCALATE, "PENDING_APPROVAL", True, reason_codes + ["APPROVAL_REQUIRED"]

    return Outcome.ADMIT, "AUTHORIZED_TO_PROCEED", False, reason_codes + ["RUNTIME_ADMISSIBLE"]
