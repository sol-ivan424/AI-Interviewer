import re
from dataclasses import dataclass
from math import ceil

from app.core.enums import Verdict
from app.models.question import Question


@dataclass(frozen=True, slots=True)
class ScoringOutcome:
    score: int
    max_score: int
    verdict: Verdict
    feedback: str
    matched_points: list[str]
    missing_points: list[str]
    provider: str = "rule_based_fallback"


class ScoringService:
    """Deterministic rule-based scorer used when no external scorer is available."""

    _STOP_WORDS = {
        "а",
        "без",
        "бы",
        "в",
        "все",
        "всех",
        "всё",
        "во",
        "для",
        "до",
        "его",
        "ее",
        "её",
        "и",
        "из",
        "или",
        "их",
        "как",
        "к",
        "между",
        "может",
        "могут",
        "на",
        "не",
        "нужно",
        "но",
        "обычно",
        "означает",
        "он",
        "она",
        "они",
        "от",
        "по",
        "при",
        "с",
        "со",
        "также",
        "то",
        "что",
        "это",
        "является",
        "должен",
        "должна",
        "должны",
        "использовать",
        "использует",
        "используют",
        "используется",
        "используются",
        "a",
        "an",
        "and",
        "are",
        "as",
        "be",
        "by",
        "for",
        "in",
        "is",
        "of",
        "on",
        "or",
        "the",
        "to",
        "with",
    }
    _RU_SUFFIXES = (
        "иями",
        "ями",
        "ами",
        "ых",
        "ение",
        "ений",
        "овать",
        "ировать",
        "ются",
        "ется",
        "ого",
        "ему",
        "ому",
        "ыми",
        "ими",
        "ий",
        "ый",
        "ая",
        "ое",
        "ые",
        "ым",
        "им",
        "ом",
        "ем",
        "ах",
        "ях",
        "ов",
        "ев",
        "ам",
        "ям",
        "ой",
        "ей",
        "ую",
        "юю",
        "ть",
        "ти",
        "ся",
        "ют",
        "ет",
        "ат",
        "ят",
        "ы",
        "и",
        "а",
        "я",
        "у",
        "ю",
        "е",
    )

    @staticmethod
    def _normalize(value: str) -> str:
        """Normalize case, punctuation and whitespace without losing Unicode letters."""

        return " ".join(re.sub(r"[^\w]+|_+", " ", value.casefold()).split())

    @classmethod
    def _token_key(cls, token: str) -> str:
        stem = token
        if re.fullmatch(r"[а-яё]+", token):
            for suffix in cls._RU_SUFFIXES:
                if token.endswith(suffix) and len(token) - len(suffix) >= 3:
                    stem = token[: -len(suffix)]
                    break
            if len(stem) >= 8:
                return stem[:6]
        elif re.fullmatch(r"[a-z]+", token):
            for suffix in ("ing", "ed", "es", "s"):
                if token.endswith(suffix) and len(token) - len(suffix) >= 3:
                    stem = token[: -len(suffix)]
                    break
        return stem

    @classmethod
    def _semantic_tokens(cls, value: str) -> set[str]:
        raw_tokens = cls._normalize(value).split()
        tokens = {
            cls._token_key(token)
            for token in raw_tokens
            if token not in cls._STOP_WORDS and len(token) > 1
        }
        if "stateless" in raw_tokens:
            tokens.update({"самодостаточ", "сесс", "состоян"})
        if "async" in raw_tokens or any(token.startswith("асинх") for token in raw_tokens):
            tokens.update({"async", "асинхр", "await"})
        if {"i", "o"} <= set(raw_tokens) or "io" in raw_tokens:
            tokens.update({"ввод", "вывод"})
        if any("блокир" in token for token in raw_tokens):
            tokens.update({"блокир", "неблок"})
        if any(token.startswith("preprocess") for token in raw_tokens):
            tokens.update({"преобр", "обуча"})
        if any(token.startswith("предсказ") for token in raw_tokens):
            tokens.add("inference")
        return tokens

    @classmethod
    def _is_point_matched(cls, point: str, normalized_answer: str) -> bool:
        """Match a criterion by meaningful token coverage, allowing natural rephrasing."""

        point_tokens = cls._semantic_tokens(point)
        if not point_tokens:
            return False
        answer_tokens = cls._semantic_tokens(normalized_answer)
        overlap = len(point_tokens & answer_tokens)
        required = 1 if len(point_tokens) <= 2 else max(2, ceil(len(point_tokens) * 0.3))
        raw_point_tokens = [
            token
            for token in cls._normalize(point).split()
            if token not in cls._STOP_WORDS and len(token) > 1
        ]
        anchor = max(raw_point_tokens, key=len, default="")
        anchor_matched = len(anchor) >= 8 and cls._token_key(anchor) in answer_tokens
        return overlap >= required or anchor_matched

    @staticmethod
    def _verdict_for_score(score: int) -> Verdict:
        if score >= 8:
            return Verdict.CORRECT
        if score >= 4:
            return Verdict.PARTIALLY_CORRECT
        return Verdict.INCORRECT

    def evaluate(self, question: Question, answer_text: str) -> ScoringOutcome:
        normalized_answer = self._normalize(answer_text)
        if not normalized_answer:
            raise ValueError("answer_text must not be blank")

        matched = [
            point
            for point in question.evaluation_points
            if self._is_point_matched(point, normalized_answer)
        ]
        missing = [point for point in question.evaluation_points if point not in matched]
        criteria_count = len(question.evaluation_points)
        score = round(question.max_score * len(matched) / criteria_count) if criteria_count else 0
        verdict = self._verdict_for_score(score)

        feedback = (
            f"Раскрыто критериев: {len(matched)} из {criteria_count}. "
            f"Оценка: {score}/{question.max_score}."
        )
        return ScoringOutcome(
            score=score,
            max_score=question.max_score,
            verdict=verdict,
            feedback=feedback,
            matched_points=matched,
            missing_points=missing,
        )
