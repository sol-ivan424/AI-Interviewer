"""Idempotently seed the curated interview question bank."""

import asyncio
from dataclasses import asdict
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.data.question_bank import QUESTION_BANK
from app.db.session import create_session_factory
from app.models.question import Question

CONFLICT_COLUMNS = ("role", "level", "text")
MUTABLE_COLUMNS = (
    "skill",
    "ideal_answer",
    "evaluation_points",
    "max_score",
    "is_active",
    "source",
)


def _question_values() -> list[dict[str, Any]]:
    values = []
    seen: dict[tuple[str, str], int] = {}
    for question in QUESTION_BANK:
        item = asdict(question)
        item["evaluation_points"] = list(question.evaluation_points)
        key = (question.role, question.level)
        seen[key] = seen.get(key, 0) + 1
        item["source"] = "seed" if seen[key] <= 3 else "fallback"
        values.append(item)
    return values


async def seed_questions(session: AsyncSession) -> int:
    """Insert or update all curated questions and return the resulting row count."""
    values = _question_values()
    bind = session.get_bind()

    if bind.dialect.name == "postgresql":
        statement = postgresql_insert(Question).values(values)
    elif bind.dialect.name == "sqlite":
        statement = sqlite_insert(Question).values(values)
    else:
        raise RuntimeError(f"Question seed does not support database dialect: {bind.dialect.name}")

    excluded = statement.excluded
    update_values = {column: getattr(excluded, column) for column in MUTABLE_COLUMNS}
    update_values["updated_at"] = func.now()
    statement = statement.on_conflict_do_update(
        index_elements=list(CONFLICT_COLUMNS),
        set_=update_values,
    )

    await session.execute(statement)
    await session.commit()
    result = await session.scalar(select(func.count()).select_from(Question))
    return int(result or 0)


async def main(settings: Settings | None = None) -> None:
    """Load settings, connect to the configured database, and seed questions."""
    app_settings = settings or get_settings()
    engine, session_factory = create_session_factory(app_settings.database_url)
    try:
        async with session_factory() as session:
            total = await seed_questions(session)
        print(f"Question seed completed: {total} questions in database.")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
