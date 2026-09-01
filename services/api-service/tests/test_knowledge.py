import pytest

from app.services.knowledge import (
    KnowledgeEvidence,
    KnowledgeState,
    select_next_subtopic,
    update_knowledge,
)


def test_weighted_update_and_weakest_subtopic_selection() -> None:
    updated = update_knowledge(
        [
            KnowledgeState("SQL", "Joins", 80, 0.5, 1, 1.0),
            KnowledgeState("Python", "Async IO", 70, 0.25, 1, 0.5),
        ],
        [
            KnowledgeEvidence("sql", "joins", 0.2, 0.5),
            KnowledgeEvidence("Docker", "Layers", 0.4, 0.25),
        ],
    )

    sql = next(state for state in updated if state.topic == "SQL")
    assert sql.score == pytest.approx(60)
    assert sql.confidence == pytest.approx(0.75)
    assert sql.evidence_count == 2
    assert sql.evidence_weight == pytest.approx(1.5)

    selected = select_next_subtopic(updated)
    assert selected is not None
    assert (selected.topic, selected.subtopic) == ("Docker", "Layers")
    assert selected.confidence == pytest.approx(0.125)
