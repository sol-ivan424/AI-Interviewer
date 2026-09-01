from collections.abc import Collection, Sequence
from dataclasses import dataclass

from app.core.enums import RecommendationPriority, SkillStatus


@dataclass(frozen=True, slots=True)
class SkillScoreInput:
    """Aggregated score for one skill, independent from persistence models."""

    skill: str
    score: int
    max_score: int
    percentage: int


@dataclass(frozen=True, slots=True)
class AnswerEvidenceInput:
    """Answer evidence used to explain and personalize a recommendation."""

    skill: str
    answer_text: str
    score: int
    max_score: int
    verdict: str
    matched_points: tuple[str, ...] = ()
    missing_points: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Recommendation:
    skill: str
    priority: RecommendationPriority
    current_percentage: int
    reason: str
    topics_to_learn: tuple[str, ...]
    practice_tasks: tuple[str, ...]


class RecommendationService:
    """Build deterministic rule-based recommendations from scoring evidence."""

    @staticmethod
    def skill_status(percentage: int) -> SkillStatus:
        RecommendationService._validate_percentage(percentage)
        if percentage >= 70:
            return SkillStatus.GOOD
        if percentage >= 40:
            return SkillStatus.NEED_REPEAT
        return SkillStatus.WEAK

    def generate(
        self,
        *,
        role: str,
        level: str,
        answers: Sequence[AnswerEvidenceInput],
        skill_scores: Sequence[SkillScoreInput],
        weak_skills: Collection[str] | None = None,
    ) -> list[Recommendation]:
        """Return recommendations for skills below 70 percent.

        ``role`` and ``level`` are explicit inputs required by the product contract. The
        MVP rules do not branch on them yet, but keeping them in this boundary allows a
        later recommendation model to personalize output without changing its callers.
        """

        if not role.strip() or not level.strip():
            raise ValueError("role and level must not be empty")

        substantive_answers = [answer for answer in answers if answer.answer_text.strip()]
        if not substantive_answers:
            return []

        selected_skills = set(weak_skills) if weak_skills is not None else None
        recommendations: list[Recommendation] = []

        for skill_score in skill_scores:
            self._validate_skill_score(skill_score)
            if skill_score.percentage >= 70:
                continue
            if selected_skills is not None and skill_score.skill not in selected_skills:
                continue

            skill_answers = [
                answer for answer in substantive_answers if answer.skill == skill_score.skill
            ]
            if not skill_answers:
                continue

            topics = self._unique_missing_points(skill_answers)
            priority = (
                RecommendationPriority.HIGH
                if skill_score.percentage < 40
                else RecommendationPriority.MEDIUM
            )
            recommendations.append(
                Recommendation(
                    skill=skill_score.skill,
                    priority=priority,
                    current_percentage=skill_score.percentage,
                    reason=self._reason(skill_score.skill, topics),
                    topics_to_learn=topics,
                    practice_tasks=tuple(
                        f"Изучить и закрепить на практике: {topic}." for topic in topics
                    ),
                )
            )

        return recommendations

    @staticmethod
    def _unique_missing_points(answers: Sequence[AnswerEvidenceInput]) -> tuple[str, ...]:
        result: list[str] = []
        seen: set[str] = set()
        for answer in answers:
            for point in answer.missing_points:
                cleaned = " ".join(point.split())
                identity = cleaned.casefold()
                if cleaned and identity not in seen:
                    seen.add(identity)
                    result.append(cleaned)
        return tuple(result)

    @staticmethod
    def _reason(skill: str, topics: tuple[str, ...]) -> str:
        if not topics:
            return f"Нужно лучше разобраться с {skill}."

        joined_topics = ", ".join(topics)
        return (
            f"Нужно лучше разобраться с {skill}, потому что в ответах "
            f"были пропущены: {joined_topics}."
        )

    @staticmethod
    def _validate_skill_score(skill_score: SkillScoreInput) -> None:
        if not skill_score.skill.strip():
            raise ValueError("skill must not be empty")
        if skill_score.max_score < 0 or skill_score.score < 0:
            raise ValueError("score values must not be negative")
        if skill_score.score > skill_score.max_score:
            raise ValueError("score must not exceed max_score")
        RecommendationService._validate_percentage(skill_score.percentage)

    @staticmethod
    def _validate_percentage(percentage: int) -> None:
        if not 0 <= percentage <= 100:
            raise ValueError("percentage must be between 0 and 100")
