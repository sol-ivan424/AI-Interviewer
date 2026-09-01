import pytest

from app.core.enums import Verdict
from app.data.question_bank import QUESTION_BANK
from app.models.question import Question
from app.services.scoring import ScoringService


@pytest.fixture
def question() -> Question:
    return Question(
        role="backend",
        level="junior",
        skill="HTTP",
        text="Что важно знать об HTTP?",
        ideal_answer="HTTP использует методы и коды ответа, а GET безопасен.",
        evaluation_points=[
            "HTTP использует методы",
            "HTTP использует коды ответа",
            "GET является безопасным методом",
            "POST создаёт ресурс",
        ],
        max_score=10,
        is_active=True,
    )


def test_empty_answer_is_rejected(question: Question) -> None:
    with pytest.raises(ValueError, match="answer_text must not be blank"):
        ScoringService().evaluate(question, " \n\t !!! ")


def test_full_answer_has_high_score(question: Question) -> None:
    outcome = ScoringService().evaluate(
        question,
        (
            "HTTP использует методы и коды ответа. "
            "GET является безопасным методом, POST создаёт ресурс."
        ),
    )

    assert outcome.score == 10
    assert outcome.max_score == 10
    assert outcome.verdict is Verdict.CORRECT
    assert outcome.matched_points == question.evaluation_points
    assert outcome.missing_points == []
    assert outcome.provider == "rule_based_fallback"
    assert "4" in outcome.feedback
    assert "10/10" in outcome.feedback


def test_partial_answer_has_medium_score_and_preserves_point_order(
    question: Question,
) -> None:
    outcome = ScoringService().evaluate(
        question,
        "Коды ответа использует HTTP; также HTTP использует разные методы.",
    )

    assert outcome.score == 5
    assert outcome.verdict is Verdict.PARTIALLY_CORRECT
    assert outcome.matched_points == question.evaluation_points[:2]
    assert outcome.missing_points == question.evaluation_points[2:]


def test_irrelevant_answer_has_low_score(question: Question) -> None:
    outcome = ScoringService().evaluate(question, "Docker запускает изолированные контейнеры.")

    assert outcome.score == 0
    assert outcome.verdict is Verdict.INCORRECT
    assert outcome.matched_points == []
    assert outcome.missing_points == question.evaluation_points


def test_normalization_ignores_case_punctuation_underscores_and_extra_spaces(
    question: Question,
) -> None:
    outcome = ScoringService().evaluate(
        question,
        "  http___ИСПОЛЬЗУЕТ,,,   МЕТОДЫ!!!  ",
    )

    assert outcome.score == 2
    assert outcome.matched_points == ["HTTP использует методы"]
    assert outcome.verdict is Verdict.INCORRECT


def test_verdict_depends_only_on_resulting_score() -> None:
    scorer = ScoringService()

    assert scorer._verdict_for_score(8) is Verdict.CORRECT
    assert scorer._verdict_for_score(7) is Verdict.PARTIALLY_CORRECT
    assert scorer._verdict_for_score(4) is Verdict.PARTIALLY_CORRECT
    assert scorer._verdict_for_score(3) is Verdict.INCORRECT


def test_question_without_evaluation_points_returns_zero_score() -> None:
    question = Question(
        role="backend",
        level="junior",
        skill="HTTP",
        text="Что такое HTTP?",
        ideal_answer="Протокол прикладного уровня.",
        evaluation_points=[],
        max_score=10,
        is_active=True,
    )

    outcome = ScoringService().evaluate(question, "HTTP — протокол.")

    assert outcome.score == 0
    assert outcome.verdict is Verdict.INCORRECT
    assert outcome.matched_points == []
    assert outcome.missing_points == []


def test_real_seed_ideal_answers_receive_high_scores() -> None:
    scorer = ScoringService()

    for seed in QUESTION_BANK:
        question = Question(
            role=seed.role,
            level=seed.level,
            skill=seed.skill,
            text=seed.text,
            ideal_answer=seed.ideal_answer,
            evaluation_points=list(seed.evaluation_points),
            max_score=seed.max_score,
            is_active=seed.is_active,
        )
        outcome = scorer.evaluate(question, seed.ideal_answer)
        assert outcome.score >= 8, (
            f"Ideal answer for {seed.role}/{seed.level}/{seed.skill} scored {outcome.score}: "
            f"missing={outcome.missing_points}"
        )


def test_natural_rest_paraphrase_covers_all_criteria() -> None:
    seed = QUESTION_BANK[0]
    question = Question(
        role=seed.role,
        level=seed.level,
        skill=seed.skill,
        text=seed.text,
        ideal_answer=seed.ideal_answer,
        evaluation_points=list(seed.evaluation_points),
        max_score=seed.max_score,
        is_active=seed.is_active,
    )

    outcome = ScoringService().evaluate(
        question,
        (
            "REST — это архитектурный стиль, не отдельный протокол. Ресурс имеет URI, "
            "к нему применяют стандартные HTTP методы и коды ответа. Каждый запрос "
            "самодостаточен: сервер не сохраняет клиентскую сессию между запросами."
        ),
    )

    assert outcome.score == 10
    assert outcome.matched_points == list(seed.evaluation_points)
