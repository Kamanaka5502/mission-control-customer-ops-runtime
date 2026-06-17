from app.models import CustomerRequest, Outcome
from app.services.policy_gate import evaluate_request


def make_request(**overrides):
    base = dict(
        customer_id="demo-customer",
        workflow_id="vendor-onboarding",
        request_id="REQ-TEST-001",
        requested_action="approve_vendor",
        business_context="Test request",
        authority_present=True,
        scope_matched=True,
        evidence_present=True,
        evidence_fresh=True,
        risk_level="low",
        approval_required=False,
        metadata={},
    )
    base.update(overrides)
    return CustomerRequest(**base)


def test_admit_when_all_conditions_hold():
    outcome, effect_status, no_bind, reason_codes = evaluate_request(make_request())
    assert outcome == Outcome.ADMIT
    assert effect_status == "AUTHORIZED_TO_PROCEED"
    assert no_bind is False
    assert "POLICY_PACK:finance" in reason_codes
    assert "FINANCE_ADMISSIBLE" in reason_codes


def test_refuse_when_authority_missing():
    outcome, effect_status, no_bind, reason_codes = evaluate_request(make_request(authority_present=False))
    assert outcome == Outcome.REFUSE
    assert effect_status == "NOT_RELEASED"
    assert no_bind is True
    assert "NO_BIND" in reason_codes


def test_hold_when_evidence_needs_review():
    outcome, effect_status, no_bind, reason_codes = evaluate_request(make_request(evidence_fresh=False))
    assert outcome == Outcome.HOLD
    assert effect_status == "PENDING_EVIDENCE_REVIEW"
    assert no_bind is True
    assert "FINANCE_EVIDENCE_REVIEW_REQUIRED" in reason_codes


def test_escalate_critical_risk_finance_pack():
    outcome, effect_status, no_bind, reason_codes = evaluate_request(make_request(risk_level="critical"))
    assert outcome == Outcome.ESCALATE
    assert effect_status == "PENDING_FINANCE_APPROVAL"
    assert no_bind is True
    assert "POLICY_PACK:finance" in reason_codes
    assert "FINANCE_REVIEW_REQUIRED" in reason_codes


def test_cyber_policy_pack_for_security_exception():
    req = make_request(
        workflow_id="security-exception",
        risk_level="critical",
        approval_required=True,
    )
    outcome, effect_status, no_bind, reason_codes = evaluate_request(req)
    assert outcome == Outcome.ESCALATE
    assert effect_status == "PENDING_HIGH_AUTHORITY_REVIEW"
    assert no_bind is True
    assert "POLICY_PACK:cyber" in reason_codes
    assert "CYBER_CRITICAL_ESCALATION" in reason_codes


def test_healthcare_policy_pack_for_clinical_review():
    req = make_request(
        workflow_id="clinical-review",
        risk_level="medium",
        approval_required=True,
    )
    outcome, effect_status, no_bind, reason_codes = evaluate_request(req)
    assert outcome == Outcome.ESCALATE
    assert effect_status == "PENDING_CLINICAL_SIGNOFF"
    assert no_bind is True
    assert "POLICY_PACK:healthcare" in reason_codes
    assert "CLINICAL_SIGNOFF_REQUIRED" in reason_codes
