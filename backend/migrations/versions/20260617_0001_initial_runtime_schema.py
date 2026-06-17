"""initial runtime schema

Revision ID: 20260617_0001
Revises:
Create Date: 2026-06-17
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260617_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def existing_tables() -> set[str]:
    inspector = sa.inspect(op.get_bind())
    return set(inspector.get_table_names())


def upgrade() -> None:
    tables = existing_tables()

    if "customers" not in tables:
        op.create_table(
            "customers",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("industry", sa.String(), nullable=False, server_default="general"),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )

    if "workflows" not in tables:
        op.create_table(
            "workflows",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("customer_id", sa.String(), sa.ForeignKey("customers.id"), nullable=False),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("description", sa.Text(), nullable=False, server_default=""),
            sa.Column("status", sa.String(), nullable=False, server_default="active"),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )

    if "operation_requests" not in tables:
        op.create_table(
            "operation_requests",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("customer_id", sa.String(), sa.ForeignKey("customers.id"), nullable=False),
            sa.Column("workflow_id", sa.String(), sa.ForeignKey("workflows.id"), nullable=False),
            sa.Column("requested_action", sa.String(), nullable=False),
            sa.Column("business_context", sa.Text(), nullable=False),
            sa.Column("authority_present", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("scope_matched", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("evidence_present", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("evidence_fresh", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("risk_level", sa.String(), nullable=False, server_default="medium"),
            sa.Column("approval_required", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("lifecycle_status", sa.String(), nullable=False, server_default="submitted"),
            sa.Column("request_metadata", sa.JSON(), nullable=False, server_default="{}"),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )

    if "decisions" not in tables:
        op.create_table(
            "decisions",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("request_id", sa.String(), sa.ForeignKey("operation_requests.id"), nullable=False),
            sa.Column("outcome", sa.String(), nullable=False),
            sa.Column("protected_effect_status", sa.String(), nullable=False),
            sa.Column("no_bind_status", sa.Boolean(), nullable=False),
            sa.Column("reason_codes", sa.JSON(), nullable=False, server_default="[]"),
            sa.Column("receipt_id", sa.String(), nullable=False),
            sa.Column("replay_token", sa.String(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )

    if "evidence_items" not in tables:
        op.create_table(
            "evidence_items",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("request_id", sa.String(), sa.ForeignKey("operation_requests.id"), nullable=False),
            sa.Column("label", sa.String(), nullable=False),
            sa.Column("source", sa.String(), nullable=False),
            sa.Column("freshness_status", sa.String(), nullable=False, server_default="unknown"),
            sa.Column("payload", sa.JSON(), nullable=False, server_default="{}"),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )

    if "audit_events" not in tables:
        op.create_table(
            "audit_events",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("request_id", sa.String(), sa.ForeignKey("operation_requests.id"), nullable=False),
            sa.Column("event_type", sa.String(), nullable=False),
            sa.Column("actor", sa.String(), nullable=False, server_default="system"),
            sa.Column("detail", sa.JSON(), nullable=False, server_default="{}"),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )

    if "execution_jobs" not in tables:
        op.create_table(
            "execution_jobs",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("request_id", sa.String(), sa.ForeignKey("operation_requests.id"), nullable=False),
            sa.Column("status", sa.String(), nullable=False, server_default="QUEUED"),
            sa.Column("worker_id", sa.String(), nullable=True),
            sa.Column("failure_reason", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("started_at", sa.DateTime(), nullable=True),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
        )


def downgrade() -> None:
    for table_name in [
        "execution_jobs",
        "audit_events",
        "evidence_items",
        "decisions",
        "operation_requests",
        "workflows",
        "customers",
    ]:
        if table_name in existing_tables():
            op.drop_table(table_name)
