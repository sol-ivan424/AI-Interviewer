from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class LLMRequest(Base):
    __tablename__ = "llm_requests"
    __table_args__ = (
        Index("ix_llm_requests_interview_id", "interview_id"),
        Index("ix_llm_requests_answer_id", "answer_id"),
        Index("ix_llm_requests_question_id", "question_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    interview_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("interviews.id", ondelete="CASCADE"), nullable=False
    )
    answer_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("answers.id", ondelete="CASCADE"), nullable=True
    )
    question_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("questions.id", ondelete="SET NULL"), nullable=True
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_type: Mapped[str] = mapped_column(String(50), nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
