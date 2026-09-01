import pytest

from app.services.recommendations import (
    AnswerEvidenceInput,
    RecommendationPriority,
    RecommendationService,
    SkillScoreInput,
    SkillStatus,
)


def answer(
    *,
    skill: str = "SQL",
    answer_text: str = "JOIN combines rows",
    missing_points: tuple[str, ...] = ("indexes", "transactions"),
) -> AnswerEvidenceInput:
    return AnswerEvidenceInput(
        skill=skill,
        answer_text=answer_text,
        score=4,
        max_score=10,
        verdict="partially_correct",
        matched_points=("JOIN",),
        missing_points=missing_points,
    )


def skill_score(percentage: int, *, skill: str = "SQL") -> SkillScoreInput:
    return SkillScoreInput(
        skill=skill,
        score=percentage,
        max_score=100,
        percentage=percentage,
    )


@pytest.mark.parametrize(
    ("percentage", "expected_status"),
    [
        (39, SkillStatus.WEAK),
        (40, SkillStatus.NEED_REPEAT),
        (69, SkillStatus.NEED_REPEAT),
        (70, SkillStatus.GOOD),
    ],
)
def test_skill_status_thresholds(percentage: int, expected_status: SkillStatus) -> None:
    assert RecommendationService.skill_status(percentage) is expected_status


@pytest.mark.parametrize(
    ("percentage", "expected_priority"),
    [
        (0, RecommendationPriority.HIGH),
        (39, RecommendationPriority.HIGH),
        (40, RecommendationPriority.MEDIUM),
        (69, RecommendationPriority.MEDIUM),
    ],
)
def test_recommendation_priority_thresholds(
    percentage: int, expected_priority: RecommendationPriority
) -> None:
    recommendations = RecommendationService().generate(
        role="backend",
        level="junior",
        answers=[answer()],
        skill_scores=[skill_score(percentage)],
    )

    assert len(recommendations) == 1
    assert recommendations[0].priority is expected_priority
    assert recommendations[0].current_percentage == percentage


@pytest.mark.parametrize("percentage", [70, 100])
def test_no_recommendation_for_good_skill(percentage: int) -> None:
    recommendations = RecommendationService().generate(
        role="backend",
        level="junior",
        answers=[answer()],
        skill_scores=[skill_score(percentage)],
    )

    assert recommendations == []


@pytest.mark.parametrize("answer_text", ["", "   \n\t"])
def test_empty_answers_return_empty_recommendations(answer_text: str) -> None:
    recommendations = RecommendationService().generate(
        role="backend",
        level="junior",
        answers=[answer(answer_text=answer_text)],
        skill_scores=[skill_score(20)],
    )

    assert recommendations == []


def test_recommendation_content_comes_from_unique_missing_points() -> None:
    recommendations = RecommendationService().generate(
        role="backend",
        level="middle",
        answers=[
            answer(missing_points=(" JOIN ", "indexes")),
            answer(missing_points=("join", "transactions")),
        ],
        skill_scores=[skill_score(39)],
    )

    recommendation = recommendations[0]
    assert recommendation.topics_to_learn == ("JOIN", "indexes", "transactions")
    assert "JOIN, indexes, transactions" in recommendation.reason
    assert recommendation.practice_tasks == (
        "Изучить и закрепить на практике: JOIN.",
        "Изучить и закрепить на практике: indexes.",
        "Изучить и закрепить на практике: transactions.",
    )


def test_weak_skills_filter_is_respected() -> None:
    recommendations = RecommendationService().generate(
        role="backend",
        level="senior",
        answers=[answer(skill="SQL"), answer(skill="HTTP")],
        skill_scores=[skill_score(20, skill="SQL"), skill_score(50, skill="HTTP")],
        weak_skills={"HTTP"},
    )

    assert [recommendation.skill for recommendation in recommendations] == ["HTTP"]
