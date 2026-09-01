class DuplicateEmailError(Exception):
    """Raised when registration attempts to reuse an email address."""


class InvalidCredentialsError(Exception):
    """Raised when an email/password pair cannot be authenticated."""


class InsufficientQuestionsError(Exception):
    """Raised when a role and level do not have enough active questions."""


class InterviewNotFoundError(Exception):
    """Raised when an interview does not exist for the current user."""


class InterviewStateConflictError(Exception):
    """Raised when an interview operation conflicts with its current state."""


class InvalidAnswerError(Exception):
    """Raised when an answer has no meaningful content after normalization."""


class LLMQuestionGenerationError(Exception):
    """Raised when an interview cannot continue without a newly generated question."""
