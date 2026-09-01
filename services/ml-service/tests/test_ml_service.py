from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from training.generate_synthetic import generate
from training.train import train


def test_training_and_inference(tmp_path: Path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    artifact_dir = tmp_path / "artifacts"
    generate(data_dir)
    metrics = train(data_dir, artifact_dir)
    assert metrics["topic_classifier"]["accuracy"] >= 0.8
    assert metrics["level_predictor"]["macro_f1"] >= 0.8
    monkeypatch.setenv("ML_ARTIFACT_DIR", str(artifact_dir))

    with TestClient(app) as client:
        health = client.get("/health")
        assert health.status_code == 200
        assert health.json()["model_version"] == "1.0.0"

        level = client.post(
            "/ml/predict-level",
            json={
                "average_score": 84,
                "backend_score": 81,
                "ml_score": 86,
                "llm_score": 83,
                "answers_count": 50,
                "correct_answers_count": 37,
                "partial_answers_count": 10,
                "wrong_answers_count": 3,
                "weak_skills_count": 1,
                "average_answer_length": 520,
            },
        )
        assert level.status_code == 200
        assert level.json()["prediction"] == "senior"
        assert sum(level.json()["probabilities"].values()) == 1

        topic = client.post(
            "/ml/classify-weak-topic",
            json={
                "answers": [
                    {
                        "answer_text": "A query reads rows from a database.",
                        "missing_points": ["indexes and query plans"],
                        "score": 2,
                        "max_score": 10,
                    }
                ]
            },
        )
        assert topic.status_code == 200
        assert topic.json()["prediction"] == "SQL"

        ranking = client.post(
            "/ml/recommendations/rank",
            json={
                "recommendations": [
                    {
                        "skill": "Unknown skill",
                        "priority": "high",
                        "current_percentage": 20,
                        "topics_count": 1,
                    },
                    {
                        "skill": "SQL",
                        "priority": "high",
                        "current_percentage": 20,
                        "topics_count": 1,
                    },
                ]
            },
        )
        assert ranking.json() == {
            "prediction": ["SQL", "Unknown skill"],
            "model_version": "1.0.0",
        }


def test_request_validation() -> None:
    # Lifespan is intentionally skipped: validation happens before model access.
    response = TestClient(app).post(
        "/ml/predict-level",
        json={
            "average_score": 50,
            "backend_score": 50,
            "ml_score": 50,
            "llm_score": 50,
            "answers_count": 1,
            "correct_answers_count": 1,
            "partial_answers_count": 1,
            "wrong_answers_count": 0,
            "weak_skills_count": 0,
            "average_answer_length": 100,
        },
    )
    assert response.status_code == 422


def test_knowledge_update_and_stable_target_selection() -> None:
    response = TestClient(app).post(
        "/ml/knowledge/update",
        json={
            "nodes": [
                {
                    "topic": "SQL",
                    "subtopic": "joins",
                    "score": 40,
                    "confidence": 0.25,
                    "evidence_count": 1,
                    "evidence_weight": 0.5,
                }
            ],
            "observations": [
                {"topic": "SQL", "subtopic": "joins", "question_weight": 0.5, "coverage": 0.8},
                {"topic": "SQL", "subtopic": "indexes", "question_weight": 0.25, "coverage": 0.2},
                {"topic": "API", "subtopic": "auth", "question_weight": 0.25, "coverage": 0.2},
            ],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["nodes"] == [
        {
            "topic": "SQL",
            "subtopic": "joins",
            "score": 60.0,
            "confidence": 0.5,
            "evidence_count": 2,
            "evidence_weight": 1.0,
        },
        {
            "topic": "SQL",
            "subtopic": "indexes",
            "score": 20.0,
            "confidence": 0.125,
            "evidence_count": 1,
            "evidence_weight": 0.25,
        },
        {
            "topic": "API",
            "subtopic": "auth",
            "score": 20.0,
            "confidence": 0.125,
            "evidence_count": 1,
            "evidence_weight": 0.25,
        },
    ]
    assert body["next_target"] == {"topic": "API", "subtopic": "auth"}
