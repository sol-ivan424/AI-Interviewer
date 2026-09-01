from collections import defaultdict

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.analytics import AnalyticsRepository
from app.schemas.analytics import (
    AnalyticsProgressResponse,
    AnalyticsSkillResponse,
    AnalyticsSummaryResponse,
)
from app.services.interviews import percentage


class AnalyticsService:
    def __init__(self, session: AsyncSession) -> None:
        self.repository = AnalyticsRepository(session)

    async def summary(self, user: User) -> AnalyticsSummaryResponse:
        total = await self.repository.total_interviews(user.id)
        finished = await self.repository.finished_interviews(user.id)
        skills = await self.skills(user)

        if not finished:
            return AnalyticsSummaryResponse(
                total_interviews=total,
                finished_interviews=0,
                average_percentage=None,
                best_role=None,
                strongest_skill=None,
                weakest_skills=[],
            )

        interview_percentages = [
            percentage(interview.total_score, max_score) for interview, max_score in finished
        ]
        by_role: dict[str, list[int]] = defaultdict(list)
        for (interview, _), value in zip(finished, interview_percentages, strict=True):
            by_role[interview.role].append(value)

        role_averages = {role: round(sum(values) / len(values)) for role, values in by_role.items()}
        best_role = sorted(role_averages, key=lambda role: (-role_averages[role], role))[0]

        strongest_skill = None
        weakest_skills: list[str] = []
        if skills:
            strongest_skill = sorted(
                skills, key=lambda item: (-item.average_percentage, item.skill)
            )[0].skill
            weakest_skills = [
                item.skill
                for item in sorted(skills, key=lambda item: (item.average_percentage, item.skill))
                if item.average_percentage < 70
            ]

        return AnalyticsSummaryResponse(
            total_interviews=total,
            finished_interviews=len(finished),
            average_percentage=round(sum(interview_percentages) / len(interview_percentages)),
            best_role=best_role,
            strongest_skill=strongest_skill,
            weakest_skills=weakest_skills,
        )

    async def skills(self, user: User) -> list[AnalyticsSkillResponse]:
        rows = await self.repository.skill_aggregates(user.id)
        return [
            AnalyticsSkillResponse(
                skill=skill,
                average_percentage=percentage(int(score), int(max_score)),
                answers_count=int(count),
            )
            for skill, score, max_score, count in rows
        ]

    async def progress(self, user: User) -> list[AnalyticsProgressResponse]:
        rows = await self.repository.finished_interviews(user.id)
        return [
            AnalyticsProgressResponse(
                interview_id=interview.id,
                role=interview.role,
                level=interview.level,
                finished_at=interview.finished_at,
                percentage=percentage(interview.total_score, max_score),
            )
            for interview, max_score in rows
            if interview.finished_at is not None
        ]
