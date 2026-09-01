from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import InterviewStatus
from app.models.answer import Answer
from app.models.interview import Interview
from app.models.interview_question import InterviewQuestion
from app.models.question import Question

FinishedInterviewRow = tuple[Interview, int]
SkillAggregateRow = tuple[str, int, int, int]


class AnalyticsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def total_interviews(self, user_id: UUID) -> int:
        value = await self.session.scalar(
            select(func.count(Interview.id)).where(Interview.user_id == user_id)
        )
        return int(value or 0)

    async def finished_interviews(self, user_id: UUID) -> Sequence[FinishedInterviewRow]:
        result = await self.session.execute(
            select(Interview, func.coalesce(func.sum(Question.max_score), 0))
            .join(InterviewQuestion, InterviewQuestion.interview_id == Interview.id)
            .join(Question, Question.id == InterviewQuestion.question_id)
            .where(
                Interview.user_id == user_id,
                Interview.status == InterviewStatus.FINISHED.value,
            )
            .group_by(Interview.id)
            .order_by(Interview.finished_at.asc(), Interview.id.asc())
        )
        return result.all()

    async def skill_aggregates(self, user_id: UUID) -> Sequence[SkillAggregateRow]:
        result = await self.session.execute(
            select(
                Question.skill,
                func.coalesce(func.sum(Answer.score), 0),
                func.coalesce(func.sum(Answer.max_score), 0),
                func.count(Answer.id),
            )
            .join(InterviewQuestion, InterviewQuestion.question_id == Question.id)
            .join(Answer, Answer.interview_question_id == InterviewQuestion.id)
            .join(Interview, Interview.id == Answer.interview_id)
            .where(
                Interview.user_id == user_id,
                Interview.status == InterviewStatus.FINISHED.value,
            )
            .group_by(Question.skill)
            .order_by(Question.skill.asc())
        )
        return result.all()
