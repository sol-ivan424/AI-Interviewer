"""Create the Phase 1 application schema.

Revision ID: 20260711_0001
Revises:
Create Date: 2026-07-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260711_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=True),
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
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )

    op.create_table(
        "questions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(length=50), nullable=False),
        sa.Column("level", sa.String(length=50), nullable=False),
        sa.Column("skill", sa.String(length=100), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("ideal_answer", sa.Text(), nullable=False),
        sa.Column("evaluation_points", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("max_score", sa.Integer(), server_default="10", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
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
        sa.PrimaryKeyConstraint("id", name="pk_questions"),
        sa.UniqueConstraint("role", "level", "text", name="uq_questions_role_level_text"),
    )
    op.create_index("ix_questions_role_level", "questions", ["role", "level"])
    op.create_index("ix_questions_skill", "questions", ["skill"])

    op.create_table(
        "interviews",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(length=50), nullable=False),
        sa.Column("level", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=50), server_default="in_progress", nullable=False),
        sa.Column("finished_reason", sa.String(length=50), nullable=True),
        sa.Column("total_score", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_interviews_user_id_users", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_interviews"),
    )
    op.create_index("ix_interviews_status", "interviews", ["status"])
    op.create_index("ix_interviews_user_id", "interviews", ["user_id"])

    op.create_table(
        "interview_questions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("interview_id", sa.Uuid(), nullable=False),
        sa.Column("question_id", sa.Uuid(), nullable=False),
        sa.Column("order_number", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["interview_id"],
            ["interviews.id"],
            name="fk_interview_questions_interview_id_interviews",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["question_id"], ["questions.id"], name="fk_interview_questions_question_id_questions"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_interview_questions"),
        sa.UniqueConstraint(
            "interview_id", "order_number", name="uq_interview_questions_interview_order"
        ),
        sa.UniqueConstraint(
            "interview_id", "question_id", name="uq_interview_questions_interview_question"
        ),
    )
    op.create_index("ix_interview_questions_interview_id", "interview_questions", ["interview_id"])

    op.create_table(
        "answers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("interview_id", sa.Uuid(), nullable=False),
        sa.Column("interview_question_id", sa.Uuid(), nullable=False),
        sa.Column("answer_text", sa.Text(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("max_score", sa.Integer(), server_default="10", nullable=False),
        sa.Column("verdict", sa.String(length=50), nullable=False),
        sa.Column("feedback", sa.Text(), nullable=False),
        sa.Column("matched_points", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("missing_points", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("scoring_provider", sa.String(length=50), nullable=False),
        sa.Column("llm_score", sa.Integer(), nullable=True),
        sa.Column("keyword_score", sa.Integer(), nullable=True),
        sa.Column("ml_score", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("max_score > 0", name="ck_answers_max_score_positive"),
        sa.CheckConstraint("score >= 0", name="ck_answers_score_non_negative"),
        sa.CheckConstraint("score <= max_score", name="ck_answers_score_not_above_max"),
        sa.ForeignKeyConstraint(
            ["interview_id"],
            ["interviews.id"],
            name="fk_answers_interview_id_interviews",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["interview_question_id"],
            ["interview_questions.id"],
            name="fk_answers_interview_question_id_interview_questions",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_answers"),
        sa.UniqueConstraint("interview_question_id", name="uq_answers_interview_question_id"),
    )
    op.create_index("ix_answers_interview_id", "answers", ["interview_id"])


def downgrade() -> None:
    op.drop_index("ix_answers_interview_id", table_name="answers")
    op.drop_table("answers")
    op.drop_index("ix_interview_questions_interview_id", table_name="interview_questions")
    op.drop_table("interview_questions")
    op.drop_index("ix_interviews_user_id", table_name="interviews")
    op.drop_index("ix_interviews_status", table_name="interviews")
    op.drop_table("interviews")
    op.drop_index("ix_questions_skill", table_name="questions")
    op.drop_index("ix_questions_role_level", table_name="questions")
    op.drop_table("questions")
    op.drop_table("users")
