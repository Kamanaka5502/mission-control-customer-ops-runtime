from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, Text, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    industry: Mapped[str] = mapped_column(String, default="general")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    workflows: Mapped[list["Workflow"]] = relationship(back_populates="customer")


class Workflow(Base):
    __tablename__ = "workflows"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    customer: Mapped[Customer] = relationship(back_populates="workflows")
    requests: Mapped[list["OperationRequest"]] = relationship(back_populates="workflow")


class OperationRequest(Base):
    __tablename__ = "operation_requests"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id"), nullable=False)
    workflow_id: Mapped[str] = mapped_column(ForeignKey("workflows.id"), nullable=False)
    requested_action: Mapped[str] = mapped_column(String, nullable=False)
    business_context: Mapped[str] = mapped_column(Text, nullable=False)
    authority_present: Mapped[bool] = mapped_column(Boolean, default=False)
    scope_matched: Mapped[bool] = mapped_column(Boolean, default=False)
    evidence_present: Mapped[bool] = mapped_column(Boolean, default=False)
    evidence_fresh: Mapped[bool] = mapped_column(Boolean, default=False)
    risk_level: Mapped[str] = mapped_column(String, default="medium")
    approval_required: Mapped[bool] = mapped_column(Boolean, default=True)
    lifecycle_status: Mapped[str] = mapped_column(String, default="submitted")
    request_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    workflow: Mapped[Workflow] = relationship(back_populates="requests")
    decision: Mapped["Decision"] = relationship(back_populates="request", uselist=False)
    evidence_items: Mapped[list["EvidenceItem"]] = relationship(back_populates="request")
    audit_events: Mapped[list["AuditEvent"]] = relationship(back_populates="request")


class Decision(Base):
    __tablename__ = "decisions"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    request_id: Mapped[str] = mapped_column(ForeignKey("operation_requests.id"), nullable=False)
    outcome: Mapped[str] = mapped_column(String, nullable=False)
    protected_effect_status: Mapped[str] = mapped_column(String, nullable=False)
    no_bind_status: Mapped[bool] = mapped_column(Boolean, nullable=False)
    reason_codes: Mapped[list] = mapped_column(JSON, default=list)
    receipt_id: Mapped[str] = mapped_column(String, nullable=False)
    replay_token: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    request: Mapped[OperationRequest] = relationship(back_populates="decision")


class EvidenceItem(Base):
    __tablename__ = "evidence_items"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    request_id: Mapped[str] = mapped_column(ForeignKey("operation_requests.id"), nullable=False)
    label: Mapped[str] = mapped_column(String, nullable=False)
    source: Mapped[str] = mapped_column(String, nullable=False)
    freshness_status: Mapped[str] = mapped_column(String, default="unknown")
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    request: Mapped[OperationRequest] = relationship(back_populates="evidence_items")


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    request_id: Mapped[str] = mapped_column(ForeignKey("operation_requests.id"), nullable=False)
    event_type: Mapped[str] = mapped_column(String, nullable=False)
    actor: Mapped[str] = mapped_column(String, default="system")
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    request: Mapped[OperationRequest] = relationship(back_populates="audit_events")


class ExecutionJob(Base):
    __tablename__ = "execution_jobs"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    request_id: Mapped[str] = mapped_column(ForeignKey("operation_requests.id"), nullable=False)
    status: Mapped[str] = mapped_column(String, default="QUEUED")
    worker_id: Mapped[str | None] = mapped_column(String, nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
