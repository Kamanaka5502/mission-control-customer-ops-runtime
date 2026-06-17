from app.models import CustomerRequest
from app.policy_packs import get_policy_pack


def evaluate_request(req: CustomerRequest):
    policy_pack = get_policy_pack(req.workflow_id)
    result = policy_pack.evaluate(req)

    reason_codes = [
        f"POLICY_PACK:{policy_pack.name}",
        *result.reason_codes,
    ]

    return (
        result.outcome,
        result.protected_effect_status,
        result.no_bind_status,
        reason_codes,
    )
