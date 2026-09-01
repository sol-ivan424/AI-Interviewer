from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, status

from app.api.dependencies import CurrentUserDependency, SessionDependency
from app.core.errors import (
    InsufficientQuestionsError,
    InterviewNotFoundError,
    InterviewStateConflictError,
    InvalidAnswerError,
    LLMQuestionGenerationError,
)
from app.schemas.interviews import (
    AnswerSubmitRequest,
    AnswerSubmitResponse,
    InterviewCreateRequest,
    InterviewCreateResponse,
    InterviewDetailResponse,
    InterviewFinishResponse,
    InterviewListItemResponse,
    InterviewResultResponse,
)
from app.services.interviews import InterviewService

router = APIRouter(prefix="/api/v1/interviews", tags=["interviews"])


def service(request: Request, session: SessionDependency) -> InterviewService:
    return InterviewService(
        session,
        request.app.state.settings,
        request.app.state.llm_scoring_client,
        request.app.state.ml_recommendation_client,
    )


def not_found(error: InterviewNotFoundError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found")


def conflict(error: InterviewStateConflictError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))


@router.post("", response_model=InterviewCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_interview(
    payload: InterviewCreateRequest,
    request: Request,
    session: SessionDependency,
    current_user: CurrentUserDependency,
) -> InterviewCreateResponse:
    try:
        return await service(request, session).create(current_user, payload)
    except InsufficientQuestionsError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Not enough active questions for this role and level",
        ) from error
    except LLMQuestionGenerationError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(error),
        ) from error


@router.get("", response_model=list[InterviewListItemResponse])
async def list_interviews(
    request: Request,
    session: SessionDependency,
    current_user: CurrentUserDependency,
) -> list[InterviewListItemResponse]:
    return await service(request, session).list(current_user)


@router.get("/{interview_id}", response_model=InterviewDetailResponse)
async def get_interview(
    interview_id: UUID,
    request: Request,
    session: SessionDependency,
    current_user: CurrentUserDependency,
) -> InterviewDetailResponse:
    try:
        return await service(request, session).detail(current_user, interview_id)
    except InterviewNotFoundError as error:
        raise not_found(error) from error


@router.post("/{interview_id}/answers", response_model=AnswerSubmitResponse)
async def submit_answer(
    interview_id: UUID,
    payload: AnswerSubmitRequest,
    request: Request,
    session: SessionDependency,
    current_user: CurrentUserDependency,
) -> AnswerSubmitResponse:
    try:
        return await service(request, session).submit_answer(current_user, interview_id, payload)
    except InterviewNotFoundError as error:
        raise not_found(error) from error
    except InterviewStateConflictError as error:
        raise conflict(error) from error
    except InvalidAnswerError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        ) from error
    except LLMQuestionGenerationError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(error),
        ) from error


@router.post("/{interview_id}/finish", response_model=InterviewFinishResponse)
async def finish_interview(
    interview_id: UUID,
    request: Request,
    session: SessionDependency,
    current_user: CurrentUserDependency,
) -> InterviewFinishResponse:
    try:
        return await service(request, session).finish(current_user, interview_id)
    except InterviewNotFoundError as error:
        raise not_found(error) from error
    except InterviewStateConflictError as error:
        raise conflict(error) from error


@router.get("/{interview_id}/result", response_model=InterviewResultResponse)
async def get_result(
    interview_id: UUID,
    request: Request,
    session: SessionDependency,
    current_user: CurrentUserDependency,
) -> InterviewResultResponse:
    try:
        return await service(request, session).result(current_user, interview_id)
    except InterviewNotFoundError as error:
        raise not_found(error) from error
    except InterviewStateConflictError as error:
        raise conflict(error) from error
