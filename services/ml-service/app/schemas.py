from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class LevelPredictionRequest(StrictModel):
    average_score: float = Field(ge=0, le=100)
    backend_score: float = Field(ge=0, le=100)
    ml_score: float = Field(ge=0, le=100)
    llm_score: float = Field(ge=0, le=100)
    answers_count: int = Field(ge=0)
    correct_answers_count: int = Field(ge=0)
    partial_answers_count: int = Field(ge=0)
    wrong_answers_count: int = Field(ge=0)
    weak_skills_count: int = Field(ge=0)
    average_answer_length: float = Field(ge=0)

    @model_validator(mode="after")
    def validate_answer_counts(self) -> "LevelPredictionRequest":
        outcomes = (
            self.correct_answers_count + self.partial_answers_count + self.wrong_answers_count
        )
        if outcomes > self.answers_count:
            raise ValueError("answer outcome counts must not exceed answers_count")
        return self


class WeaknessEvidence(StrictModel):
    answer_text: str = Field(min_length=1)
    missing_points: list[str] = Field(default_factory=list)
    score: int = Field(ge=0)
    max_score: int = Field(gt=0)

    @model_validator(mode="after")
    def validate_score(self) -> "WeaknessEvidence":
        if self.score > self.max_score:
            raise ValueError("score must not exceed max_score")
        return self


class WeakTopicRequest(StrictModel):
    answers: list[WeaknessEvidence] = Field(min_length=1)


class PredictionResponse(StrictModel):
    prediction: str
    confidence: float = Field(ge=0, le=1)
    probabilities: dict[str, float]
    model_version: str


class RecommendationRankItem(StrictModel):
    skill: str = Field(min_length=1)
    priority: Literal["high", "medium"]
    current_percentage: int = Field(ge=0, le=100)
    topics_count: int = Field(ge=0)


class RecommendationRankRequest(StrictModel):
    recommendations: list[RecommendationRankItem]

    @model_validator(mode="after")
    def validate_unique_skills(self) -> "RecommendationRankRequest":
        skills = [item.skill.casefold() for item in self.recommendations]
        if len(skills) != len(set(skills)):
            raise ValueError("recommendation skills must be unique")
        return self


class RankingResponse(StrictModel):
    prediction: list[str]
    model_version: str


class KnowledgeNode(StrictModel):
    topic: str = Field(min_length=1)
    subtopic: str = Field(min_length=1)
    score: float = Field(ge=0, le=100)
    confidence: float = Field(ge=0, le=1)
    evidence_count: int = Field(ge=0)
    evidence_weight: float = Field(ge=0)


class KnowledgeObservation(StrictModel):
    topic: str = Field(min_length=1)
    subtopic: str = Field(min_length=1)
    question_weight: float = Field(gt=0, le=1)
    coverage: float = Field(ge=0, le=1)


class KnowledgeUpdateRequest(StrictModel):
    nodes: list[KnowledgeNode]
    observations: list[KnowledgeObservation]

    @model_validator(mode="after")
    def validate_nodes(self) -> "KnowledgeUpdateRequest":
        if not self.nodes and not self.observations:
            raise ValueError("nodes or observations must not be empty")
        keys = [(node.topic.casefold(), node.subtopic.casefold()) for node in self.nodes]
        if len(keys) != len(set(keys)):
            raise ValueError("knowledge nodes must be unique")
        return self


class KnowledgeTarget(StrictModel):
    topic: str
    subtopic: str


class KnowledgeUpdateResponse(StrictModel):
    nodes: list[KnowledgeNode]
    next_target: KnowledgeTarget


class HealthResponse(StrictModel):
    status: Literal["ok"]
    model_version: str
    topic_classifier_loaded: bool
    level_predictor_loaded: bool
