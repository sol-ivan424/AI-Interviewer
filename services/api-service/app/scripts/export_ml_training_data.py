import argparse
import asyncio
import json
from collections import defaultdict
from pathlib import Path

from sqlalchemy import select

from app.core.config import get_settings
from app.db.session import create_session_factory
from app.models.answer import Answer
from app.models.interview import Interview
from app.models.interview_question import InterviewQuestion
from app.models.question import Question

SCHEMA_VERSION = "1.0"


def _level_record(interview: Interview, rows: list[tuple[Answer, Question]]) -> dict[str, object]:
    score = sum(answer.score for answer, _ in rows)
    max_score = sum(answer.max_score for answer, _ in rows)
    average_score = round(score * 100 / max_score, 2) if max_score else 0.0
    by_skill: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for answer, question in rows:
        by_skill[question.skill][0] += answer.score
        by_skill[question.skill][1] += answer.max_score

    return {
        "schema_version": SCHEMA_VERSION,
        "average_score": average_score,
        "backend_score": average_score if interview.role == "backend" else 0.0,
        "ml_score": average_score if interview.role == "ml_engineer" else 0.0,
        "llm_score": average_score if interview.role == "llm_engineer" else 0.0,
        "answers_count": len(rows),
        "correct_answers_count": sum(a.verdict == "correct" for a, _ in rows),
        "partial_answers_count": sum(a.verdict == "partially_correct" for a, _ in rows),
        "wrong_answers_count": sum(a.verdict == "incorrect" for a, _ in rows),
        "weak_skills_count": sum(
            score * 100 / maximum < 40 for score, maximum in by_skill.values()
        ),
        "average_answer_length": round(
            sum(len(answer.answer_text.strip()) for answer, _ in rows) / len(rows), 2
        ),
        # The selected interview level is a proxy label, not expert assessment.
        "target_level": interview.level,
    }


async def export(output_dir: Path) -> tuple[int, int]:
    settings = get_settings()
    engine, session_factory = create_session_factory(settings.database_url)
    try:
        async with session_factory() as session:
            result = await session.execute(
                select(Interview, Answer, Question)
                .join(InterviewQuestion, InterviewQuestion.interview_id == Interview.id)
                .join(Question, Question.id == InterviewQuestion.question_id)
                .join(Answer, Answer.interview_question_id == InterviewQuestion.id)
                .where(Interview.status == "finished")
                .order_by(Interview.id, InterviewQuestion.order_number)
            )
            grouped: dict[object, tuple[Interview, list[tuple[Answer, Question]]]] = {}
            for interview, answer, question in result.all():
                grouped.setdefault(interview.id, (interview, []))[1].append((answer, question))
    finally:
        await engine.dispose()

    output_dir.mkdir(parents=True, exist_ok=True)
    topic_records = [
        {
            "schema_version": SCHEMA_VERSION,
            "missing_points": answer.missing_points,
            "score_ratio": round(answer.score / answer.max_score, 3),
            "answer_length": len(answer.answer_text.strip()),
            "target_skill": question.skill,
        }
        for _, rows in grouped.values()
        for answer, question in rows
        if answer.score / answer.max_score < 0.7
    ]
    level_records = [
        _level_record(interview, rows)
        for interview, rows in grouped.values()
        if interview.finished_reason == "completed" and rows
    ]
    for name, records in (
        ("topic_weakness.jsonl", topic_records),
        ("candidate_level.jsonl", level_records),
    ):
        (output_dir / name).write_text(
            "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records),
            encoding="utf-8",
        )
    return len(topic_records), len(level_records)


def main() -> None:
    parser = argparse.ArgumentParser(description="Export anonymized ML training features")
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()
    topic_count, level_count = asyncio.run(export(args.output_dir))
    print(f"Exported {topic_count} topic rows and {level_count} level rows")


if __name__ == "__main__":
    main()
