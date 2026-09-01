import asyncio
import json
from dataclasses import dataclass
from time import perf_counter
from typing import Literal
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.config import Settings
from app.core.enums import Verdict
from app.services.scoring import ScoringOutcome


class _TopicWeightResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    topic: str = Field(min_length=1)
    subtopic: str = Field(min_length=1)
    weight: float = Field(gt=0, le=1)


class _TopicCoverageResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    topic: str = Field(min_length=1)
    subtopic: str = Field(min_length=1)
    coverage: float = Field(ge=0, le=1)


def _validate_topics(topics: list[_TopicWeightResponse]) -> list[_TopicWeightResponse]:
    keys = [(item.topic.casefold(), item.subtopic.casefold()) for item in topics]
    if len(keys) != len(set(keys)) or not topics or abs(sum(x.weight for x in topics) - 1) > 0.01:
        raise ValueError("LLM topic weights are invalid")
    return topics


class _QuestionAnalysisResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    topics: list[_TopicWeightResponse] = Field(min_length=1, max_length=8)

    @model_validator(mode="after")
    def validate_topics(self) -> "_QuestionAnalysisResponse":
        _validate_topics(self.topics)
        return self


class _EvaluationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    score: int = Field(ge=0, le=10, strict=True)
    max_score: Literal[10]
    verdict: Verdict
    feedback: str = Field(min_length=1)
    matched_points: list[str]
    missing_points: list[str]
    topic_coverage: list[_TopicCoverageResponse] = Field(default_factory=list)


class _GeneratedQuestionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    question_text: str = Field(min_length=1)
    ideal_answer: str = Field(min_length=1)
    evaluation_points: list[str] = Field(min_length=1, max_length=8)
    topics: list[_TopicWeightResponse] = Field(min_length=1, max_length=8)

    @model_validator(mode="after")
    def validate_question(self) -> "_GeneratedQuestionResponse":
        _validate_topics(self.topics)
        unique_points = {point.casefold() for point in self.evaluation_points}
        if len(self.evaluation_points) != len(unique_points):
            raise ValueError("LLM evaluation points must be unique")
        return self


class _BaselineQuestionResponse(_GeneratedQuestionResponse):
    area: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_area(self) -> "_BaselineQuestionResponse":
        if self.area.casefold() not in {item.topic.casefold() for item in self.topics}:
            raise ValueError("LLM topics do not include the baseline area")
        return self


class _BaselineQuestionsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    questions: list[_BaselineQuestionResponse] = Field(min_length=5, max_length=5)

    @model_validator(mode="after")
    def validate_questions(self) -> "_BaselineQuestionsResponse":
        areas = [item.area.casefold() for item in self.questions]
        texts = [" ".join(item.question_text.casefold().split()) for item in self.questions]
        if len(set(areas)) != 5 or len(set(texts)) != 5:
            raise ValueError("LLM baseline questions are not unique")
        return self


@dataclass(frozen=True, slots=True)
class TopicWeight:
    topic: str
    subtopic: str
    weight: float


@dataclass(frozen=True, slots=True)
class TopicCoverage:
    topic: str
    subtopic: str
    coverage: float


@dataclass(frozen=True, slots=True)
class LLMQuestionInput:
    role: str
    level: str
    skill: str
    question_text: str
    ideal_answer: str
    evaluation_points: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class LLMEvaluationInput:
    role: str
    level: str
    skill: str
    question_text: str
    ideal_answer: str
    evaluation_points: tuple[str, ...]
    user_answer: str
    topics: tuple[TopicWeight, ...] = ()


@dataclass(frozen=True, slots=True)
class LLMScoringAttempt:
    outcome: ScoringOutcome | None
    latency_ms: int
    provider: str
    model: str
    error: str | None
    topic_coverage: tuple[TopicCoverage, ...] = ()

    @property
    def success(self) -> bool:
        return self.outcome is not None


@dataclass(frozen=True, slots=True)
class LLMQuestionAnalysisAttempt:
    topics: tuple[TopicWeight, ...] | None
    latency_ms: int
    provider: str
    model: str
    error: str | None

    @property
    def success(self) -> bool:
        return self.topics is not None


@dataclass(frozen=True, slots=True)
class GeneratedQuestion:
    text: str
    ideal_answer: str
    evaluation_points: tuple[str, ...]
    topics: tuple[TopicWeight, ...]


@dataclass(frozen=True, slots=True)
class BaselineQuestion:
    area: str
    text: str
    ideal_answer: str
    evaluation_points: tuple[str, ...]
    topics: tuple[TopicWeight, ...]


@dataclass(frozen=True, slots=True)
class LLMQuestionGenerationAttempt:
    question: GeneratedQuestion | None
    latency_ms: int
    provider: str
    model: str
    error: str | None

    @property
    def success(self) -> bool:
        return self.question is not None


@dataclass(frozen=True, slots=True)
class LLMBaselineGenerationAttempt:
    questions: tuple[BaselineQuestion, ...] | None
    latency_ms: int
    provider: str
    model: str
    error: str | None

    @property
    def success(self) -> bool:
        return self.questions is not None


def _post_json(url: str, payload: dict[str, object], timeout: float) -> object:
    request = Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=timeout) as response:
        return json.load(response)


class LLMScoringClient:
    def __init__(self, settings: Settings) -> None:
        self.base_url = settings.llm_service_url.rstrip("/")
        self.timeout = settings.llm_timeout_seconds + 5
        self.provider = settings.llm_provider
        self.model = settings.llm_model

    @property
    def enabled(self) -> bool:
        return bool(self.base_url)

    async def analyze_question(self, payload: LLMQuestionInput) -> LLMQuestionAnalysisAttempt:
        started_at = perf_counter()
        try:
            body = await asyncio.to_thread(
                _post_json,
                f"{self.base_url}/llm/analyze-question",
                {
                    "role": payload.role,
                    "level": payload.level,
                    "skill": payload.skill,
                    "question_text": payload.question_text,
                    "ideal_answer": payload.ideal_answer,
                    "evaluation_points": list(payload.evaluation_points),
                },
                self.timeout,
            )
            result = _QuestionAnalysisResponse.model_validate(body)
            topics = tuple(TopicWeight(**item.model_dump()) for item in result.topics)
            error = None
        except Exception as caught_error:
            topics = None
            error = self._error_name(caught_error)
        return LLMQuestionAnalysisAttempt(
            topics=topics,
            latency_ms=round((perf_counter() - started_at) * 1000),
            provider=self.provider,
            model=self.model,
            error=error,
        )

    async def evaluate(self, payload: LLMEvaluationInput) -> LLMScoringAttempt:
        started_at = perf_counter()
        try:
            body = await asyncio.to_thread(
                _post_json,
                f"{self.base_url}/llm/evaluate-answer",
                {
                    "role": payload.role,
                    "level": payload.level,
                    "skill": payload.skill,
                    "question_text": payload.question_text,
                    "ideal_answer": payload.ideal_answer,
                    "evaluation_points": list(payload.evaluation_points),
                    "user_answer": payload.user_answer,
                    "topics": [
                        {
                            "topic": item.topic,
                            "subtopic": item.subtopic,
                            "weight": item.weight,
                        }
                        for item in payload.topics
                    ],
                },
                self.timeout,
            )
            result = _EvaluationResponse.model_validate(body)
            expected_points = set(payload.evaluation_points)
            matched_points = set(result.matched_points)
            missing_points = set(result.missing_points)
            if (
                matched_points & missing_points
                or matched_points | missing_points != expected_points
                or len(result.matched_points) + len(result.missing_points)
                != len(payload.evaluation_points)
            ):
                raise ValueError("LLM criteria do not match the question")
            coverage = tuple(TopicCoverage(**item.model_dump()) for item in result.topic_coverage)
            if payload.topics:
                expected_topics = {
                    (item.topic.casefold(), item.subtopic.casefold()) for item in payload.topics
                }
                actual_topics = {
                    (item.topic.casefold(), item.subtopic.casefold()) for item in coverage
                }
                if actual_topics != expected_topics or len(coverage) != len(payload.topics):
                    raise ValueError("LLM topic coverage does not match the question")
                score = int(
                    sum(
                        item.weight
                        * next(
                            value.coverage
                            for value in coverage
                            if value.topic.casefold() == item.topic.casefold()
                            and value.subtopic.casefold() == item.subtopic.casefold()
                        )
                        for item in payload.topics
                    )
                    * 10
                    + 0.5
                )
            else:
                score = result.score
            verdict = (
                Verdict.CORRECT
                if score >= 8
                else Verdict.PARTIALLY_CORRECT
                if score >= 4
                else Verdict.INCORRECT
            )
            outcome = ScoringOutcome(
                score=score,
                max_score=result.max_score,
                verdict=verdict,
                feedback=result.feedback,
                matched_points=result.matched_points,
                missing_points=result.missing_points,
                provider=self.provider,
            )
            error = None
        except Exception as caught_error:
            outcome = None
            coverage = ()
            error = self._error_name(caught_error)

        return LLMScoringAttempt(
            outcome=outcome,
            latency_ms=round((perf_counter() - started_at) * 1000),
            provider=self.provider,
            model=self.model,
            error=error,
            topic_coverage=coverage,
        )

    async def generate_question(
        self,
        *,
        role: str,
        level: str,
        topic: str,
        subtopic: str,
        previous_questions: tuple[str, ...],
    ) -> LLMQuestionGenerationAttempt:
        started_at = perf_counter()
        try:
            body = await asyncio.to_thread(
                _post_json,
                f"{self.base_url}/llm/generate-question",
                {
                    "role": role,
                    "level": level,
                    "target_topic": topic,
                    "target_subtopic": subtopic,
                    "previous_questions": list(previous_questions),
                },
                self.timeout,
            )
            result = _GeneratedQuestionResponse.model_validate(body)
            if result.question_text.casefold() in {text.casefold() for text in previous_questions}:
                raise ValueError("LLM repeated an existing question")
            question = GeneratedQuestion(
                text=result.question_text,
                ideal_answer=result.ideal_answer,
                evaluation_points=tuple(result.evaluation_points),
                topics=tuple(TopicWeight(**item.model_dump()) for item in result.topics),
            )
            error = None
        except Exception as caught_error:
            question = None
            error = self._error_name(caught_error)
        return LLMQuestionGenerationAttempt(
            question=question,
            latency_ms=round((perf_counter() - started_at) * 1000),
            provider=self.provider,
            model=self.model,
            error=error,
        )

    async def generate_baseline_questions(
        self,
        *,
        role: str,
        level: str,
        previous_questions: tuple[str, ...],
    ) -> LLMBaselineGenerationAttempt:
        started_at = perf_counter()
        try:
            body = await asyncio.to_thread(
                _post_json,
                f"{self.base_url}/llm/generate-baseline-questions",
                {
                    "role": role,
                    "level": level,
                    "previous_questions": list(previous_questions),
                },
                self.timeout,
            )
            result = _BaselineQuestionsResponse.model_validate(body)
            previous = {" ".join(text.casefold().split()) for text in previous_questions}
            if any(
                " ".join(item.question_text.casefold().split()) in previous
                for item in result.questions
            ):
                raise ValueError("LLM repeated a previous baseline question")
            questions = tuple(
                BaselineQuestion(
                    area=item.area,
                    text=item.question_text,
                    ideal_answer=item.ideal_answer,
                    evaluation_points=tuple(item.evaluation_points),
                    topics=tuple(TopicWeight(**topic.model_dump()) for topic in item.topics),
                )
                for item in result.questions
            )
            error = None
        except Exception as caught_error:
            questions = None
            error = self._error_name(caught_error)
        return LLMBaselineGenerationAttempt(
            questions=questions,
            latency_ms=round((perf_counter() - started_at) * 1000),
            provider=self.provider,
            model=self.model,
            error=error,
        )

    @staticmethod
    def _error_name(error: Exception) -> str:
        return f"HTTP {error.code}" if isinstance(error, HTTPError) else type(error).__name__
