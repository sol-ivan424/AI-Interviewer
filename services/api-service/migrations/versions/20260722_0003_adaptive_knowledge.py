"""Add adaptive interview knowledge storage.

Revision ID: 20260722_0003
Revises: 20260712_0002
Create Date: 2026-07-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260722_0003"
down_revision: str | None = "20260712_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "questions",
        sa.Column("source", sa.String(length=50), server_default="seed", nullable=False),
    )
    op.execute(
        """
        WITH ranked AS (
            SELECT id, row_number() OVER (
                PARTITION BY role, level ORDER BY created_at, id
            ) AS position
            FROM questions
        )
        UPDATE questions AS question
        SET source = 'fallback'
        FROM ranked
        WHERE question.id = ranked.id AND ranked.position > 3
        """
    )
    op.add_column("questions", sa.Column("target_subtopic", sa.String(length=255), nullable=True))
    op.add_column(
        "questions",
        sa.Column(
            "topic_weights",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column(
        "answers",
        sa.Column(
            "topic_coverage",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column(
        "interviews",
        sa.Column("target_questions_count", sa.Integer(), server_default="5", nullable=False),
    )
    op.alter_column("llm_requests", "answer_id", existing_type=sa.Uuid(), nullable=True)
    op.add_column("llm_requests", sa.Column("question_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_llm_requests_question_id_questions",
        "llm_requests",
        "questions",
        ["question_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_llm_requests_question_id", "llm_requests", ["question_id"])

    op.create_table(
        "user_topic_knowledge",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(length=50), nullable=False),
        sa.Column("level", sa.String(length=50), nullable=False),
        sa.Column("topic", sa.String(length=255), nullable=False),
        sa.Column("subtopic", sa.String(length=255), nullable=False),
        sa.Column("score", sa.Float(), server_default="0", nullable=False),
        sa.Column("confidence", sa.Float(), server_default="0", nullable=False),
        sa.Column("evidence_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("evidence_weight", sa.Float(), server_default="0", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_user_topic_knowledge_confidence_range",
        ),
        sa.CheckConstraint(
            "evidence_count >= 0",
            name="ck_user_topic_knowledge_evidence_count_non_negative",
        ),
        sa.CheckConstraint(
            "evidence_weight >= 0",
            name="ck_user_topic_knowledge_evidence_weight_non_negative",
        ),
        sa.CheckConstraint(
            "score >= 0 AND score <= 100", name="ck_user_topic_knowledge_score_range"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_user_topic_knowledge_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_user_topic_knowledge"),
        sa.UniqueConstraint(
            "user_id",
            "role",
            "level",
            "topic",
            "subtopic",
            name="uq_user_topic_knowledge_identity",
        ),
    )
    op.create_index(
        "ix_user_topic_knowledge_user_role_level",
        "user_topic_knowledge",
        ["user_id", "role", "level"],
    )


def downgrade() -> None:
    op.drop_index("ix_user_topic_knowledge_user_role_level", table_name="user_topic_knowledge")
    op.drop_table("user_topic_knowledge")
    op.drop_index("ix_llm_requests_question_id", table_name="llm_requests")
    op.drop_constraint("fk_llm_requests_question_id_questions", "llm_requests", type_="foreignkey")
    op.drop_column("llm_requests", "question_id")
    op.alter_column("llm_requests", "answer_id", existing_type=sa.Uuid(), nullable=False)
    op.drop_column("interviews", "target_questions_count")
    op.drop_column("answers", "topic_coverage")
    op.drop_column("questions", "topic_weights")
    op.drop_column("questions", "target_subtopic")
    op.drop_column("questions", "source")
