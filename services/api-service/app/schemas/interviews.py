from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.enums import (
    FinishedReason,
    InterviewStatus,
    Level,
    RecommendationPriority,
    Role,
    SkillStatus,
    Verdict,
)


class InterviewCreateRequest(BaseModel):
    role: Role
    level: Level


class InterviewQuestionResponse(BaseModel):
    interview_question_id: UUID
    order_number: int
    skill: str
    text: str


class AnswerFeedbackResponse(BaseModel):
    id: UUID
    score: int
    max_score: int
    verdict: Verdict
    feedback: str
    matched_points: list[str]
    missing_points: list[str]
    scoring_provider: str


class AnswerHistoryResponse(AnswerFeedbackResponse):
    interview_question_id: UUID
    order_number: int
    question_text: str
    skill: str
    answer_text: str


class KnowledgeNodeResponse(BaseModel):
    topic: str
    subtopic: str
    score: float
    confidence: float
    evidence_count: int


class InterviewCreateResponse(BaseModel):
    id: UUID
    role: Role
    level: Level
    status: InterviewStatus
    total_questions: int
    answered_questions: int
    current_question: InterviewQuestionResponse
    created_at: datetime


class InterviewListItemResponse(BaseModel):
    id: UUID
    role: Role
    level: Level
    status: InterviewStatus
    total_score: int
    max_score: int
    percentage: int
    created_at: datetime
    finished_at: datetime | None


class InterviewDetailResponse(BaseModel):
    id: UUID
    role: Role
    level: Level
    status: InterviewStatus
    total_score: int
    total_questions: int
    answered_questions: int
    current_question: InterviewQuestionResponse | None
    answers: list[AnswerHistoryResponse]
    knowledge_graph: list[KnowledgeNodeResponse]
    created_at: datetime
    finished_at: datetime | None


class AnswerSubmitRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    interview_question_id: UUID
    answer_text: str = Field(min_length=1)

    @field_validator("answer_text")
    @classmethod
    def answer_must_not_be_blank(cls, value: str) -> str:
        if not value:
            raise ValueError("answer_text must not be blank")
        return value


class AnswerSubmitResponse(BaseModel):
    answer: AnswerFeedbackResponse
    interview_status: InterviewStatus
    next_question: InterviewQuestionResponse | None
    result_url: str | None = None


class InterviewFinishResponse(BaseModel):
    id: UUID
    status: InterviewStatus
    finished_reason: FinishedReason
    total_score: int
    max_score: int
    percentage: int
    result_url: str


class InterviewResultSummary(BaseModel):
    id: UUID
    role: Role
    level: Level
    status: InterviewStatus
    finished_reason: FinishedReason
    total_score: int
    max_score: int
    percentage: int
    started_at: datetime
    finished_at: datetime


class SkillScoreResponse(BaseModel):
    skill: str
    score: int
    max_score: int
    percentage: int
    status: SkillStatus


class RecommendationResponse(BaseModel):
    skill: str
    priority: RecommendationPriority
    current_percentage: int
    reason: str
    topics_to_learn: list[str]
    practice_tasks: list[str]


class InterviewResultResponse(BaseModel):
    interview: InterviewResultSummary
    skill_scores: list[SkillScoreResponse]
    answers: list[AnswerHistoryResponse]
    recommendations: list[RecommendationResponse]
    knowledge_graph: list[KnowledgeNodeResponse]
