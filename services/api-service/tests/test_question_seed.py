import asyncio
from collections import Counter

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.data.question_bank import QUESTION_BANK
from app.db.base import Base
from app.models.question import Question
from app.scripts.seed_questions import seed_questions

EXPECTED_ROLES = {"backend", "ml_engineer", "llm_engineer"}
EXPECTED_LEVELS = {"junior", "middle", "senior"}


def test_question_bank_has_five_complete_questions_per_role_and_level() -> None:
    assert len(QUESTION_BANK) == 45
    assert Counter((item.role, item.level) for item in QUESTION_BANK) == {
        (role, level): 5 for role in EXPECTED_ROLES for level in EXPECTED_LEVELS
    }
    assert len({(item.role, item.level, item.text) for item in QUESTION_BANK}) == 45

    for item in QUESTION_BANK:
        assert item.role in EXPECTED_ROLES
        assert item.level in EXPECTED_LEVELS
        assert item.skill.strip()
        assert item.text.strip()
        assert item.ideal_answer.strip()
        assert len(item.evaluation_points) >= 4
        assert all(point.strip() for point in item.evaluation_points)
        assert len(set(item.evaluation_points)) == len(item.evaluation_points)
        assert item.max_score == 10
        assert item.is_active is True


def test_seed_questions_is_idempotent_and_updates_mutable_fields(tmp_path) -> None:
    asyncio.run(_assert_seed_is_idempotent(tmp_path / "question-seed.db"))


async def _assert_seed_is_idempotent(database_path) -> None:
    engine = create_async_engine(f"sqlite+aiosqlite:///{database_path}")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

        async with session_factory() as session:
            assert await seed_questions(session) == 45
            assert await seed_questions(session) == 45

            first_seed = QUESTION_BANK[0]
            question = await session.scalar(
                select(Question).where(
                    Question.role == first_seed.role,
                    Question.level == first_seed.level,
                    Question.text == first_seed.text,
                )
            )
            assert question is not None
            question.skill = "outdated-value"
            question.is_active = False
            await session.commit()

            assert await seed_questions(session) == 45
            await session.refresh(question)

            assert question.skill == first_seed.skill
            assert question.is_active is True
            assert question.ideal_answer == first_seed.ideal_answer
            assert question.evaluation_points == list(first_seed.evaluation_points)

            rows = (await session.scalars(select(Question))).all()
            assert len(rows) == 45
            assert len({(row.role, row.level, row.text) for row in rows}) == 45
            assert Counter((row.role, row.level, row.source) for row in rows) == {
                (role, level, source): count
                for role in EXPECTED_ROLES
                for level in EXPECTED_LEVELS
                for source, count in (("seed", 3), ("fallback", 2))
            }
    finally:
        await engine.dispose()
