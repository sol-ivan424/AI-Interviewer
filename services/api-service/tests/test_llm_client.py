import asyncio
import json
from dataclasses import replace
from urllib.error import URLError

import pytest

from app.core.config import Settings
from app.core.enums import Verdict
from app.services.llm import LLMEvaluationInput, LLMScoringClient, TopicWeight


def client() -> LLMScoringClient:
    return LLMScoringClient(
        Settings(
            database_url="sqlite+aiosqlite:///:memory:",
            jwt_secret_key="test-secret-key-that-is-long-enough",
            llm_service_url="http://llm-service:8001",
            llm_timeout_seconds=1,
        )
    )


def payload() -> LLMEvaluationInput:
    return LLMEvaluationInput(
        role="backend",
        level="junior",
        skill="REST",
        question_text="Что такое REST?",
        ideal_answer="REST — архитектурный стиль.",
        evaluation_points=("архитектурный стиль", "ресурсы"),
        user_answer="REST — стиль API вокруг ресурсов.",
    )


def test_valid_llm_response_recalculates_verdict(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.llm._post_json",
        lambda *_: {
            "score": 9,
            "max_score": 10,
            "verdict": "incorrect",
            "feedback": "Хороший ответ.",
            "matched_points": ["архитектурный стиль", "ресурсы"],
            "missing_points": [],
        },
    )

    attempt = asyncio.run(client().evaluate(payload()))

    assert attempt.success is True
    assert attempt.outcome is not None
    assert attempt.outcome.verdict == Verdict.CORRECT
    assert attempt.outcome.provider == "ollama"


def test_topic_coverage_drives_weighted_score(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.llm._post_json",
        lambda *_: {
            "score": 10,
            "max_score": 10,
            "verdict": "correct",
            "feedback": "Weighted feedback.",
            "matched_points": list(payload().evaluation_points),
            "missing_points": [],
            "topic_coverage": [
                {"topic": "API", "subtopic": "REST", "coverage": 0.8},
                {"topic": "API", "subtopic": "Resources", "coverage": 0.2},
            ],
        },
    )
    weighted = replace(
        payload(),
        topics=(
            TopicWeight(topic="API", subtopic="REST", weight=0.75),
            TopicWeight(topic="API", subtopic="Resources", weight=0.25),
        ),
    )

    attempt = asyncio.run(client().evaluate(weighted))

    assert attempt.outcome is not None
    assert attempt.outcome.score == 7
    assert len(attempt.topic_coverage) == 2


def test_invalid_llm_criteria_become_controlled_failure(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.llm._post_json",
        lambda *_: {
            "score": 5,
            "max_score": 10,
            "verdict": "partially_correct",
            "feedback": "Ответ неполный.",
            "matched_points": ["выдуманный критерий"],
            "missing_points": [],
        },
    )

    attempt = asyncio.run(client().evaluate(payload()))

    assert attempt.success is False
    assert attempt.outcome is None
    assert attempt.error == "ValueError"


@pytest.mark.parametrize(
    "error",
    [
        TimeoutError("timeout"),
        URLError("offline"),
        json.JSONDecodeError("invalid JSON", "not-json", 0),
    ],
)
def test_transport_and_json_errors_become_controlled_failures(monkeypatch, error) -> None:
    def fail(*_args) -> object:
        raise error

    monkeypatch.setattr("app.services.llm._post_json", fail)

    attempt = asyncio.run(client().evaluate(payload()))

    assert attempt.success is False
    assert attempt.outcome is None
    assert attempt.error == type(error).__name__
