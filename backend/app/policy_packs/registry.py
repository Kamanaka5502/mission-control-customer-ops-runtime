from app.policy_packs.cyber import CyberPolicyPack
from app.policy_packs.finance import FinancePolicyPack
from app.policy_packs.healthcare import HealthcarePolicyPack

POLICY_PACKS = {
    "cyber": CyberPolicyPack(),
    "finance": FinancePolicyPack(),
    "healthcare": HealthcarePolicyPack(),
}

WORKFLOW_POLICY_MAP = {
    "security-exception": "cyber",
    "payment-release": "finance",
    "vendor-onboarding": "finance",
    "clinical-review": "healthcare",
}


def list_policy_packs():
    return [
        {"name": pack.name, "description": pack.description}
        for pack in POLICY_PACKS.values()
    ]


def get_policy_pack(workflow_id: str):
    pack_name = WORKFLOW_POLICY_MAP.get(workflow_id, "cyber")
    return POLICY_PACKS[pack_name]
