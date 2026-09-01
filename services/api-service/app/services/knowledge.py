from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class KnowledgeState:
    topic: str
    subtopic: str
    score: float
    confidence: float
    evidence_count: int
    evidence_weight: float


@dataclass(frozen=True, slots=True)
class KnowledgeEvidence:
    topic: str
    subtopic: str
    coverage: float
    weight: float


def update_knowledge(
    current: Iterable[KnowledgeState], evidence: Iterable[KnowledgeEvidence]
) -> list[KnowledgeState]:
    # ponytail: deterministic fallback; replace with a calibrated model after labels exist.
    states: dict[tuple[str, str], KnowledgeState] = {}
    for state in current:
        _validate_state(state)
        key = _key(state.topic, state.subtopic)
        if key in states:
            raise ValueError("knowledge state contains a duplicate topic and subtopic")
        states[key] = state

    for item in evidence:
        _validate_evidence(item)
        key = _key(item.topic, item.subtopic)
        previous = states.get(key)
        previous_weight = previous.evidence_weight if previous else 0.0
        total_weight = previous_weight + item.weight
        score = round(
            (
                ((previous.score * previous_weight) if previous else 0.0)
                + item.coverage * 100 * item.weight
            )
            / total_weight,
            6,
        )
        states[key] = KnowledgeState(
            topic=previous.topic if previous else item.topic.strip(),
            subtopic=previous.subtopic if previous else item.subtopic.strip(),
            score=score,
            confidence=round(min(1.0, total_weight / 2), 6),
            evidence_count=(previous.evidence_count if previous else 0) + 1,
            evidence_weight=round(total_weight, 6),
        )

    return sorted(states.values(), key=lambda state: _key(state.topic, state.subtopic))


def select_next_subtopic(states: Iterable[KnowledgeState]) -> KnowledgeState | None:
    validated: list[KnowledgeState] = []
    for state in states:
        _validate_state(state)
        validated.append(state)
    return min(
        validated,
        key=lambda state: (
            state.score / 100 + state.confidence,
            *_key(state.topic, state.subtopic),
        ),
        default=None,
    )


def _key(topic: str, subtopic: str) -> tuple[str, str]:
    cleaned_topic = topic.strip()
    cleaned_subtopic = subtopic.strip()
    if not cleaned_topic or not cleaned_subtopic:
        raise ValueError("topic and subtopic must not be empty")
    return cleaned_topic.casefold(), cleaned_subtopic.casefold()


def _validate_state(state: KnowledgeState) -> None:
    _key(state.topic, state.subtopic)
    if not 0 <= state.score <= 100 or not 0 <= state.confidence <= 1:
        raise ValueError("score must be between 0 and 100 and confidence between 0 and 1")
    if state.evidence_count < 0 or state.evidence_weight < 0:
        raise ValueError("evidence values must not be negative")


def _validate_evidence(evidence: KnowledgeEvidence) -> None:
    _key(evidence.topic, evidence.subtopic)
    if not 0 <= evidence.coverage <= 1:
        raise ValueError("evidence coverage must be between 0 and 1")
    if evidence.weight <= 0:
        raise ValueError("evidence weight must be positive")
