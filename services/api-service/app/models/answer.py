from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.question import json_type


class Answer(Base):
    __tablename__ = "answers"
    __table_args__ = (
        CheckConstraint("score >= 0", name="score_non_negative"),
        CheckConstraint("score <= max_score", name="score_not_above_max"),
        CheckConstraint("max_score > 0", name="max_score_positive"),
        Index("ix_answers_interview_id", "interview_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    interview_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("interviews.id", ondelete="CASCADE"), nullable=False
    )
    interview_question_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("interview_questions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    answer_text: Mapped[str] = mapped_column(Text, nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    max_score: Mapped[int] = mapped_column(Integer, nullable=False, default=10, server_default="10")
    verdict: Mapped[str] = mapped_column(String(50), nullable=False)
    feedback: Mapped[str] = mapped_column(Text, nullable=False)
    matched_points: Mapped[list[str]] = mapped_column(json_type, nullable=False)
    missing_points: Mapped[list[str]] = mapped_column(json_type, nullable=False)
    topic_coverage: Mapped[list[dict[str, object]]] = mapped_column(
        json_type, nullable=False, default=list, server_default="[]"
    )
    scoring_provider: Mapped[str] = mapped_column(String(50), nullable=False)
    llm_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    keyword_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ml_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
