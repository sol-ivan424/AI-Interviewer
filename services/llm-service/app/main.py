from fastapi import FastAPI

from app.api.v1.health import router as health_router
from app.api.v1.llm import router as llm_router
from app.core.config import settings
from app.services.openai_compatible_client import OpenAICompatibleClient

app = FastAPI(title="AI Interviewer LLM Service", version="0.1.0")
app.state.llm_client = OpenAICompatibleClient(
    base_url=settings.llm_api_base_url,
    api_key=settings.llm_api_key,
    provider=settings.llm_provider,
    model=settings.llm_model,
    timeout_seconds=settings.llm_timeout_seconds,
    temperature=settings.llm_temperature,
    max_tokens=settings.llm_max_tokens,
)
app.include_router(health_router)
app.include_router(llm_router)
