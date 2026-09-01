import logging

from fastapi import APIRouter, HTTPException, Request, status

from app.schemas.adaptive import (
    BaselineQuestionGenerationRequest,
    BaselineQuestionGenerationResponse,
    QuestionAnalysisRequest,
    QuestionAnalysisResponse,
    QuestionGenerationRequest,
    QuestionGenerationResponse,
)
from app.schemas.chat import InterviewerMessageRequest, InterviewerMessageResponse
from app.schemas.evaluation import EvaluationRequest, EvaluationResponse
from app.services.evaluation_service import (
    analyze_question,
    create_interviewer_message,
    evaluate_answer,
    generate_baseline_questions,
    generate_question,
)
from app.services.openai_compatible_client import LLMResponseError, LLMUnavailableError

router = APIRouter(prefix="/llm")
logger = logging.getLogger(__name__)


def controlled_error(error: Exception) -> HTTPException:
    logger.warning("LLM request failed: %s", error)
    if isinstance(error, LLMUnavailableError):
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLM API is unavailable",
        )
    return HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail="LLM API returned an invalid response",
    )


@router.post("/interviewer-message", response_model=InterviewerMessageResponse)
async def interviewer_message(
    payload: InterviewerMessageRequest, request: Request
) -> InterviewerMessageResponse:
    try:
        return await create_interviewer_message(request.app.state.llm_client, payload)
    except (LLMUnavailableError, LLMResponseError) as error:
        raise controlled_error(error) from error


@router.post("/evaluate-answer", response_model=EvaluationResponse)
async def evaluate(payload: EvaluationRequest, request: Request) -> EvaluationResponse:
    try:
        return await evaluate_answer(request.app.state.llm_client, payload)
    except (LLMUnavailableError, LLMResponseError) as error:
        raise controlled_error(error) from error


@router.post("/analyze-question", response_model=QuestionAnalysisResponse)
async def analyze(payload: QuestionAnalysisRequest, request: Request) -> QuestionAnalysisResponse:
    try:
        return await analyze_question(request.app.state.llm_client, payload)
    except (LLMUnavailableError, LLMResponseError) as error:
        raise controlled_error(error) from error


@router.post("/generate-question", response_model=QuestionGenerationResponse)
async def generate(
    payload: QuestionGenerationRequest, request: Request
) -> QuestionGenerationResponse:
    try:
        return await generate_question(request.app.state.llm_client, payload)
    except (LLMUnavailableError, LLMResponseError) as error:
        raise controlled_error(error) from error


@router.post("/generate-baseline-questions", response_model=BaselineQuestionGenerationResponse)
async def generate_baseline(
    payload: BaselineQuestionGenerationRequest, request: Request
) -> BaselineQuestionGenerationResponse:
    try:
        return await generate_baseline_questions(request.app.state.llm_client, payload)
    except (LLMUnavailableError, LLMResponseError) as error:
        raise controlled_error(error) from error
