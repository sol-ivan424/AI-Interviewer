import json
from pathlib import Path

import joblib

from app.schemas import (
    KnowledgeNode,
    KnowledgeObservation,
    KnowledgeTarget,
    KnowledgeUpdateResponse,
    LevelPredictionRequest,
    RecommendationRankItem,
    WeaknessEvidence,
)


def build_topic_text(answers: list[WeaknessEvidence]) -> str:
    parts: list[str] = []
    for answer in answers:
        ratio = answer.score / answer.max_score
        score_bucket = (
            "score_low" if ratio < 0.4 else "score_medium" if ratio < 0.7 else "score_high"
        )
        parts.extend((answer.answer_text, *answer.missing_points, score_bucket))
    return " ".join(part.strip() for part in parts if part.strip())


def update_knowledge(
    nodes: list[KnowledgeNode], observations: list[KnowledgeObservation]
) -> KnowledgeUpdateResponse:
    # ponytail: deterministic weighted baseline; replace with a trained/calibrated selector
    # once production labels exist.
    updated = {node_key(node): node.model_copy() for node in nodes}
    for observation in observations:
        key = node_key(observation)
        node = updated.get(key)
        if node is None:
            node = KnowledgeNode(
                topic=observation.topic,
                subtopic=observation.subtopic,
                score=0,
                confidence=0,
                evidence_count=0,
                evidence_weight=0,
            )
            updated[key] = node
        total_weight = node.evidence_weight + observation.question_weight
        node.score = round(
            (
                node.score * node.evidence_weight
                + observation.coverage * 100 * observation.question_weight
            )
            / total_weight,
            6,
        )
        node.evidence_count += 1
        node.evidence_weight = round(total_weight, 6)

    result = list(updated.values())
    for node in result:
        node.confidence = round(min(1, node.evidence_weight / 2), 6)
    target = min(
        result,
        key=lambda node: (
            node.score / 100 + node.confidence,
            node.topic.casefold(),
            node.subtopic.casefold(),
            node.topic,
            node.subtopic,
        ),
    )
    return KnowledgeUpdateResponse(
        nodes=result,
        next_target=KnowledgeTarget(topic=target.topic, subtopic=target.subtopic),
    )


def node_key(node: KnowledgeNode | KnowledgeObservation) -> tuple[str, str]:
    return node.topic.casefold(), node.subtopic.casefold()


class ModelService:
    def __init__(
        self,
        *,
        topic_classifier: object,
        level_predictor: object,
        model_version: str,
        level_features: list[str],
    ) -> None:
        self.topic_classifier = topic_classifier
        self.level_predictor = level_predictor
        self.model_version = model_version
        self.level_features = level_features

    @classmethod
    def load(cls, artifact_dir: Path) -> "ModelService":
        manifest = json.loads((artifact_dir / "manifest.json").read_text(encoding="utf-8"))
        return cls(
            topic_classifier=joblib.load(artifact_dir / "topic_classifier.joblib"),
            level_predictor=joblib.load(artifact_dir / "level_predictor.joblib"),
            model_version=manifest["model_version"],
            level_features=manifest["level_features"],
        )

    def predict_level(self, request: LevelPredictionRequest) -> tuple[str, dict[str, float]]:
        values = request.model_dump()
        row = [[values[name] for name in self.level_features]]
        probabilities = self.level_predictor.predict_proba(row)[0]
        classes = self.level_predictor.classes_
        result = {
            str(label): round(float(value), 6)
            for label, value in zip(classes, probabilities, strict=True)
        }
        return max(result, key=result.get), result

    def classify_weak_topic(self, answers: list[WeaknessEvidence]) -> tuple[str, dict[str, float]]:
        probabilities = self.topic_classifier.predict_proba([build_topic_text(answers)])[0]
        classes = self.topic_classifier.classes_
        result = {
            str(label): round(float(value), 6)
            for label, value in zip(classes, probabilities, strict=True)
        }
        return max(result, key=result.get), result

    def rank_recommendations(self, recommendations: list[RecommendationRankItem]) -> list[str]:
        classes = [str(label) for label in self.topic_classifier.classes_]

        def rank_score(item: RecommendationRankItem) -> float:
            probabilities = self.topic_classifier.predict_proba([item.skill])[0]
            matching_probability = next(
                (
                    float(probability)
                    for label, probability in zip(classes, probabilities, strict=True)
                    if label.casefold() == item.skill.casefold()
                ),
                0.0,
            )
            return (
                (0.2 if item.priority == "high" else 0.1)
                + (100 - item.current_percentage) / 100 * 0.6
                + min(item.topics_count, 5) / 5 * 0.05
                + matching_probability * 0.15
            )

        indexed = enumerate(recommendations)
        ranked = sorted(
            indexed,
            key=lambda pair: (
                -rank_score(pair[1]),
                pair[0],
            ),
        )
        return [item.skill for _, item in ranked]
