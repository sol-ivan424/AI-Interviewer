import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request

from app.model_service import ModelService, update_knowledge
from app.schemas import (
    HealthResponse,
    KnowledgeUpdateRequest,
    KnowledgeUpdateResponse,
    LevelPredictionRequest,
    PredictionResponse,
    RankingResponse,
    RecommendationRankRequest,
    WeakTopicRequest,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    artifact_dir = Path(os.getenv("ML_ARTIFACT_DIR", "/app/artifacts"))
    app.state.model_service = ModelService.load(artifact_dir)
    yield


app = FastAPI(title="AI Interviewer ML Service", version="1.0.0", lifespan=lifespan)


def get_model_service(request: Request) -> ModelService:
    return request.app.state.model_service


@app.post("/ml/knowledge/update", response_model=KnowledgeUpdateResponse)
async def update_knowledge_state(payload: KnowledgeUpdateRequest) -> KnowledgeUpdateResponse:
    return update_knowledge(payload.nodes, payload.observations)


@app.get("/health", response_model=HealthResponse)
async def health(request: Request) -> HealthResponse:
    service = get_model_service(request)
    return HealthResponse(
        status="ok",
        model_version=service.model_version,
        topic_classifier_loaded=service.topic_classifier is not None,
        level_predictor_loaded=service.level_predictor is not None,
    )


@app.post("/ml/predict-level", response_model=PredictionResponse)
async def predict_level(payload: LevelPredictionRequest, request: Request) -> PredictionResponse:
    service = get_model_service(request)
    prediction, probabilities = service.predict_level(payload)
    return PredictionResponse(
        prediction=prediction,
        confidence=max(probabilities.values()),
        probabilities=probabilities,
        model_version=service.model_version,
    )


@app.post("/ml/classify-weak-topic", response_model=PredictionResponse)
async def classify_weak_topic(payload: WeakTopicRequest, request: Request) -> PredictionResponse:
    service = get_model_service(request)
    prediction, probabilities = service.classify_weak_topic(payload.answers)
    return PredictionResponse(
        prediction=prediction,
        confidence=max(probabilities.values()),
        probabilities=probabilities,
        model_version=service.model_version,
    )


@app.post("/ml/recommendations/rank", response_model=RankingResponse)
async def rank_recommendations(
    payload: RecommendationRankRequest, request: Request
) -> RankingResponse:
    service = get_model_service(request)
    return RankingResponse(
        prediction=service.rank_recommendations(payload.recommendations),
        model_version=service.model_version,
    )
