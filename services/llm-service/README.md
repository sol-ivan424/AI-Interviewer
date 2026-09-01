# AI Interviewer LLM service

The active runtime calls local Qwen3.5 9B through Ollama's OpenAI-compatible
`POST /v1/chat/completions` endpoint and validates structured responses with Pydantic.

Runtime settings:

- `LLM_API_BASE_URL` (`http://ollama:11434` in Compose)
- `LLM_API_KEY` (`ollama`; required by the client and ignored by Ollama)
- `LLM_PROVIDER` (`ollama` in Compose)
- `LLM_MODEL`
- `LLM_TIMEOUT_SECONDS`, `LLM_TEMPERATURE`, `LLM_MAX_TOKENS`

Active LLM endpoints:

- `POST /llm/analyze-question`
- `POST /llm/evaluate-answer`
- `POST /llm/generate-question`
- `POST /llm/generate-baseline-questions`
- `POST /llm/interviewer-message`

Prompts, model responses and API keys are not logged.

## Ollama

FastAPI-обёртка над локальной Ollama. Сервис формирует prompts, проверяет structured JSON и возвращает контролируемые `502`/`503`, чтобы API-service мог включить fallback scoring.

## Настройки

| Переменная | Значение по умолчанию |
| --- | --- |
| `OLLAMA_BASE_URL` | `http://ollama:11434` |
| `LLM_MODEL` | `qwen3.5:9b` |
| `LLM_TIMEOUT_SECONDS` | `60` |
| `LLM_TEMPERATURE` | `0.2` |
| `LLM_MAX_TOKENS` | `1800` |

## Локальный запуск

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
uvicorn app.main:app --reload --port 8001
```

Перед первым inference загрузите модель в запущенную Ollama:

```text
ollama pull qwen3.5:9b
```

Endpoints:

- `GET /health`
- `GET /llm/health`
- `POST /llm/interviewer-message`
- `POST /llm/evaluate-answer`

Проверки:

```powershell
pytest
ruff check .
ruff format --check .
```

Сервис логирует только тип prompt, модель и latency. Полные prompts и ответы модели не сохраняются.
