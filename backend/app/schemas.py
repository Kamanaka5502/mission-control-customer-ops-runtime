from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
from app.models import Outcome


class CustomerCreate(BaseModel):
    id: str
    name: str
    industry: str = "general"


class WorkflowCreate(BaseModel):
    id: str
    customer_id: str
    name: str
    description: str = ""


class EvidenceCreate(BaseModel):
    id: str
    request_id: str
    label: str
    source: str
    freshness_status: str = "unknown"
    payload: Dict[str, Any] = {}


class RequestCreate(BaseModel):
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


class ReviewAction(BaseModel):
    actor: str = "reviewer"
    decision: str = Field(pattern="^(approve|hold|escalate|refuse)$")
    notes: str = ""


class AuditEventOut(BaseModel):
    id: str
    event_type: str
    actor: str
    detail: Dict[str, Any]


class RequestSummary(BaseModel):
    request_id: str
    workflow_id: str
    customer_id: str
    requested_action: str
    lifecycle_status: str
    risk_level: str
    approval_required: bool


class OperationsDashboard(BaseModel):
    total_requests: int
    admitted: int
    held: int
    escalated: int
    refused: int
    pending_review: int
    recent_requests: List[RequestSummary]
