import asyncio
import json
from collections import Counter
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from urllib.request import Request, urlopen

from pydantic import BaseModel, Field


class _RankingResponse(BaseModel):
    prediction: list[str] = Field(min_length=1)


class MLKnowledgeNode(BaseModel):
    topic: str = Field(min_length=1)
    subtopic: str = Field(min_length=1)
    score: float = Field(ge=0, le=100)
    confidence: float = Field(ge=0, le=1)
    evidence_count: int = Field(ge=0)
    evidence_weight: float = Field(ge=0)


class MLKnowledgeObservation(BaseModel):
    topic: str = Field(min_length=1)
    subtopic: str = Field(min_length=1)
    question_weight: float = Field(gt=0, le=1)
    coverage: float = Field(ge=0, le=1)


class _KnowledgeTarget(BaseModel):
    topic: str = Field(min_length=1)
    subtopic: str = Field(min_length=1)


class _KnowledgeResponse(BaseModel):
    nodes: list[MLKnowledgeNode] = Field(min_length=1)
    next_target: _KnowledgeTarget


@dataclass(frozen=True, slots=True)
class MLRecommendationInput:
    skill: str
    priority: str
    current_percentage: int
    topics_count: int


def _post_json(url: str, payload: dict[str, object], timeout: float) -> object:
    request = Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=timeout) as response:
        return json.load(response)


class MLRecommendationClient:
    def __init__(self, base_url: str, timeout_seconds: float) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout_seconds

    @property
    def enabled(self) -> bool:
        return bool(self.base_url)

    async def rank(
        self,
        *,
        recommendations: Sequence[MLRecommendationInput],
    ) -> tuple[str, ...] | None:
        if not self.enabled or not recommendations:
            return None

        try:
            body = await asyncio.to_thread(
                _post_json,
                f"{self.base_url}/ml/recommendations/rank",
                {
                    "recommendations": [asdict(item) for item in recommendations],
                },
                self.timeout,
            )
            prediction = _RankingResponse.model_validate(body).prediction
            skills = [item.skill for item in recommendations]
            if Counter(prediction) != Counter(skills):
                raise ValueError("ML ranking is not a permutation of recommendation skills")
            return tuple(prediction)
        except Exception:
            return None

    async def update_knowledge(
        self,
        *,
        nodes: Sequence[MLKnowledgeNode],
        observations: Sequence[MLKnowledgeObservation],
    ) -> tuple[tuple[MLKnowledgeNode, ...], tuple[str, str]] | None:
        if not self.enabled or not observations:
            return None
        try:
            body = await asyncio.to_thread(
                _post_json,
                f"{self.base_url}/ml/knowledge/update",
                {
                    "nodes": [item.model_dump() for item in nodes],
                    "observations": [item.model_dump() for item in observations],
                },
                self.timeout,
            )
            result = _KnowledgeResponse.model_validate(body)
            keys = [(item.topic.casefold(), item.subtopic.casefold()) for item in result.nodes]
            target_key = (
                result.next_target.topic.casefold(),
                result.next_target.subtopic.casefold(),
            )
            if len(keys) != len(set(keys)) or target_key not in keys:
                raise ValueError("ML knowledge response is inconsistent")
            return tuple(result.nodes), (
                result.next_target.topic,
                result.next_target.subtopic,
            )
        except Exception:
            return None
