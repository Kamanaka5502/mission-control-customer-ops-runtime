from enum import Enum
from pydantic import BaseModel, Field
from typing import List, Dict, Any


class Outcome(str, Enum):
    ADMIT = "ADMIT"
    HOLD = "HOLD"
    ESCALATE = "ESCALATE"
    REFUSE = "REFUSE"


class CustomerRequest(BaseModel):
    customer_id: str
    workflow_id: str
    request_id: str
    requested_action: str
    business_context: str
    authority_present: bool = False
    scope_matched: bool = False
    evidence_present: bool = False
    evidence_fresh: bool = False
    risk_level: str = Field(default="medium", pattern="^(low|medium|high|critical)$")
    approval_required: bool = True
    metadata: Dict[str, Any] = {}


class RuntimeDecision(BaseModel):
    request_id: str
    workflow_id: str
    outcome: Outcome
    protected_effect_status: str
    no_bind_status: bool
    reason_codes: List[str]
    receipt_id: str
    replay_token: str
    customer_visible_summary: str


class Receipt(BaseModel):
    receipt_id: str
    request_id: str
    workflow_id: str
    requested_action: str
    outcome: Outcome | str
    protected_effect_status: str
    no_bind_status: bool
    reason_codes: List[str]
    replay_token: str
    public_hash: str
    notice: str
    request_snapshot_hash: str | None = None
    evidence_manifest_hash: str | None = None
    signature_algorithm: str = "hmac-sha256"
    signature_key_id: str = "development-receipt-key"
    signature: str | None = None
