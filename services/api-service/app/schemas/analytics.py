from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.core.enums import Level, Role


class AnalyticsSummaryResponse(BaseModel):
    total_interviews: int
    finished_interviews: int
    average_percentage: int | None
    best_role: Role | None
    strongest_skill: str | None
    weakest_skills: list[str]


class AnalyticsSkillResponse(BaseModel):
    skill: str
    average_percentage: int
    answers_count: int


class AnalyticsProgressResponse(BaseModel):
    interview_id: UUID
    role: Role
    level: Level
    finished_at: datetime
    percentage: int
