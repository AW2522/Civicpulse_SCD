"""001_initial_schema

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-09-27 16:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "complaints",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("location", sa.String(length=200), nullable=False),
        sa.Column("reporter_contact", sa.String(length=100), nullable=True),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("priority", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="open"),
        sa.Column("ai_summary", sa.String(length=140), nullable=True),
        sa.Column("triaged_by", sa.String(length=50), nullable=False),
        sa.Column("triage_latency_ms", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # Create composite index on (status, priority)
    op.create_index(
        "idx_complaints_status_priority",
        "complaints",
        ["status", "priority"],
        unique=False
    )

    # Create single index on created_at
    op.create_index(
        "idx_complaints_created_at",
        "complaints",
        ["created_at"],
        unique=False
    )


def downgrade() -> None:
    op.drop_index("idx_complaints_created_at", table_name="complaints")
    op.drop_index("idx_complaints_status_priority", table_name="complaints")
    op.drop_table("complaints")
