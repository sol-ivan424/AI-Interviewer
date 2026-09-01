import argparse
import csv
import json
from pathlib import Path

import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

from app.model_service import build_topic_text
from app.schemas import WeaknessEvidence
from training.generate_synthetic import LEVEL_FEATURES, SCHEMA_VERSION

MODEL_VERSION = "1.0.0"
RANDOM_STATE = 42


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as source:
        rows = list(csv.DictReader(source))
    if not rows or {row["schema_version"] for row in rows} != {SCHEMA_VERSION}:
        raise ValueError(f"{path} must contain schema version {SCHEMA_VERSION}")
    return rows


def metric_report(model: object, x_test: list, y_test: list[str]) -> dict[str, object]:
    predictions = model.predict(x_test)
    labels = sorted(set(y_test))
    return {
        "accuracy": round(float(accuracy_score(y_test, predictions)), 6),
        "macro_f1": round(float(f1_score(y_test, predictions, average="macro")), 6),
        "labels": labels,
        "classification_report": classification_report(
            y_test, predictions, labels=labels, output_dict=True, zero_division=0
        ),
        "confusion_matrix": confusion_matrix(y_test, predictions, labels=labels).tolist(),
    }


def train(data_dir: Path, output_dir: Path) -> dict[str, object]:
    topic_rows = read_rows(data_dir / "topic_weakness_v1.csv")
    topic_x = [
        build_topic_text(
            [
                WeaknessEvidence(
                    answer_text=row["answer_text"],
                    missing_points=json.loads(row["missing_points"]),
                    score=int(row["score"]),
                    max_score=int(row["max_score"]),
                )
            ]
        )
        for row in topic_rows
    ]
    topic_y = [row["target_topic"] for row in topic_rows]
    topic_x_train, topic_x_test, topic_y_train, topic_y_test = train_test_split(
        topic_x, topic_y, test_size=0.25, random_state=RANDOM_STATE, stratify=topic_y
    )
    topic_model = Pipeline(
        [
            ("tfidf", TfidfVectorizer(ngram_range=(1, 2))),
            ("classifier", LogisticRegression(max_iter=500, random_state=RANDOM_STATE)),
        ]
    )
    topic_model.fit(topic_x_train, topic_y_train)

    level_rows = read_rows(data_dir / "candidate_level_v1.csv")
    level_x = [[float(row[name]) for name in LEVEL_FEATURES] for row in level_rows]
    level_y = [row["target_level"] for row in level_rows]
    level_x_train, level_x_test, level_y_train, level_y_test = train_test_split(
        level_x, level_y, test_size=0.25, random_state=RANDOM_STATE, stratify=level_y
    )
    level_model = RandomForestClassifier(n_estimators=100, random_state=RANDOM_STATE)
    level_model.fit(level_x_train, level_y_train)

    metrics = {
        "model_version": MODEL_VERSION,
        "data_schema_version": SCHEMA_VERSION,
        "dataset": "deterministic synthetic baseline",
        "topic_classifier": metric_report(topic_model, topic_x_test, topic_y_test),
        "level_predictor": metric_report(level_model, level_x_test, level_y_test),
    }
    manifest = {
        "model_version": MODEL_VERSION,
        "data_schema_version": SCHEMA_VERSION,
        "level_features": LEVEL_FEATURES,
        "topic_labels": sorted(set(topic_y)),
        "level_labels": sorted(set(level_y)),
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(topic_model, output_dir / "topic_classifier.joblib")
    joblib.dump(level_model, output_dir / "level_predictor.joblib")
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output_dir / "metrics.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return metrics


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=Path("data/synthetic"))
    parser.add_argument("--output", type=Path, default=Path("artifacts"))
    arguments = parser.parse_args()
    train(arguments.data, arguments.output)
