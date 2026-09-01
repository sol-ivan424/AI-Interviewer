from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.llm_request import LLMRequest


class LLMRequestRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def add(
        self,
        interview_id: UUID,
        answer_id: UUID | None = None,
        *,
        question_id: UUID | None = None,
        provider: str,
        model: str,
        prompt_type: str = "evaluate_answer",
        latency_ms: int,
        success: bool,
        error: str | None,
    ) -> None:
        self.session.add(
            LLMRequest(
                interview_id=interview_id,
                answer_id=answer_id,
                question_id=question_id,
                provider=provider,
                model=model,
                prompt_type=prompt_type,
                latency_ms=latency_ms,
                success=success,
                error_message=error,
            )
        )
