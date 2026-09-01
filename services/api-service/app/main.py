from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers.analytics import router as analytics_router
from app.api.routers.auth import router as auth_router
from app.api.routers.health import router as health_router
from app.api.routers.interviews import router as interviews_router
from app.api.routers.roles import router as roles_router
from app.api.routers.users import router as users_router
from app.core.config import Settings, get_settings
from app.db.session import create_session_factory
from app.services.llm import LLMScoringClient
from app.services.ml import MLRecommendationClient


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build and configure the API application."""
    app_settings = settings or get_settings()
    engine, session_factory = create_session_factory(app_settings.database_url)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        yield
        await engine.dispose()

    application = FastAPI(
        title=app_settings.app_name,
        version=app_settings.app_version,
        debug=app_settings.debug,
        lifespan=lifespan,
    )

    application.state.settings = app_settings
    application.state.llm_scoring_client = LLMScoringClient(app_settings)
    application.state.ml_recommendation_client = MLRecommendationClient(
        app_settings.ml_service_url, app_settings.ml_timeout_seconds
    )
    application.state.engine = engine
    application.state.session_factory = session_factory
    application.add_middleware(
        CORSMiddleware,
        allow_origins=app_settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.include_router(health_router)
    application.include_router(auth_router)
    application.include_router(users_router)
    application.include_router(roles_router)
    application.include_router(interviews_router)
    application.include_router(analytics_router)
    return application


app = create_app()
