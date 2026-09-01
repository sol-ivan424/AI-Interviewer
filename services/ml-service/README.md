# AI Interviewer ML service

FastAPI service with two reproducible baseline models:

- weak-topic classification: TF-IDF and logistic regression;
- candidate-level prediction: random forest.

The dataset is synthetic and deterministic (`seed=42`). Its metrics demonstrate the training
and inference pipeline, not expected production quality. Model artifacts are generated during
the Docker build and are loaded only from the configured local artifact directory.

## Local setup

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
python -m training.generate_synthetic --output data/synthetic
python -m training.train --data data/synthetic --output artifacts
$env:ML_ARTIFACT_DIR = "$PWD\artifacts"
uvicorn app.main:app --reload --port 8002
```

Generated `metrics.json` contains accuracy, macro F1, classification reports, and confusion
matrices. `manifest.json` records data schema version `1.0`, model version `1.0.0`, labels, and
the exact numeric feature order.

## Endpoints

- `GET /health`
- `POST /ml/predict-level`
- `POST /ml/classify-weak-topic`
- `POST /ml/recommendations/rank`

Recommendation ranking combines rule-based severity with the topic classifier probability for
known skills. Unknown skills receive no model bonus and retain stable ordering.

## Checks

```powershell
pytest
ruff check .
ruff format --check .
```
