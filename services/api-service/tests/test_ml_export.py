from app.models.answer import Answer
from app.models.interview import Interview
from app.models.question import Question
from app.scripts.export_ml_training_data import SCHEMA_VERSION, _level_record


def test_level_record_uses_anonymized_aggregates() -> None:
    interview = Interview(role="backend", level="middle", finished_reason="completed")
    rows = [
        (
            Answer(
                answer_text="secret@example.com",
                score=8,
                max_score=10,
                verdict="correct",
                feedback="ok",
                matched_points=[],
                missing_points=[],
                scoring_provider="rule",
            ),
            Question(skill="SQL", max_score=10),
        ),
        (
            Answer(
                answer_text="short",
                score=2,
                max_score=10,
                verdict="incorrect",
                feedback="no",
                matched_points=[],
                missing_points=[],
                scoring_provider="rule",
            ),
            Question(skill="Docker", max_score=10),
        ),
    ]

    record = _level_record(interview, rows)

    assert record == {
        "schema_version": SCHEMA_VERSION,
        "average_score": 50.0,
        "backend_score": 50.0,
        "ml_score": 0.0,
        "llm_score": 0.0,
        "answers_count": 2,
        "correct_answers_count": 1,
        "partial_answers_count": 0,
        "wrong_answers_count": 1,
        "weak_skills_count": 1,
        "average_answer_length": 11.5,
        "target_level": "middle",
    }
    assert "secret@example.com" not in str(record)
