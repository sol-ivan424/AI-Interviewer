import asyncio
import json
from urllib.error import URLError

import pytest

from app.services.ml import MLRecommendationClient, MLRecommendationInput


def client(base_url: str = "http://ml-service:8002") -> MLRecommendationClient:
    return MLRecommendationClient(base_url, timeout_seconds=1)


def recommendations() -> list[MLRecommendationInput]:
    return [
        MLRecommendationInput(skill="SQL", priority="high", current_percentage=20, topics_count=3),
        MLRecommendationInput(
            skill="Docker", priority="medium", current_percentage=50, topics_count=1
        ),
    ]


def test_valid_response_returns_exact_ranking_and_payload(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def respond(url: str, payload: dict[str, object], timeout: float) -> object:
        captured.update(url=url, payload=payload, timeout=timeout)
        return {
            "prediction": ["Docker", "SQL"],
            "confidence": 0.8,
            "probabilities": {"Docker": 0.6, "SQL": 0.4},
            "model_version": "recommendation-ranker-v1",
        }

    monkeypatch.setattr("app.services.ml._post_json", respond)

    result = asyncio.run(client().rank(recommendations=recommendations()))

    assert result == ("Docker", "SQL")
    assert captured == {
        "url": "http://ml-service:8002/ml/recommendations/rank",
        "payload": {
            "recommendations": [
                {
                    "skill": "SQL",
                    "priority": "high",
                    "current_percentage": 20,
                    "topics_count": 3,
                },
                {
                    "skill": "Docker",
                    "priority": "medium",
                    "current_percentage": 50,
                    "topics_count": 1,
                },
            ],
        },
        "timeout": 1,
    }


@pytest.mark.parametrize(
    "prediction",
    [
        ["SQL"],
        ["SQL", "REST"],
        ["SQL", "SQL"],
        ["SQL", "Docker", "REST"],
    ],
)
def test_non_permutation_response_is_controlled_failure(monkeypatch, prediction: list[str]) -> None:
    monkeypatch.setattr(
        "app.services.ml._post_json",
        lambda *_args: {"prediction": prediction},
    )

    result = asyncio.run(client().rank(recommendations=recommendations()))

    assert result is None


@pytest.mark.parametrize(
    "error",
    [
        TimeoutError(),
        URLError("unavailable"),
        json.JSONDecodeError("invalid", "{", 0),
    ],
)
def test_transport_and_decode_errors_are_controlled_failures(monkeypatch, error: Exception) -> None:
    def fail(*_args) -> object:
        raise error

    monkeypatch.setattr("app.services.ml._post_json", fail)

    result = asyncio.run(client().rank(recommendations=recommendations()))

    assert result is None


@pytest.mark.parametrize("base_url, items", [("", recommendations()), ("http://ml", [])])
def test_disabled_or_empty_input_does_not_call_service(monkeypatch, base_url, items) -> None:
    def unexpected(*_args) -> object:
        raise AssertionError("ML service must not be called")

    monkeypatch.setattr("app.services.ml._post_json", unexpected)

    result = asyncio.run(client(base_url).rank(recommendations=items))

    assert result is None
