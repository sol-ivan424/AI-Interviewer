from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin


class UserTopicKnowledge(TimestampMixin, Base):
    __tablename__ = "user_topic_knowledge"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "role",
            "level",
            "topic",
            "subtopic",
            name="uq_user_topic_knowledge_identity",
        ),
        CheckConstraint("score >= 0 AND score <= 100", name="score_range"),
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="confidence_range"),
        CheckConstraint("evidence_count >= 0", name="evidence_count_non_negative"),
        CheckConstraint("evidence_weight >= 0", name="evidence_weight_non_negative"),
        Index("ix_user_topic_knowledge_user_role_level", "user_id", "role", "level"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    level: Mapped[str] = mapped_column(String(50), nullable=False)
    topic: Mapped[str] = mapped_column(String(255), nullable=False)
    subtopic: Mapped[str] = mapped_column(String(255), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    confidence: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0, server_default="0"
    )
    evidence_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    evidence_weight: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0, server_default="0"
    )
