from pydantic import ValidationError

from app.schemas.adaptive import (
    BaselineQuestionGenerationRequest,
    BaselineQuestionGenerationResponse,
    QuestionAnalysisRequest,
    QuestionAnalysisResponse,
    QuestionGenerationRequest,
    QuestionGenerationResponse,
)
from app.schemas.chat import InterviewerMessageRequest, InterviewerMessageResponse
from app.schemas.evaluation import EvaluationRequest, EvaluationResponse, Verdict
from app.services.adaptive_prompt_builder import (
    build_baseline_question_generation_prompt,
    build_question_analysis_prompt,
    build_question_generation_prompt,
    build_topic_evaluation_prompt,
)
from app.services.openai_compatible_client import LLMResponseError, OpenAICompatibleClient
from app.services.prompt_builder import build_interviewer_prompt


def verdict_for_score(score: int) -> Verdict:
    if score >= 8:
        return "correct"
    if score >= 4:
        return "partially_correct"
    return "incorrect"


async def evaluate_answer(
    client: OpenAICompatibleClient, request: EvaluationRequest
) -> EvaluationResponse:
    raw = await client.generate(
        build_topic_evaluation_prompt(request),
        "evaluate_answer",
        EvaluationResponse.model_json_schema(),
    )
    try:
        result = EvaluationResponse.model_validate_json(raw)
    except ValidationError as error:
        raise LLMResponseError("LLM evaluation response failed validation") from error
    expected_points = set(request.evaluation_points)
    matched_points = set(result.matched_points)
    missing_points = set(result.missing_points)
    if (
        matched_points & missing_points
        or matched_points | missing_points != expected_points
        or len(result.matched_points) + len(result.missing_points) != len(request.evaluation_points)
    ):
        raise LLMResponseError("LLM evaluation criteria do not match the request")
    expected_topics = {(item.topic, item.subtopic) for item in request.topics}
    actual_topics = {(item.topic, item.subtopic) for item in result.topic_coverage}
    if actual_topics != expected_topics or len(result.topic_coverage) != len(request.topics):
        raise LLMResponseError("LLM topic coverage does not match the request")
    return result.model_copy(update={"verdict": verdict_for_score(result.score)})


async def create_interviewer_message(
    client: OpenAICompatibleClient, request: InterviewerMessageRequest
) -> InterviewerMessageResponse:
    raw = await client.generate(
        build_interviewer_prompt(request),
        "interviewer_message",
        InterviewerMessageResponse.model_json_schema(),
    )
    try:
        return InterviewerMessageResponse.model_validate_json(raw)
    except ValidationError as error:
        raise LLMResponseError("LLM interviewer response failed validation") from error


async def analyze_question(
    client: OpenAICompatibleClient, request: QuestionAnalysisRequest
) -> QuestionAnalysisResponse:
    raw = await client.generate(
        build_question_analysis_prompt(request),
        "analyze_question",
        QuestionAnalysisResponse.model_json_schema(),
    )
    try:
        return QuestionAnalysisResponse.model_validate_json(raw)
    except ValidationError as error:
        raise LLMResponseError("LLM question analysis failed validation") from error


async def generate_question(
    client: OpenAICompatibleClient, request: QuestionGenerationRequest
) -> QuestionGenerationResponse:
    raw = await client.generate(
        build_question_generation_prompt(request),
        "generate_question",
        QuestionGenerationResponse.model_json_schema(),
    )
    try:
        result = QuestionGenerationResponse.model_validate_json(raw)
    except ValidationError as error:
        raise LLMResponseError("LLM generated question failed validation") from error

    normalized_question = " ".join(result.question_text.casefold().split())
    previous = {" ".join(question.casefold().split()) for question in request.previous_questions}
    if normalized_question in previous:
        raise LLMResponseError("LLM repeated a previous question")
    target = (request.target_topic.casefold(), request.target_subtopic.casefold())
    if target not in {(item.topic.casefold(), item.subtopic.casefold()) for item in result.topics}:
        raise LLMResponseError("LLM generated question does not cover the target subtopic")
    return result


async def generate_baseline_questions(
    client: OpenAICompatibleClient, request: BaselineQuestionGenerationRequest
) -> BaselineQuestionGenerationResponse:
    raw = await client.generate(
        build_baseline_question_generation_prompt(request),
        "generate_baseline_questions",
        BaselineQuestionGenerationResponse.model_json_schema(),
    )
    try:
        result = BaselineQuestionGenerationResponse.model_validate_json(raw)
    except ValidationError as error:
        raise LLMResponseError("LLM baseline questions failed validation") from error

    previous = {" ".join(question.casefold().split()) for question in request.previous_questions}
    if any(
        " ".join(question.question_text.casefold().split()) in previous
        for question in result.questions
    ):
        raise LLMResponseError("LLM repeated a previous baseline question")
    return result
