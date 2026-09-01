from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.answer import Answer
from app.models.interview import Interview
from app.models.interview_question import InterviewQuestion
from app.models.question import Question

QuestionRow = tuple[InterviewQuestion, Question, Answer | None]
InterviewSummaryRow = tuple[Interview, int]


class InterviewRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_owned(
        self, interview_id: UUID, user_id: UUID, *, for_update: bool = False
    ) -> Interview | None:
        statement = select(Interview).where(
            Interview.id == interview_id, Interview.user_id == user_id
        )
        if for_update:
            statement = statement.with_for_update()
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_owned_summaries(self, user_id: UUID) -> Sequence[InterviewSummaryRow]:
        result = await self.session.execute(
            select(Interview, func.coalesce(func.sum(Question.max_score), 0))
            .outerjoin(InterviewQuestion, InterviewQuestion.interview_id == Interview.id)
            .outerjoin(Question, Question.id == InterviewQuestion.question_id)
            .where(Interview.user_id == user_id)
            .group_by(Interview.id)
            .order_by(Interview.created_at.desc())
        )
        return result.all()

    async def question_rows(self, interview_id: UUID) -> Sequence[QuestionRow]:
        result = await self.session.execute(
            select(InterviewQuestion, Question, Answer)
            .join(Question, Question.id == InterviewQuestion.question_id)
            .outerjoin(Answer, Answer.interview_question_id == InterviewQuestion.id)
            .where(InterviewQuestion.interview_id == interview_id)
            .order_by(InterviewQuestion.order_number.asc())
        )
        return result.all()

    async def previous_question_texts(
        self, user_id: UUID, role: str, level: str, limit: int = 50
    ) -> tuple[str, ...]:
        result = await self.session.execute(
            select(Question.text)
            .join(InterviewQuestion, InterviewQuestion.question_id == Question.id)
            .join(Interview, Interview.id == InterviewQuestion.interview_id)
            .where(
                Interview.user_id == user_id,
                Interview.role == role,
                Interview.level == level,
            )
            .order_by(Interview.created_at.desc(), InterviewQuestion.order_number.asc())
            .limit(limit)
        )
        return tuple(result.scalars())
