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
    assert "RUNTIME_ADMISSIBLE" in reason_codes


def test_refuse_when_authority_missing():
    outcome, effect_status, no_bind, reason_codes = evaluate_request(make_request(authority_present=False))
    assert outcome == Outcome.REFUSE
    assert effect_status == "NOT_RELEASED"
    assert no_bind is True


def test_hold_when_evidence_needs_review():
    outcome, effect_status, no_bind, reason_codes = evaluate_request(make_request(evidence_fresh=False))
    assert outcome == Outcome.HOLD
    assert effect_status == "PENDING_EVIDENCE_REVIEW"
    assert no_bind is True


def test_escalate_critical_risk():
    outcome, effect_status, no_bind, reason_codes = evaluate_request(make_request(risk_level="critical"))
    assert outcome == Outcome.ESCALATE
    assert effect_status == "PENDING_HIGH_AUTHORITY_REVIEW"
    assert no_bind is True
