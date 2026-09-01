from fastapi import APIRouter

from app.api.dependencies import CurrentUserDependency, SessionDependency
from app.schemas.analytics import (
    AnalyticsProgressResponse,
    AnalyticsSkillResponse,
    AnalyticsSummaryResponse,
)
from app.services.analytics import AnalyticsService

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


@router.get("/summary", response_model=AnalyticsSummaryResponse)
async def get_summary(
    session: SessionDependency, current_user: CurrentUserDependency
) -> AnalyticsSummaryResponse:
    return await AnalyticsService(session).summary(current_user)


@router.get("/skills", response_model=list[AnalyticsSkillResponse])
async def get_skills(
    session: SessionDependency, current_user: CurrentUserDependency
) -> list[AnalyticsSkillResponse]:
    return await AnalyticsService(session).skills(current_user)


@router.get("/progress", response_model=list[AnalyticsProgressResponse])
async def get_progress(
    session: SessionDependency, current_user: CurrentUserDependency
) -> list[AnalyticsProgressResponse]:
    return await AnalyticsService(session).progress(current_user)
