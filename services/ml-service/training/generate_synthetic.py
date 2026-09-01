import argparse
import csv
import json
import random
from pathlib import Path

SCHEMA_VERSION = "1.0"
SEED = 42
TOPICS = {
    "SQL": ("query index join database", "indexes and query plans"),
    "REST": ("http resource endpoint api", "resource semantics and status codes"),
    "Docker": ("container image layer dockerfile", "image layers and container isolation"),
    "Transactions": ("commit rollback isolation atomic", "isolation levels and rollback"),
    "RAG": ("retrieval context generation chunks", "retrieval quality and grounded context"),
    "Embeddings": ("vector similarity semantic search", "vector similarity and normalization"),
    "Metrics": ("precision recall f1 accuracy", "metric selection and class imbalance"),
    "Overfitting": (
        "train validation regularization generalization",
        "validation and regularization",
    ),
    "Model Deployment": ("serving inference model version rollout", "versioning and safe rollout"),
}
LEVEL_FEATURES = [
    "average_score",
    "backend_score",
    "ml_score",
    "llm_score",
    "answers_count",
    "correct_answers_count",
    "partial_answers_count",
    "wrong_answers_count",
    "weak_skills_count",
    "average_answer_length",
]


def clamp(value: float, lower: float, upper: float) -> float:
    return round(max(lower, min(upper, value)), 2)


def generate_topic_rows(rng: random.Random) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for topic, (keywords, missing) in TOPICS.items():
        words = keywords.split()
        for index in range(40):
            rng.shuffle(words)
            score = rng.randint(0, 6)
            rows.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "answer_text": (
                        f"I know {' '.join(words[: rng.randint(1, len(words))])} "
                        f"but need more practice {index % 5}"
                    ),
                    "missing_points": json.dumps([missing, f"practical {topic} details"]),
                    "score": score,
                    "max_score": 10,
                    "target_topic": topic,
                }
            )
    rng.shuffle(rows)
    return rows


def generate_level_rows(rng: random.Random) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    profiles = {
        "junior": (34, 8, 120, (5, 20)),
        "middle": (62, 7, 260, (15, 40)),
        "senior": (84, 6, 520, (30, 70)),
    }
    for level, (center, spread, length_center, answer_range) in profiles.items():
        for _ in range(120):
            answers_count = rng.randint(*answer_range)
            average_score = clamp(rng.gauss(center, spread), 0, 100)
            correct_ratio = clamp((average_score - 10) / 100, 0.05, 0.9)
            correct = min(answers_count, round(answers_count * correct_ratio))
            wrong = min(
                answers_count - correct, round(answers_count * (1 - average_score / 100) * 0.55)
            )
            partial = answers_count - correct - wrong
            rows.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "average_score": average_score,
                    "backend_score": clamp(rng.gauss(center, spread + 3), 0, 100),
                    "ml_score": clamp(rng.gauss(center, spread + 3), 0, 100),
                    "llm_score": clamp(rng.gauss(center, spread + 3), 0, 100),
                    "answers_count": answers_count,
                    "correct_answers_count": correct,
                    "partial_answers_count": partial,
                    "wrong_answers_count": wrong,
                    "weak_skills_count": max(
                        0, round((100 - average_score) / 14 + rng.gauss(0, 1))
                    ),
                    "average_answer_length": clamp(
                        rng.gauss(length_center, length_center * 0.15), 20, 1000
                    ),
                    "target_level": level,
                }
            )
    rng.shuffle(rows)
    return rows


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def generate(output_dir: Path) -> None:
    rng = random.Random(SEED)
    write_csv(output_dir / "topic_weakness_v1.csv", generate_topic_rows(rng))
    write_csv(output_dir / "candidate_level_v1.csv", generate_level_rows(rng))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("data/synthetic"))
    generate(parser.parse_args().output)
