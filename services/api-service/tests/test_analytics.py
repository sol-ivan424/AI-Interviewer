import asyncio
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.models  # noqa: F401
from app.core.config import Settings
from app.db.base import Base
from app.main import create_app
from app.models.question import Question
from app.services.llm import (
    BaselineQuestion,
    LLMBaselineGenerationAttempt,
    LLMScoringAttempt,
    TopicWeight,
)


class AnalyticsLLMStub:
    enabled = True

    async def generate_baseline_questions(self, **payload) -> LLMBaselineGenerationAttempt:
        role = payload["role"]
        skill = "SQL" if role == "backend" else "MLOps"
        return LLMBaselineGenerationAttempt(
            questions=tuple(
                BaselineQuestion(
                    area=f"{skill} {number}",
                    text=f"{role} question {number}?",
                    ideal_answer=f"{role} criterion {number}",
                    evaluation_points=(f"{role} criterion {number}",),
                    topics=(TopicWeight(f"{skill} {number}", f"Basics {number}", 1.0),),
                )
                for number in range(1, 6)
            ),
            latency_ms=1,
            provider="test_api",
            model="test-model",
            error=None,
        )

    async def evaluate(self, _payload) -> LLMScoringAttempt:
        return LLMScoringAttempt(
            outcome=None,
            latency_ms=1,
            provider="test_api",
            model="test-model",
            error="disabled for analytics test",
        )


@pytest.fixture
def analytics_app(tmp_path: Path) -> FastAPI:
    database_path = (tmp_path / "analytics.sqlite3").as_posix()
    settings = Settings(
        app_name="Test API",
        app_env="test",
        app_version="0.0.0-test",
        debug=False,
        database_url=f"sqlite+aiosqlite:///{database_path}",
        jwt_secret_key="test-secret-key-that-is-long-enough",
        interview_questions_count=5,
        cors_origins="http://localhost:3000",
    )
    application = create_app(settings)

    async def create_schema_and_questions() -> None:
        async with application.state.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with application.state.session_factory() as session:
            for role, skill in (("backend", "SQL"), ("ml_engineer", "MLOps")):
                for index in range(1, 6):
                    session.add(
                        Question(
                            role=role,
                            level="junior",
                            skill=skill,
                            text=f"{role} question {index}?",
                            ideal_answer=f"{role} criterion {index}",
                            evaluation_points=[f"{role} criterion {index}"],
                            max_score=10,
                            is_active=True,
                        )
                    )
            await session.commit()

    asyncio.run(create_schema_and_questions())
    application.state.llm_scoring_client = AnalyticsLLMStub()
    return application


def auth_headers(client: TestClient, email: str) -> dict[str, str]:
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "StrongPassword123", "full_name": "Analytics"},
    )
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "StrongPassword123"},
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def create_interview(client: TestClient, headers: dict[str, str], role: str) -> dict[str, object]:
    response = client.post(
        "/api/v1/interviews",
        headers=headers,
        json={"role": role, "level": "junior"},
    )
    assert response.status_code == 201
    return response.json()


def complete_with_full_answers(
    client: TestClient, headers: dict[str, str], created: dict[str, object]
) -> None:
    current = created["current_question"]
    while current is not None:
        question_number = current["text"].removesuffix("?").split()[-1]
        role = current["text"].split()[0]
        response = client.post(
            f"/api/v1/interviews/{created['id']}/answers",
            headers=headers,
            json={
                "interview_question_id": current["interview_question_id"],
                "answer_text": f"{role} criterion {question_number}",
            },
        )
        assert response.status_code == 200
        current = response.json()["next_question"]


def test_analytics_empty_state(analytics_app: FastAPI) -> None:
    with TestClient(analytics_app) as client:
        headers = auth_headers(client, "empty@example.com")

        summary = client.get("/api/v1/analytics/summary", headers=headers)
        skills = client.get("/api/v1/analytics/skills", headers=headers)
        progress = client.get("/api/v1/analytics/progress", headers=headers)

    assert summary.status_code == 200
    assert summary.json() == {
        "total_interviews": 0,
        "finished_interviews": 0,
        "average_percentage": None,
        "best_role": None,
        "strongest_skill": None,
        "weakest_skills": [],
    }
    assert skills.json() == []
    assert progress.json() == []


def test_result_recommendations_and_filled_analytics(analytics_app: FastAPI) -> None:
    with TestClient(analytics_app) as client:
        headers = auth_headers(client, "filled@example.com")

        backend = create_interview(client, headers, "backend")
        complete_with_full_answers(client, headers, backend)

        ml = create_interview(client, headers, "ml_engineer")
        current = ml["current_question"]
        weak_answer = client.post(
            f"/api/v1/interviews/{ml['id']}/answers",
            headers=headers,
            json={
                "interview_question_id": current["interview_question_id"],
                "answer_text": "irrelevant but substantive answer",
            },
        )
        assert weak_answer.status_code == 200
        assert (
            client.post(f"/api/v1/interviews/{ml['id']}/finish", headers=headers).status_code == 200
        )

        in_progress = create_interview(client, headers, "backend")

        backend_result = client.get(
            f"/api/v1/interviews/{backend['id']}/result", headers=headers
        ).json()
        ml_result = client.get(f"/api/v1/interviews/{ml['id']}/result", headers=headers).json()
        summary = client.get("/api/v1/analytics/summary", headers=headers).json()
        skills = client.get("/api/v1/analytics/skills", headers=headers).json()
        progress = client.get("/api/v1/analytics/progress", headers=headers).json()

        other_headers = auth_headers(client, "other@example.com")
        other_summary = client.get("/api/v1/analytics/summary", headers=other_headers).json()

    assert backend_result["skill_scores"] == [
        {
            "skill": f"SQL {number}",
            "score": 10,
            "max_score": 10,
            "percentage": 100,
            "status": "good",
        }
        for number in range(1, 6)
    ]
    assert backend_result["recommendations"] == []

    assert ml_result["skill_scores"] == [
        {
            "skill": f"MLOps {number}",
            "score": 0,
            "max_score": 10,
            "percentage": 0,
            "status": "weak",
        }
        for number in range(1, 6)
    ]
    assert len(ml_result["recommendations"]) == 1
    assert ml_result["recommendations"][0]["priority"] == "high"
    assert ml_result["recommendations"][0]["topics_to_learn"]

    assert summary == {
        "total_interviews": 3,
        "finished_interviews": 2,
        "average_percentage": 50,
        "best_role": "backend",
        "strongest_skill": "SQL 1",
        "weakest_skills": ["MLOps 1"],
    }
    assert skills == [
        {"skill": "MLOps 1", "average_percentage": 0, "answers_count": 1},
        *[
            {
                "skill": f"SQL {number}",
                "average_percentage": 100,
                "answers_count": 1,
            }
            for number in range(1, 6)
        ],
    ]
    assert [item["interview_id"] for item in progress] == [backend["id"], ml["id"]]
    assert all(item["interview_id"] != in_progress["id"] for item in progress)
    assert [item["finished_at"] for item in progress] == sorted(
        item["finished_at"] for item in progress
    )
    assert other_summary["total_interviews"] == 0
    assert other_summary["finished_interviews"] == 0
