from enum import StrEnum


class Role(StrEnum):
    BACKEND = "backend"
    ML_ENGINEER = "ml_engineer"
    LLM_ENGINEER = "llm_engineer"


class Level(StrEnum):
    JUNIOR = "junior"
    MIDDLE = "middle"
    SENIOR = "senior"


class InterviewStatus(StrEnum):
    IN_PROGRESS = "in_progress"
    FINISHED = "finished"


class FinishedReason(StrEnum):
    COMPLETED = "completed"
    MANUAL = "manual"


class Verdict(StrEnum):
    CORRECT = "correct"
    PARTIALLY_CORRECT = "partially_correct"
    INCORRECT = "incorrect"


class SkillStatus(StrEnum):
    GOOD = "good"
    NEED_REPEAT = "need_repeat"
    WEAK = "weak"


class RecommendationPriority(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
