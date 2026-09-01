from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.schemas.adaptive import QuestionTopic, TopicCoverage, validate_topic_weights

Verdict = Literal["correct", "partially_correct", "incorrect"]
NonEmptyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class EvaluationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    role: Literal["backend", "ml_engineer", "llm_engineer"]
    level: Literal["junior", "middle", "senior"]
    skill: str = Field(min_length=1)
    question_text: str = Field(min_length=1)
    ideal_answer: str = Field(min_length=1)
    evaluation_points: list[NonEmptyText] = Field(min_length=1)
    user_answer: str = Field(min_length=1)
    topics: list[QuestionTopic] = Field(default_factory=list, max_length=8)

    @model_validator(mode="after")
    def validate_topics(self) -> "EvaluationRequest":
        validate_topic_weights(self.topics)
        return self


class EvaluationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    score: int = Field(ge=0, le=10, strict=True)
    max_score: Literal[10]
    verdict: Verdict
    feedback: str = Field(min_length=1)
    matched_points: list[NonEmptyText]
    missing_points: list[NonEmptyText]
    topic_coverage: list[TopicCoverage]
