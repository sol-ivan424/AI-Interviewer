import asyncio
import json
import logging
from email.message import Message

from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.services.openai_compatible_client import (
    LLMUnavailableError,
    OpenAICompatibleClient,
    ollama_schema,
)

EVALUATION_REQUEST = {
    "role": "backend",
    "level": "junior",
    "skill": "REST",
    "question_text": "Что такое REST API?",
    "ideal_answer": "REST — архитектурный стиль вокруг ресурсов.",
    "evaluation_points": ["REST это архитектурный стиль", "API строится вокруг ресурсов"],
    "user_answer": "REST использует HTTP.",
}


class FakeOllamaClient:
    def __init__(self, response: dict[str, object] | str | Exception) -> None:
        self.response = response

    async def is_available(self) -> bool:
        if isinstance(self.response, Exception):
            raise self.response
        return True

    async def generate(
        self, prompt: str, prompt_type: str, response_schema: dict[str, object]
    ) -> str:
        assert prompt
        assert response_schema["type"] == "object"
        assert prompt_type in {
            "analyze_question",
            "evaluate_answer",
            "generate_baseline_questions",
            "generate_question",
            "interviewer_message",
        }
        if isinstance(self.response, Exception):
            raise self.response
        return (
            self.response
            if isinstance(self.response, str)
            else json.dumps(self.response, ensure_ascii=False)
        )


def test_health_endpoints() -> None:
    app.state.llm_client = FakeOllamaClient({})
    with TestClient(app) as client:
        assert client.get("/health").json() == {
            "status": "ok",
            "runtime": settings.llm_provider,
        }
        assert client.get("/llm/health").json() == {
            "status": "ok",
            "provider": "openai_compatible",
            "model": "gpt-4.1-mini",
            "available": True,
        }
        app.state.llm_client = FakeOllamaClient(LLMUnavailableError("offline"))
        assert client.get("/llm/health").json() == {
            "status": "ok",
            "provider": "openai_compatible",
            "model": "gpt-4.1-mini",
            "available": False,
        }


def test_evaluation_validates_and_recalculates_verdict() -> None:
    app.state.llm_client = FakeOllamaClient(
        {
            "score": 8,
            "max_score": 10,
            "verdict": "incorrect",
            "feedback": "Хороший ответ.",
            "matched_points": ["REST это архитектурный стиль"],
            "missing_points": ["API строится вокруг ресурсов"],
            "topic_coverage": [],
        }
    )
    with TestClient(app) as client:
        response = client.post("/llm/evaluate-answer", json=EVALUATION_REQUEST)
    assert response.status_code == 200
    assert response.json()["verdict"] == "correct"


def test_topic_analysis_and_coverage_require_matching_unique_pairs() -> None:
    app.state.llm_client = FakeOllamaClient(
        {
            "topics": [
                {"topic": "HTTP", "subtopic": "Caching", "weight": 0.6},
                {"topic": "HTTP", "subtopic": "Validation", "weight": 0.4},
            ]
        }
    )
    analysis_request = {
        "role": "backend",
        "level": "junior",
        "skill": "HTTP",
        "question_text": "How does HTTP caching work?",
        "ideal_answer": "Caches reuse fresh responses and validate stale responses.",
        "evaluation_points": ["freshness", "validators"],
    }
    with TestClient(app) as client:
        analysis = client.post("/llm/analyze-question", json=analysis_request)
        assert analysis.status_code == 200

        app.state.llm_client = FakeOllamaClient(
            {
                "topics": [
                    {"topic": "HTTP", "subtopic": "Caching", "weight": 0.5},
                    {"topic": "http", "subtopic": "caching", "weight": 0.5},
                ]
            }
        )
        duplicate_analysis = client.post("/llm/analyze-question", json=analysis_request)
        assert duplicate_analysis.status_code == 502

        weighted_request = {
            **EVALUATION_REQUEST,
            "topics": analysis.json()["topics"],
        }
        app.state.llm_client = FakeOllamaClient(
            {
                "score": 7,
                "max_score": 10,
                "verdict": "partially_correct",
                "feedback": "Good coverage.",
                "matched_points": EVALUATION_REQUEST["evaluation_points"],
                "missing_points": [],
                "topic_coverage": [
                    {"topic": "HTTP", "subtopic": "Caching", "coverage": 0.8},
                    {"topic": "HTTP", "subtopic": "Validation", "coverage": 0.5},
                ],
            }
        )
        evaluation = client.post("/llm/evaluate-answer", json=weighted_request)
        assert evaluation.status_code == 200
        assert len(evaluation.json()["topic_coverage"]) == 2

        app.state.llm_client = FakeOllamaClient(
            {
                "score": 7,
                "max_score": 10,
                "verdict": "partially_correct",
                "feedback": "Incomplete coverage.",
                "matched_points": EVALUATION_REQUEST["evaluation_points"],
                "missing_points": [],
                "topic_coverage": [{"topic": "HTTP", "subtopic": "Caching", "coverage": 0.8}],
            }
        )
        mismatched_coverage = client.post("/llm/evaluate-answer", json=weighted_request)
        assert mismatched_coverage.status_code == 502

        invalid_weights = client.post(
            "/llm/evaluate-answer",
            json={
                **weighted_request,
                "topics": [
                    {"topic": "HTTP", "subtopic": "Caching", "weight": 0.4},
                    {"topic": "HTTP", "subtopic": "Validation", "weight": 0.4},
                ],
            },
        )
        assert invalid_weights.status_code == 422


def test_question_generation_rejects_exact_repeat() -> None:
    request = {
        "role": "backend",
        "level": "middle",
        "target_topic": "Databases",
        "target_subtopic": "Indexes",
        "previous_questions": ["When should you use an index?"],
    }
    response = {
        "question_text": "How does a composite index work?",
        "ideal_answer": "It orders rows by multiple indexed columns.",
        "evaluation_points": ["column order", "leftmost prefix"],
        "topics": [{"topic": "Databases", "subtopic": "Indexes", "weight": 1.0}],
    }
    with TestClient(app) as client:
        app.state.llm_client = FakeOllamaClient(response)
        generated = client.post("/llm/generate-question", json=request)
        assert generated.status_code == 200

        app.state.llm_client = FakeOllamaClient(
            {**response, "question_text": "  WHEN should you use an index? "}
        )
        repeated = client.post("/llm/generate-question", json=request)
        assert repeated.status_code == 502


def test_baseline_generation_requires_five_new_areas() -> None:
    questions = [
        {
            "area": f"Area {number}",
            "question_text": f"Question {number}?",
            "ideal_answer": f"Answer {number}",
            "evaluation_points": [f"Criterion {number}"],
            "topics": [{"topic": f"Area {number}", "subtopic": f"Basics {number}", "weight": 1.0}],
        }
        for number in range(1, 6)
    ]
    request = {
        "role": "backend",
        "level": "junior",
        "previous_questions": ["Old question?"],
    }
    with TestClient(app) as client:
        app.state.llm_client = FakeOllamaClient({"questions": questions})
        response = client.post("/llm/generate-baseline-questions", json=request)
        assert response.status_code == 200

        app.state.llm_client = FakeOllamaClient(
            {"questions": [{**questions[0], "question_text": "Old question?"}, *questions[1:]]}
        )
        assert client.post("/llm/generate-baseline-questions", json=request).status_code == 502


def test_interviewer_message_is_structured() -> None:
    app.state.llm_client = FakeOllamaClient({"message": "Следующий вопрос: что такое REST?"})
    with TestClient(app) as client:
        response = client.post(
            "/llm/interviewer-message",
            json={
                "role": "backend",
                "level": "junior",
                "question_text": "Что такое REST?",
                "context": {"question_number": 2, "total_questions": 5},
            },
        )
    assert response.json() == {"message": "Следующий вопрос: что такое REST?"}


def test_invalid_response_and_timeout_are_controlled() -> None:
    with TestClient(app) as client:
        app.state.llm_client = FakeOllamaClient({"score": 11})
        assert client.post("/llm/evaluate-answer", json=EVALUATION_REQUEST).status_code == 502

        app.state.llm_client = FakeOllamaClient("```json\n{}\n```")
        assert client.post("/llm/evaluate-answer", json=EVALUATION_REQUEST).status_code == 502

        app.state.llm_client = FakeOllamaClient(LLMUnavailableError("timeout"))
        assert client.post("/llm/evaluate-answer", json=EVALUATION_REQUEST).status_code == 503


def test_api_logs_exclude_key_prompt_and_response(monkeypatch, caplog) -> None:
    secret_prompt = "password=LogSecretPassword123 token=secret-token"
    secret_response = "secret model response"
    monkeypatch.setattr(
        OpenAICompatibleClient,
        "_request_json",
        lambda *_args: {"choices": [{"message": {"content": secret_response}}]},
    )
    client = OpenAICompatibleClient(
        base_url="https://llm.example",
        api_key="LogSecretApiKey123",
        provider="openai_compatible",
        model="llama3.1:8b",
        timeout_seconds=1,
        temperature=0.2,
        max_tokens=10,
    )
    caplog.set_level(logging.INFO)

    asyncio.run(client.generate(secret_prompt, "evaluate_answer", {"type": "object"}))

    assert secret_prompt not in caplog.text
    assert secret_response not in caplog.text
    assert "LogSecretApiKey123" not in caplog.text
    assert "prompt_type=evaluate_answer" in caplog.text


def test_openai_compatible_request_uses_chat_completions_and_bearer_key(monkeypatch) -> None:
    captured = {}

    class FakeResponse:
        headers = Message()

        def __enter__(self):
            return self

        def __exit__(self, *_args) -> None:
            return None

        def read(self) -> bytes:
            return b'{"choices":[{"message":{"content":"{}"}}]}'

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["authorization"] = request.get_header("Authorization")
        captured["timeout"] = timeout
        captured["payload"] = json.loads(request.data)
        return FakeResponse()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    client = OpenAICompatibleClient(
        base_url="https://llm.example",
        api_key="secret-key",
        provider="openai_compatible",
        model="test-model",
        timeout_seconds=3,
        temperature=0.2,
        max_tokens=100,
    )

    assert asyncio.run(client.generate("prompt", "evaluate_answer", {"type": "object"})) == "{}"
    assert captured["url"] == "https://llm.example/v1/chat/completions"
    assert captured["authorization"] == "Bearer secret-key"
    assert captured["timeout"] == 3
    assert captured["payload"]["response_format"] == {
        "type": "json_schema",
        "json_schema": {
            "name": "evaluate_answer",
            "strict": True,
            "schema": {"type": "object"},
        },
    }
    assert "reasoning_effort" not in captured["payload"]


def test_ollama_request_disables_reasoning(monkeypatch) -> None:
    captured = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args) -> None:
            return None

        def read(self) -> bytes:
            return b'{"message":{"content":"{}"}}'

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["payload"] = json.loads(request.data)
        return FakeResponse()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    client = OpenAICompatibleClient(
        base_url="http://ollama:11434",
        api_key="ollama",
        provider="ollama",
        model="qwen3.5:9b",
        timeout_seconds=3,
        temperature=0.2,
        max_tokens=100,
    )

    assert asyncio.run(client.generate("prompt", "evaluate_answer", {"type": "object"})) == "{}"
    assert captured["url"] == "http://ollama:11434/api/chat"
    assert captured["payload"]["think"] is False
    assert captured["payload"]["format"] == {"type": "object"}
    assert captured["payload"]["options"] == {"temperature": 0.2, "num_predict": 100}


def test_ollama_schema_inlines_refs_and_leaves_validation_to_pydantic() -> None:
    schema = {
        "$defs": {
            "Item": {
                "type": "string",
                "minLength": 1,
                "maxLength": 10,
                "title": "Item",
            }
        },
        "type": "array",
        "items": {"$ref": "#/$defs/Item"},
        "minItems": 5,
        "maxItems": 5,
    }

    assert ollama_schema(schema) == {"type": "array", "items": {"type": "string"}}
