# MVP acceptance report

Date: 2026-07-15  
Environment: Windows, Docker Desktop, Docker Compose, local `llama3.1:8b`

## Verification summary

- Docker Compose built and started frontend, API, LLM-service, ML-service, Ollama, PostgreSQL and Redis; all seven containers are healthy.
- Browser flow passed: register, login, select role/level, answer five questions, automatic finish, result tabs and updated dashboard.
- Local LLM success was verified through API-service; fallback was verified with Ollama stopped.
- API: 61 tests; LLM-service: 5 tests; ML-service: 2 training/inference tests; Ruff, ESLint, TypeScript and Next.js production build passed.
- Docker logs did not contain the test password, JWT or Authorization header.
- Phase 8 browser QA passed on desktop and 390px mobile: progress charts, skeletons,
  recoverable states, keyboard tabs, ARIA progress bars and zero console warnings/errors.

## PRD acceptance criteria

| # | Criterion | Status | Evidence |
| --- | --- | --- | --- |
| 1 | Site starts locally | Pass | Frontend container healthy; `/register` opened in browser. |
| 2 | Backend starts locally | Pass | API container healthy; `/health` responds. |
| 3 | PostgreSQL starts locally | Pass | PostgreSQL container healthy; migrations at head. |
| 4 | Ollama starts locally | Pass | Ollama container running with `llama3.1:8b`. |
| 5 | LLM-service starts locally | Pass | LLM-service container healthy. |
| 6 | User can register | Pass | Browser registration completed. |
| 7 | User can login | Pass | Browser login redirected to dashboard. |
| 8 | User can open dashboard | Pass | Dashboard rendered user greeting and empty state. |
| 9 | User can select role | Pass | `ml_engineer` selected in browser. |
| 10 | User can select level | Pass | `middle` selected in browser. |
| 11 | User can start interview | Pass | Interview created from dashboard. |
| 12 | User sees first question in chat | Pass | First question rendered with progress `0/5`. |
| 13 | User can send answer | Pass | Five answers submitted from chat. |
| 14 | Local LLM evaluates when available | Pass | Live API inference saved `scoring_provider=ollama` and successful LLM metadata. |
| 15 | Rule-based fallback works | Pass | With Ollama stopped, answers completed with `rule_based_fallback`. |
| 16 | User receives score and feedback | Pass | Chat displayed score, verdict and feedback after every answer. |
| 17 | User can continue to next question | Pass | Progress advanced from `0/5` through `5/5`. |
| 18 | Interview auto-finishes | Pass | Fifth answer changed status to finished. |
| 19 | Input is blocked after finish | Pass | Answer form was absent after completion. |
| 20 | User sees final percentage | Pass | Browser displayed final result `32%`. |
| 21 | Knowledge tab opens | Pass | Knowledge tab activated. |
| 22 | Skill scores are visible | Pass | Five skill scores and statuses rendered. |
| 23 | Recommendations tab opens | Pass | Recommendations tab activated. |
| 24 | RecommendationService output is visible | Pass | Five prioritized recommendations rendered. |
| 25 | Answer history tab opens | Pass | History tab activated. |
| 26 | Full answer history is visible | Pass | Five questions, answers, scores, feedback and criteria rendered. |
| 27 | Dashboard statistics update | Pass | Dashboard showed one completed interview and `32%` average. |
| 28 | Other users' interviews are inaccessible | Pass | API ownership tests return `404` for read/write/finish/result. |
| 29 | Docker Compose runs required services | Pass | Seven containers running and healthy with readiness dependencies. |
| 30 | README has startup instructions | Pass | Compose, migrations, seed, model pull and local startup documented. |
| 31 | Core backend logic is tested | Pass | Scoring, recommendations, auth, interviews, analytics and concurrency covered. |
| 32 | LLM-service health and errors are controlled | Pass | Health, schema, malformed JSON and `502/503` tests pass. |
| 33 | No paid external LLM keys required | Pass | Inference uses local Ollama only. |
| 34 | Complete portfolio demonstration is possible | Pass | Full browser flow and both LLM/fallback paths verified. |

## Phase 9 acceptance — 2026-07-22

- API-service: 64 tests passed; LLM-service: 8; ML-service: 3.
- Ruff passed for all Python services; frontend ESLint, TypeScript and Next.js
  production build passed.
- Alembic revision `20260722_0003` is at `head` in Docker PostgreSQL.
- Question bank contains 27 seed questions and 18 preserved fallback questions.
- Compose runs six required healthy containers; Ollama is preserved under the
  optional `local-llm` profile.
- Without `LLM_API_KEY`, a five-answer Docker smoke completed through
  `rule_based_fallback` and persisted five knowledge-graph nodes.
- Browser QA confirmed progress `1/5`, a visible in-progress knowledge node,
  accessible progressbar metadata and no console warnings/errors.
- External API transport and strict structured responses are covered with a fake
  provider. A live provider call is intentionally not recorded here because no
  user API key was supplied.

## Remaining environment check

A destructive clean-volume restart was not run because project instructions prohibit deleting Docker volumes without explicit user permission. The existing-volume Compose rebuild and full browser smoke test passed.
