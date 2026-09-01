from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.core.config import settings
from app.services.openai_compatible_client import LLMError

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    runtime: str


class LLMHealthResponse(BaseModel):
    status: str
    provider: str
    model: str
    available: bool


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok", runtime=settings.llm_provider)


@router.get("/llm/health", response_model=LLMHealthResponse)
async def llm_health(request: Request) -> LLMHealthResponse:
    try:
        available = await request.app.state.llm_client.is_available()
    except LLMError:
        available = False
    return LLMHealthResponse(
        status="ok",
        provider=settings.llm_provider,
        model=settings.llm_model,
        available=available,
    )
