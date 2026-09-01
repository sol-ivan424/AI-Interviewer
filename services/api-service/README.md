# AI Interviewer API service

FastAPI entry point for AI Interviewer. The service currently includes async
SQLAlchemy, Alembic migrations, PostgreSQL models, JWT authentication, the
five-question LLM-generated baseline, 15-question adaptive interview state machine, persistent topic
knowledge graph, external-LLM/ML fallbacks, recommendations, analytics, and the
public health check. Generated questions reuse the existing interviews API and
are stored before being returned to the client.

## Local development

Requires Python 3.12 or newer.

```bash
python -m venv .venv
python -m pip install -r requirements-dev.txt
uvicorn app.main:app --reload --port 8000
```

Copy `.env.example` to `.env` when local values must differ from the defaults.
Apply database migrations before starting the API:

```bash
alembic upgrade head
```

## Checks

```bash
pytest
ruff check .
ruff format --check .
```

Implemented endpoints:

- `GET /health`
- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `GET /api/v1/users/me`
- `GET /api/v1/roles`
- `POST /api/v1/interviews`
- `GET /api/v1/interviews`
- `GET /api/v1/interviews/{id}`
- `POST /api/v1/interviews/{id}/answers`
- `POST /api/v1/interviews/{id}/finish`
- `GET /api/v1/interviews/{id}/result`
- `GET /api/v1/analytics/summary`
- `GET /api/v1/analytics/skills`
- `GET /api/v1/analytics/progress`
