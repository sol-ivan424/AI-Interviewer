from uuid import UUID, uuid4

from sqlalchemy import JSON, Boolean, Index, Integer, String, Text, UniqueConstraint, Uuid, true
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin

json_type = JSON().with_variant(JSONB(), "postgresql")


class Question(TimestampMixin, Base):
    __tablename__ = "questions"
    __table_args__ = (
        UniqueConstraint("role", "level", "text", name="uq_questions_role_level_text"),
        Index("ix_questions_role_level", "role", "level"),
        Index("ix_questions_skill", "skill"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    level: Mapped[str] = mapped_column(String(50), nullable=False)
    skill: Mapped[str] = mapped_column(String(100), nullable=False)
    source: Mapped[str] = mapped_column(
        String(50), nullable=False, default="seed", server_default="seed"
    )
    target_subtopic: Mapped[str | None] = mapped_column(String(255), nullable=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    ideal_answer: Mapped[str] = mapped_column(Text, nullable=False)
    evaluation_points: Mapped[list[str]] = mapped_column(json_type, nullable=False)
    topic_weights: Mapped[list[dict[str, object]]] = mapped_column(
        json_type, nullable=False, default=list, server_default="[]"
    )
    max_score: Mapped[int] = mapped_column(Integer, nullable=False, default=10, server_default="10")
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=true()
    )
