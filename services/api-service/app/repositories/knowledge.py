from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_topic_knowledge import UserTopicKnowledge
from app.services.knowledge import KnowledgeState


class KnowledgeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def load(self, user_id: UUID, role: str, level: str) -> list[KnowledgeState]:
        rows = await self.session.scalars(
            select(UserTopicKnowledge)
            .where(
                UserTopicKnowledge.user_id == user_id,
                UserTopicKnowledge.role == role,
                UserTopicKnowledge.level == level,
            )
            .order_by(UserTopicKnowledge.topic, UserTopicKnowledge.subtopic)
        )
        return [
            KnowledgeState(
                topic=row.topic,
                subtopic=row.subtopic,
                score=row.score,
                confidence=row.confidence,
                evidence_count=row.evidence_count,
                evidence_weight=row.evidence_weight,
            )
            for row in rows
        ]

    async def upsert(
        self,
        user_id: UUID,
        role: str,
        level: str,
        states: Sequence[KnowledgeState],
    ) -> None:
        existing_rows = await self.session.scalars(
            select(UserTopicKnowledge).where(
                UserTopicKnowledge.user_id == user_id,
                UserTopicKnowledge.role == role,
                UserTopicKnowledge.level == level,
            )
        )
        existing = {(row.topic.casefold(), row.subtopic.casefold()): row for row in existing_rows}
        for state in states:
            key = (state.topic.casefold(), state.subtopic.casefold())
            row = existing.get(key)
            if row is None:
                self.session.add(
                    UserTopicKnowledge(
                        user_id=user_id,
                        role=role,
                        level=level,
                        topic=state.topic,
                        subtopic=state.subtopic,
                        score=state.score,
                        confidence=state.confidence,
                        evidence_count=state.evidence_count,
                        evidence_weight=state.evidence_weight,
                    )
                )
                continue
            row.score = state.score
            row.confidence = state.confidence
            row.evidence_count = state.evidence_count
            row.evidence_weight = state.evidence_weight
