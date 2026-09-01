"""Add LLM request metadata.

Revision ID: 20260712_0002
Revises: 20260711_0001
Create Date: 2026-07-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260712_0002"
down_revision: str | None = "20260711_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "llm_requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("interview_id", sa.Uuid(), nullable=False),
        sa.Column("answer_id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=False),
        sa.Column("prompt_type", sa.String(length=50), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["answer_id"],
            ["answers.id"],
            name="fk_llm_requests_answer_id_answers",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["interview_id"],
            ["interviews.id"],
            name="fk_llm_requests_interview_id_interviews",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_llm_requests"),
    )
    op.create_index("ix_llm_requests_answer_id", "llm_requests", ["answer_id"])
    op.create_index("ix_llm_requests_interview_id", "llm_requests", ["interview_id"])


def downgrade() -> None:
    op.drop_index("ix_llm_requests_interview_id", table_name="llm_requests")
    op.drop_index("ix_llm_requests_answer_id", table_name="llm_requests")
    op.drop_table("llm_requests")
