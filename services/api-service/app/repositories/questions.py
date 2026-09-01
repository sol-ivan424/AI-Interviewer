from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import Level, Role
from app.models.question import Question


class QuestionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_random_active(
        self, role: Role, level: Level, limit: int, *, source: str = "seed"
    ) -> list[Question]:
        result = await self.session.execute(
            select(Question)
            .where(
                Question.role == role.value,
                Question.level == level.value,
                Question.is_active.is_(True),
                Question.source == source,
            )
            .order_by(func.random())
            .limit(limit)
        )
        return list(result.scalars())

    async def get_fallback(self, role: str, level: str, excluded_ids: set[UUID]) -> Question | None:
        statement = select(Question).where(
            Question.role == role,
            Question.level == level,
            Question.is_active.is_(True),
            Question.source.in_(("fallback", "seed")),
        )
        if excluded_ids:
            statement = statement.where(Question.id.not_in(excluded_ids))
        result = await self.session.execute(
            statement.order_by(Question.created_at, Question.id).limit(1)
        )
        return result.scalar_one_or_none()

    async def get_by_text(self, role: str, level: str, text: str) -> Question | None:
        result = await self.session.execute(
            select(Question).where(
                Question.role == role,
                Question.level == level,
                Question.text == text,
            )
        )
        return result.scalar_one_or_none()
