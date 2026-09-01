"""Set the default interview length to fifteen questions.

Revision ID: 20260804_0004
Revises: 20260722_0003
Create Date: 2026-08-04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260804_0004"
down_revision: str | None = "20260722_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "interviews",
        "target_questions_count",
        existing_type=sa.Integer(),
        server_default="15",
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "interviews",
        "target_questions_count",
        existing_type=sa.Integer(),
        server_default="5",
        existing_nullable=False,
    )
