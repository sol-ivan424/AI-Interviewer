import asyncio
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier
from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select

import app.models  # noqa: F401
from app.core.config import Settings
from app.core.enums import Verdict
from app.db.base import Base
from app.main import create_app
from app.models.answer import Answer
from app.models.interview import Interview
from app.models.interview_question import InterviewQuestion
from app.models.llm_request import LLMRequest
from app.models.question import Question
from app.models.user_topic_knowledge import UserTopicKnowledge
from app.services.llm import (
    BaselineQuestion,
    GeneratedQuestion,
    LLMBaselineGenerationAttempt,
    LLMQuestionAnalysisAttempt,
    LLMQuestionGenerationAttempt,
    LLMScoringAttempt,
    TopicCoverage,
    TopicWeight,
)
from app.services.scoring import ScoringOutcome


@pytest.fixture
def interview_app(tmp_path: Path) -> FastAPI:
    database_path = (tmp_path / "interviews.sqlite3").as_posix()
    settings = Settings(
        app_name="Test API",
        app_env="test",
        app_version="0.0.0-test",
        debug=False,
        database_url=f"sqlite+aiosqlite:///{database_path}",
        jwt_secret_key="test-secret-key-that-is-long-enough",
        interview_questions_count=15,
        interview_seed_questions_count=5,
        cors_origins="http://localhost:3000",
    )
    application = create_app(settings)

    async def create_schema_and_questions() -> None:
        async with application.state.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with application.state.session_factory() as session:
            for index in range(5):
                session.add(
                    Question(
                        role="backend",
                        level="junior",
                        skill=f"Skill {index + 1}",
                        text=f"Question {index + 1}?",
                        ideal_answer=f"Criterion {index + 1}",
                        evaluation_points=[f"criterion {index + 1}"],
                        max_score=10,
                        is_active=True,
                    )
                )
            await session.commit()

    asyncio.run(create_schema_and_questions())
    application.state.llm_scoring_client = AdaptiveLLMStub()
    return application


def auth_headers(client: TestClient, email: str) -> dict[str, str]:
    registration = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "StrongPassword123", "full_name": "Tester"},
    )
    assert registration.status_code == 201
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "StrongPassword123"},
    )
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def create_interview(client: TestClient, headers: dict[str, str]) -> dict[str, object]:
    response = client.post(
        "/api/v1/interviews",
        headers=headers,
        json={"role": "backend", "level": "junior"},
    )
    assert response.status_code == 201
    return response.json()


class LLMScoringStub:
    enabled = True

    def __init__(self, attempt: LLMScoringAttempt) -> None:
        self.attempt = attempt

    async def evaluate(self, _payload: object) -> LLMScoringAttempt:
        return self.attempt

    async def generate_baseline_questions(self, **_payload) -> LLMBaselineGenerationAttempt:
        return baseline_attempt()


class ConcurrentLLMScoringStub(LLMScoringStub):
    def __init__(self, attempt: LLMScoringAttempt) -> None:
        super().__init__(attempt)
        self.barrier = Barrier(2)

    async def evaluate(self, _payload: object) -> LLMScoringAttempt:
        await asyncio.to_thread(self.barrier.wait, 5)
        return self.attempt


class AdaptiveLLMStub:
    enabled = True

    def __init__(self) -> None:
        self.baseline_batches = 0

    async def generate_baseline_questions(self, **_payload) -> LLMBaselineGenerationAttempt:
        self.baseline_batches += 1
        return baseline_attempt(self.baseline_batches)

    async def analyze_question(self, payload) -> LLMQuestionAnalysisAttempt:
        return LLMQuestionAnalysisAttempt(
            topics=(TopicWeight(payload.skill, f"{payload.skill} basics", 1.0),),
            latency_ms=1,
            provider="test_api",
            model="test-model",
            error=None,
        )

    async def evaluate(self, payload) -> LLMScoringAttempt:
        topic = payload.topics[0]
        outcome = ScoringOutcome(
            score=4,
            max_score=10,
            verdict=Verdict.PARTIALLY_CORRECT,
            feedback="Adaptive feedback",
            matched_points=[],
            missing_points=list(payload.evaluation_points),
            provider="test_api",
        )
        return LLMScoringAttempt(
            outcome=outcome,
            latency_ms=1,
            provider="test_api",
            model="test-model",
            error=None,
            topic_coverage=(TopicCoverage(topic.topic, topic.subtopic, 0.4),),
        )

    async def generate_question(self, **payload) -> LLMQuestionGenerationAttempt:
        number = len(payload["previous_questions"]) + 1
        topic = TopicWeight(payload["topic"], payload["subtopic"], 1.0)
        return LLMQuestionGenerationAttempt(
            question=GeneratedQuestion(
                text=f"Adaptive question {number}?",
                ideal_answer="Adaptive ideal answer",
                evaluation_points=("adaptive criterion",),
                topics=(topic,),
            ),
            latency_ms=1,
            provider="test_api",
            model="test-model",
            error=None,
        )


class FailedBaselineLLMStub:
    enabled = True

    async def generate_baseline_questions(self, **_payload) -> LLMBaselineGenerationAttempt:
        return LLMBaselineGenerationAttempt(
            questions=None,
            latency_ms=1,
            provider="test_api",
            model="test-model",
            error="TimeoutError",
        )


class FailedAdaptiveLLMStub(AdaptiveLLMStub):
    async def generate_question(self, **_payload) -> LLMQuestionGenerationAttempt:
        return LLMQuestionGenerationAttempt(
            question=None,
            latency_ms=1,
            provider="test_api",
            model="test-model",
            error="TimeoutError",
        )


class MLRankingStub:
    def __init__(self) -> None:
        self.calls = 0
        self.input_skills: tuple[str, ...] = ()

    async def rank(self, **payload: object) -> tuple[str, ...]:
        self.calls += 1
        items = payload["recommendations"]
        self.input_skills = tuple(item.skill for item in items)
        return tuple(reversed(self.input_skills))


def llm_attempt(outcome: ScoringOutcome | None, error: str | None = None) -> LLMScoringAttempt:
    return LLMScoringAttempt(
        outcome=outcome,
        latency_ms=12,
        provider="ollama",
        model="llama3.1:8b",
        error=error,
    )


def baseline_attempt(batch: int = 1) -> LLMBaselineGenerationAttempt:
    return LLMBaselineGenerationAttempt(
        questions=tuple(
            BaselineQuestion(
                area=f"Skill {number}",
                text=f"Question {batch}-{number}?",
                ideal_answer=f"criterion {batch}-{number}",
                evaluation_points=(f"criterion {batch}-{number}",),
                topics=(
                    TopicWeight(
                        topic=f"Skill {number}",
                        subtopic=f"Skill {number} basics",
                        weight=1.0,
                    ),
                ),
            )
            for number in range(1, 6)
        ),
        latency_ms=1,
        provider="test_api",
        model="test-model",
        error=None,
    )


def test_roles_contract_is_public(interview_app: FastAPI) -> None:
    with TestClient(interview_app) as client:
        response = client.get("/api/v1/roles")

    assert response.status_code == 200
    assert response.json() == [
        {
            "slug": "backend",
            "title": "Backend-разработчик",
            "levels": ["junior", "middle", "senior"],
        },
        {
            "slug": "ml_engineer",
            "title": "ML-инженер",
            "levels": ["junior", "middle", "senior"],
        },
        {
            "slug": "llm_engineer",
            "title": "LLM-инженер",
            "levels": ["junior", "middle", "senior"],
        },
    ]


def test_create_reopen_answer_and_manual_finish(interview_app: FastAPI) -> None:
    with TestClient(interview_app) as client:
        headers = auth_headers(client, "owner@example.com")
        created = create_interview(client, headers)
        interview_id = created["id"]
        first_question = created["current_question"]

        assert created["total_questions"] == 15
        assert created["answered_questions"] == 0
        assert first_question["order_number"] == 1

        reopened = client.get(f"/api/v1/interviews/{interview_id}", headers=headers)
        assert reopened.status_code == 200
        assert reopened.json()["current_question"] == first_question
        assert reopened.json()["answers"] == []

        wrong_question = client.post(
            f"/api/v1/interviews/{interview_id}/answers",
            headers=headers,
            json={
                "interview_question_id": "00000000-0000-0000-0000-000000000001",
                "answer_text": "criterion 1",
            },
        )
        assert wrong_question.status_code == 409

        answer = client.post(
            f"/api/v1/interviews/{interview_id}/answers",
            headers=headers,
            json={
                "interview_question_id": first_question["interview_question_id"],
                "answer_text": first_question["text"]
                .replace("Question", "criterion")
                .replace("?", ""),
            },
        )
        assert answer.status_code == 200
        assert answer.json()["interview_status"] == "in_progress"
        assert isinstance(answer.json()["answer"]["score"], int)
        assert answer.json()["answer"]["verdict"] in {
            "correct",
            "partially_correct",
            "incorrect",
        }
        assert answer.json()["answer"]["feedback"]

        restored = client.get(f"/api/v1/interviews/{interview_id}", headers=headers).json()
        assert restored["answered_questions"] == 1
        assert len(restored["answers"]) == 1
        assert restored["answers"][0]["feedback"]
        assert restored["current_question"] == answer.json()["next_question"]

        repeated = client.post(
            f"/api/v1/interviews/{interview_id}/answers",
            headers=headers,
            json={
                "interview_question_id": first_question["interview_question_id"],
                "answer_text": "criterion 1",
            },
        )
        assert repeated.status_code == 409

        before_finish_result = client.get(
            f"/api/v1/interviews/{interview_id}/result", headers=headers
        )
        assert before_finish_result.status_code == 409

        second_question = restored["current_question"]
        second_answer = client.post(
            f"/api/v1/interviews/{interview_id}/answers",
            headers=headers,
            json={
                "interview_question_id": second_question["interview_question_id"],
                "answer_text": second_question["text"]
                .replace("Question", "criterion")
                .replace("?", ""),
            },
        )
        assert second_answer.status_code == 200
        third_question = second_answer.json()["next_question"]

        finish = client.post(f"/api/v1/interviews/{interview_id}/finish", headers=headers)
        assert finish.status_code == 200
        assert finish.json()["finished_reason"] == "manual"
        assert finish.json()["max_score"] == 150

        result = client.get(f"/api/v1/interviews/{interview_id}/result", headers=headers)
        assert result.status_code == 200
        assert result.json()["interview"]["finished_reason"] == "manual"
        assert len(result.json()["answers"]) == 2

        assert (
            client.post(f"/api/v1/interviews/{interview_id}/finish", headers=headers).status_code
            == 409
        )
        assert (
            client.post(
                f"/api/v1/interviews/{interview_id}/answers",
                headers=headers,
                json={
                    "interview_question_id": third_question["interview_question_id"],
                    "answer_text": "criterion 3",
                },
            ).status_code
            == 409
        )


def test_repeat_generates_five_new_baseline_questions(interview_app: FastAPI) -> None:
    with TestClient(interview_app) as client:
        headers = auth_headers(client, "repeat@example.com")
        first = create_interview(client, headers)
        finish = client.post(f"/api/v1/interviews/{first['id']}/finish", headers=headers)
        assert finish.status_code == 200
        second = create_interview(client, headers)

    async def assert_new_questions() -> None:
        interview_ids = (UUID(first["id"]), UUID(second["id"]))
        async with interview_app.state.session_factory() as session:
            rows = (
                await session.execute(
                    select(Interview.id, Question.text, Question.skill, Question.source)
                    .join(InterviewQuestion, InterviewQuestion.interview_id == Interview.id)
                    .join(Question, Question.id == InterviewQuestion.question_id)
                    .where(Interview.id.in_(interview_ids))
                )
            ).all()
            by_interview = {
                interview_id: [row for row in rows if row.id == interview_id]
                for interview_id in interview_ids
            }
            for questions in by_interview.values():
                assert len(questions) == 5
                assert len({question.skill for question in questions}) == 5
                assert {question.source for question in questions} == {"generated_base"}
            assert {row.text for row in by_interview[interview_ids[0]]}.isdisjoint(
                {row.text for row in by_interview[interview_ids[1]]}
            )

    asyncio.run(assert_new_questions())


def test_interview_creation_requires_generated_baseline(interview_app: FastAPI) -> None:
    interview_app.state.llm_scoring_client = FailedBaselineLLMStub()
    with TestClient(interview_app) as client:
        headers = auth_headers(client, "generation-failed@example.com")
        response = client.post(
            "/api/v1/interviews",
            headers=headers,
            json={"role": "backend", "level": "junior"},
        )

    assert response.status_code == 503
    assert response.json() == {"detail": "LLM could not generate baseline questions"}


def test_adaptive_generation_failure_does_not_use_saved_question(
    interview_app: FastAPI,
) -> None:
    interview_app.state.llm_scoring_client = FailedAdaptiveLLMStub()
    with TestClient(interview_app) as client:
        headers = auth_headers(client, "adaptive-generation-failed@example.com")
        created = create_interview(client, headers)
        current = created["current_question"]
        for _ in range(4):
            response = client.post(
                f"/api/v1/interviews/{created['id']}/answers",
                headers=headers,
                json={
                    "interview_question_id": current["interview_question_id"],
                    "answer_text": "substantive baseline answer",
                },
            )
            assert response.status_code == 200
            current = response.json()["next_question"]

        failed = client.post(
            f"/api/v1/interviews/{created['id']}/answers",
            headers=headers,
            json={
                "interview_question_id": current["interview_question_id"],
                "answer_text": "substantive fifth answer",
            },
        )
        detail = client.get(f"/api/v1/interviews/{created['id']}", headers=headers).json()

    assert failed.status_code == 503
    assert detail["answered_questions"] == 4
    assert detail["current_question"]["order_number"] == 5


def test_fifteenth_answer_finishes_interview_automatically(interview_app: FastAPI) -> None:
    with TestClient(interview_app) as client:
        headers = auth_headers(client, "complete@example.com")
        created = create_interview(client, headers)
        interview_id = created["id"]
        current = created["current_question"]

        for number in range(1, 16):
            response = client.post(
                f"/api/v1/interviews/{interview_id}/answers",
                headers=headers,
                json={
                    "interview_question_id": current["interview_question_id"],
                    "answer_text": f"criterion {current['text'].split()[1].rstrip('?')}",
                },
            )
            assert response.status_code == 200
            if number < 15:
                assert response.json()["interview_status"] == "in_progress"
                current = response.json()["next_question"]
            else:
                assert response.json()["interview_status"] == "finished"
                assert response.json()["next_question"] is None
                assert response.json()["result_url"]

        result = client.get(f"/api/v1/interviews/{interview_id}/result", headers=headers)
        assert result.status_code == 200
        assert result.json()["interview"]["finished_reason"] == "completed"
    assert len(result.json()["answers"]) == 15


def test_five_baseline_answers_build_graph_and_generate_adaptive_question(
    interview_app: FastAPI,
) -> None:
    interview_app.state.llm_scoring_client = AdaptiveLLMStub()
    with TestClient(interview_app) as client:
        headers = auth_headers(client, "adaptive@example.com")
        created = create_interview(client, headers)
        assert created["total_questions"] == 15
        current = created["current_question"]

        for _ in range(5):
            response = client.post(
                f"/api/v1/interviews/{created['id']}/answers",
                headers=headers,
                json={
                    "interview_question_id": current["interview_question_id"],
                    "answer_text": "substantive adaptive answer",
                },
            )
            assert response.status_code == 200
            current = response.json()["next_question"]

        detail = client.get(f"/api/v1/interviews/{created['id']}", headers=headers).json()

    assert current["text"] == "Adaptive question 6?"
    assert len(detail["knowledge_graph"]) == 5

    async def assert_adaptive_storage() -> None:
        async with interview_app.state.session_factory() as session:
            generated = (
                (
                    await session.execute(
                        select(Question).where(Question.source == "generated_adaptive")
                    )
                )
                .scalars()
                .one()
            )
            knowledge = (await session.execute(select(UserTopicKnowledge))).scalars().all()
            assert generated.target_subtopic
            assert generated.topic_weights[0]["weight"] == 1.0
            assert len(knowledge) == 5
            assert all(node.score == 40 for node in knowledge)

    asyncio.run(assert_adaptive_storage())


def test_ml_ranking_reorders_rule_based_recommendations(interview_app: FastAPI) -> None:
    ml_stub = MLRankingStub()
    interview_app.state.ml_recommendation_client = ml_stub

    with TestClient(interview_app) as client:
        headers = auth_headers(client, "ml-ranking@example.com")
        created = create_interview(client, headers)
        current = created["current_question"]
        while current is not None:
            response = client.post(
                f"/api/v1/interviews/{created['id']}/answers",
                headers=headers,
                json={
                    "interview_question_id": current["interview_question_id"],
                    "answer_text": "substantive but unrelated answer",
                },
            )
            assert response.status_code == 200
            current = response.json()["next_question"]

        result = client.get(f"/api/v1/interviews/{created['id']}/result", headers=headers)

    assert result.status_code == 200
    assert ml_stub.calls == 1
    assert [item["skill"] for item in result.json()["recommendations"]] == list(
        reversed(ml_stub.input_skills)
    )


def test_llm_score_and_request_metadata_are_saved(interview_app: FastAPI) -> None:
    interview_app.state.llm_scoring_client = LLMScoringStub(
        llm_attempt(
            ScoringOutcome(
                score=9,
                max_score=10,
                verdict=Verdict.CORRECT,
                feedback="LLM feedback",
                matched_points=["criterion 1"],
                missing_points=[],
                provider="ollama",
            )
        )
    )
    with TestClient(interview_app) as client:
        headers = auth_headers(client, "llm@example.com")
        created = create_interview(client, headers)
        response = client.post(
            f"/api/v1/interviews/{created['id']}/answers",
            headers=headers,
            json={
                "interview_question_id": created["current_question"]["interview_question_id"],
                "answer_text": created["current_question"]["text"]
                .replace("Question", "criterion")
                .replace("?", ""),
            },
        )

    assert response.status_code == 200
    assert response.json()["answer"]["scoring_provider"] == "ollama"

    async def assert_metadata() -> None:
        async with interview_app.state.session_factory() as session:
            answer = (await session.execute(select(Answer))).scalars().one()
            request = (
                (
                    await session.execute(
                        select(LLMRequest).where(LLMRequest.prompt_type == "evaluate_answer")
                    )
                )
                .scalars()
                .one()
            )
            assert answer.llm_score == 9
            assert answer.keyword_score == 10
            assert request.success is True
            assert request.error_message is None

    asyncio.run(assert_metadata())


def test_llm_error_uses_fallback_and_logs_failure(interview_app: FastAPI) -> None:
    interview_app.state.llm_scoring_client = LLMScoringStub(llm_attempt(None, error="TimeoutError"))
    with TestClient(interview_app) as client:
        headers = auth_headers(client, "fallback@example.com")
        created = create_interview(client, headers)
        response = client.post(
            f"/api/v1/interviews/{created['id']}/answers",
            headers=headers,
            json={
                "interview_question_id": created["current_question"]["interview_question_id"],
                "answer_text": created["current_question"]["text"]
                .replace("Question", "criterion")
                .replace("?", ""),
            },
        )

    assert response.status_code == 200
    assert response.json()["answer"]["scoring_provider"] == "rule_based_fallback"

    async def assert_metadata() -> None:
        async with interview_app.state.session_factory() as session:
            answer = (await session.execute(select(Answer))).scalars().one()
            request = (
                (
                    await session.execute(
                        select(LLMRequest).where(LLMRequest.prompt_type == "evaluate_answer")
                    )
                )
                .scalars()
                .one()
            )
            assert answer.llm_score is None
            assert answer.keyword_score == answer.score
            assert request.success is False
            assert request.error_message == "TimeoutError"

    asyncio.run(assert_metadata())


def test_concurrent_answer_submission_accepts_only_one(interview_app: FastAPI) -> None:
    interview_app.state.llm_scoring_client = ConcurrentLLMScoringStub(
        llm_attempt(None, error="TimeoutError")
    )
    with TestClient(interview_app) as client:
        headers = auth_headers(client, "concurrent@example.com")
        created = create_interview(client, headers)
        payload = {
            "interview_question_id": created["current_question"]["interview_question_id"],
            "answer_text": "substantive concurrent answer",
        }

        with ThreadPoolExecutor(max_workers=2) as executor:
            responses = list(
                executor.map(
                    lambda _: client.post(
                        f"/api/v1/interviews/{created['id']}/answers",
                        headers=headers,
                        json=payload,
                    ),
                    range(2),
                )
            )

        detail = client.get(f"/api/v1/interviews/{created['id']}", headers=headers)

    assert sorted(response.status_code for response in responses) == [200, 409]
    assert detail.json()["answered_questions"] == 1


def test_interview_ownership_is_hidden_with_not_found(interview_app: FastAPI) -> None:
    with TestClient(interview_app) as client:
        owner_headers = auth_headers(client, "owner@example.com")
        other_headers = auth_headers(client, "other@example.com")
        created = create_interview(client, owner_headers)
        interview_id = created["id"]

        assert (
            client.get(f"/api/v1/interviews/{interview_id}", headers=other_headers).status_code
            == 404
        )
        assert (
            client.post(
                f"/api/v1/interviews/{interview_id}/answers",
                headers=other_headers,
                json={
                    "interview_question_id": created["current_question"]["interview_question_id"],
                    "answer_text": "criterion 1",
                },
            ).status_code
            == 404
        )
        assert (
            client.post(
                f"/api/v1/interviews/{interview_id}/finish", headers=other_headers
            ).status_code
            == 404
        )
        assert (
            client.get(
                f"/api/v1/interviews/{interview_id}/result", headers=other_headers
            ).status_code
            == 404
        )


def test_blank_answer_returns_422(interview_app: FastAPI) -> None:
    with TestClient(interview_app) as client:
        headers = auth_headers(client, "validation@example.com")
        created = create_interview(client, headers)
        blank = client.post(
            f"/api/v1/interviews/{created['id']}/answers",
            headers=headers,
            json={
                "interview_question_id": created["current_question"]["interview_question_id"],
                "answer_text": "   ",
            },
        )
        assert blank.status_code == 422

        punctuation_only = client.post(
            f"/api/v1/interviews/{created['id']}/answers",
            headers=headers,
            json={
                "interview_question_id": created["current_question"]["interview_question_id"],
                "answer_text": "!!! ... —",
            },
        )
        assert punctuation_only.status_code == 422
        assert punctuation_only.json() == {"detail": "Answer must contain meaningful text"}

        finish = client.post(f"/api/v1/interviews/{created['id']}/finish", headers=headers)
        assert finish.status_code == 200
        assert finish.json()["finished_reason"] == "manual"
        assert finish.json()["total_score"] == 0
        assert finish.json()["max_score"] == 150
        assert finish.json()["percentage"] == 0

        result = client.get(f"/api/v1/interviews/{created['id']}/result", headers=headers)
        assert result.status_code == 200
        assert result.json()["answers"] == []
