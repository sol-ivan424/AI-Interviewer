from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class InterviewContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question_number: int = Field(ge=1)
    total_questions: int = Field(ge=1)

    @model_validator(mode="after")
    def validate_question_number(self) -> "InterviewContext":
        if self.question_number > self.total_questions:
            raise ValueError("question_number must not exceed total_questions")
        return self


class InterviewerMessageRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    role: Literal["backend", "ml_engineer", "llm_engineer"]
    level: Literal["junior", "middle", "senior"]
    question_text: str = Field(min_length=1)
    context: InterviewContext


class InterviewerMessageResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    message: str = Field(min_length=1)
