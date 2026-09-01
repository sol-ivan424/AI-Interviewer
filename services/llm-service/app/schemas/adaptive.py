import math
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

NonEmptyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
Role = Literal["backend", "ml_engineer", "llm_engineer"]
Level = Literal["junior", "middle", "senior"]


class QuestionTopic(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    topic: str = Field(min_length=1, max_length=100)
    subtopic: str = Field(min_length=1, max_length=150)
    weight: float = Field(gt=0, le=1)


def validate_topic_weights(topics: list[QuestionTopic]) -> None:
    pairs = [(item.topic.casefold(), item.subtopic.casefold()) for item in topics]
    if len(pairs) != len(set(pairs)):
        raise ValueError("topic and subtopic pairs must be unique")
    if topics and abs(math.fsum(item.weight for item in topics) - 1.0) > 0.01 + 1e-9:
        raise ValueError("topic weights must sum to 1 with tolerance 0.01")


class TopicCoverage(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    topic: str = Field(min_length=1, max_length=100)
    subtopic: str = Field(min_length=1, max_length=150)
    coverage: float = Field(ge=0, le=1)


class QuestionAnalysisRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    role: Role
    level: Level
    skill: str = Field(min_length=1, max_length=100)
    question_text: str = Field(min_length=1, max_length=4000)
    ideal_answer: str = Field(min_length=1, max_length=12000)
    evaluation_points: list[NonEmptyText] = Field(min_length=1, max_length=20)


class QuestionAnalysisResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    topics: list[QuestionTopic] = Field(min_length=1, max_length=8)

    @model_validator(mode="after")
    def validate_topics(self) -> "QuestionAnalysisResponse":
        validate_topic_weights(self.topics)
        return self


class QuestionGenerationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    role: Role
    level: Level
    target_topic: str = Field(min_length=1, max_length=100)
    target_subtopic: str = Field(min_length=1, max_length=150)
    previous_questions: list[NonEmptyText] = Field(default_factory=list, max_length=20)


class QuestionGenerationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    question_text: str = Field(min_length=1, max_length=4000)
    ideal_answer: str = Field(min_length=1, max_length=12000)
    evaluation_points: list[NonEmptyText] = Field(min_length=1, max_length=20)
    topics: list[QuestionTopic] = Field(min_length=1, max_length=8)

    @model_validator(mode="after")
    def validate_evaluation_points(self) -> "QuestionGenerationResponse":
        validate_topic_weights(self.topics)
        normalized = [point.casefold() for point in self.evaluation_points]
        if len(normalized) != len(set(normalized)):
            raise ValueError("evaluation_points must be unique")
        return self


class BaselineQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    area: str = Field(min_length=1, max_length=100)
    question_text: str = Field(min_length=1, max_length=4000)
    ideal_answer: str = Field(min_length=1, max_length=12000)
    evaluation_points: list[NonEmptyText] = Field(min_length=1, max_length=20)
    topics: list[QuestionTopic] = Field(min_length=1, max_length=8)

    @model_validator(mode="after")
    def validate_question(self) -> "BaselineQuestion":
        validate_topic_weights(self.topics)
        normalized = [point.casefold() for point in self.evaluation_points]
        if len(normalized) != len(set(normalized)):
            raise ValueError("evaluation_points must be unique")
        if self.area.casefold() not in {item.topic.casefold() for item in self.topics}:
            raise ValueError("topics must include the baseline area")
        return self


class BaselineQuestionGenerationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    role: Role
    level: Level
    previous_questions: list[NonEmptyText] = Field(default_factory=list, max_length=50)


class BaselineQuestionGenerationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    questions: list[BaselineQuestion] = Field(min_length=5, max_length=5)

    @model_validator(mode="after")
    def validate_questions(self) -> "BaselineQuestionGenerationResponse":
        areas = [question.area.casefold() for question in self.questions]
        texts = [" ".join(question.question_text.casefold().split()) for question in self.questions]
        if len(set(areas)) != 5:
            raise ValueError("baseline areas must be unique")
        if len(set(texts)) != 5:
            raise ValueError("baseline questions must be unique")
        return self
