# PRD.md — AI Interviewer

> Актуальное переопределение от 2026-08-04: каждое интервью содержит 15 вопросов.
> Первые 5 заново генерирует LLM по пяти разным областям без подготовленного банка;
> вопросы 6–15 генерирует LLM по целям, выбранным ML-картой знаний. При повторном
> прохождении первые 5 вопросов не должны повторять историю пользователя. Это правило
> имеет приоритет над сохранёнными ниже историческими требованиями Phase 9.

> Актуальная целевая схема продукта описана в разделе 49. Разделы про фиксированное
> MVP-интервью и локальную Ollama сохраняются как история уже реализованных фаз;
> при противоречии требования Phase 9 имеют приоритет.

## 1. Краткое описание

**AI Interviewer** — full-stack web-платформа для подготовки к техническим собеседованиям.

Пользователь регистрируется, выбирает роль и уровень, проходит интервью в формате чата, получает оценку ответов, видит уровень знания тем и получает персональные рекомендации по обучению.

Проект должен выглядеть как production-like pet-project, который демонстрирует сразу несколько направлений:

- backend-разработка;
- full-stack разработка;
- микросервисная архитектура;
- локально развёрнутая LLM;
- prompt engineering;
- собственная логика оценки и рекомендаций;
- подготовка данных для ML;
- дальнейшая интеграция собственных ML-моделей;
- аналитика результатов пользователя;
- Docker-based deployment.

Важно: проект должен развиваться поэтапно. Не нужно реализовывать сразу всё, что возможно. Каждая итерация должна оставлять проект в рабочем состоянии и логично расширять предыдущую версию.

---

## 2. Главная цель проекта

Создать сайт, где пользователь может пройти техническое интервью в чате и получить понятную обратную связь:

- итоговый результат;
- оценку по отдельным темам;
- список слабых тем;
- рекомендации по обучению;
- историю ответов;
- аналитику прогресса.

Снаружи продукт должен выглядеть как законченный сайт, а внутри — как хорошо спроектированная система с отдельными слоями:

```text
frontend -> api-service -> llm-service -> local-llm-runtime
                    |
                    -> ml-service
                    |
                    -> postgres
                    |
                    -> redis
```

---

## 3. Итоговый пользовательский продукт

На выходе должен получиться сайт **AI Interviewer**.

Пользовательский сценарий:

1. Пользователь открывает сайт.
2. Регистрируется или входит в аккаунт.
3. Попадает на dashboard.
4. Выбирает роль:
   - Backend-разработчик;
   - ML-инженер;
   - LLM-инженер.
5. Выбирает уровень:
   - Junior;
   - Middle;
   - Senior.
6. Запускает интервью.
7. Отвечает на вопросы в чате.
8. После каждого ответа получает оценку и feedback.
9. После последнего вопроса интервью завершается автоматически.
10. Пользователь видит итоговый результат.
11. Пользователь открывает вкладку “Уровень знаний”.
12. Пользователь открывает вкладку “Рекомендации”.
13. Пользователь открывает вкладку “История ответов”.
14. На dashboard обновляется статистика.

---

## 4. Основная идея интерфейса

Главный экран продукта — **страница интервью**.

На странице интервью центральным элементом является чат. Рядом с чатом или внутри этой же страницы должны быть вкладки:

```text
Чат
Уровень знаний
Рекомендации
История ответов
```

Пользователь не должен искать результат в разных местах сайта. Основная информация должна быть доступна прямо на странице интервью.

---

## 5. Основные страницы сайта

Минимальный набор страниц:

```text
/login
/register
/dashboard
/interviews/{interview_id}
```

Опционально позже:

```text
/profile
/interviews
/settings
```

---

## 6. Страница регистрации

URL:

```text
/register
```

На странице должны быть:

- поле имени пользователя;
- поле email;
- поле password;
- кнопка регистрации;
- ссылка на страницу входа.

После успешной регистрации пользователь может войти в систему.

---

## 7. Страница входа

URL:

```text
/login
```

На странице должны быть:

- поле email;
- поле password;
- кнопка входа;
- ссылка на регистрацию.

После успешного входа пользователь попадает на dashboard.

---

## 8. Dashboard

URL:

```text
/dashboard
```

Dashboard — стартовая страница авторизованного пользователя.

На странице должны быть:

- приветствие пользователя;
- кнопка или блок “Начать интервью”;
- выбор роли;
- выбор уровня;
- краткая статистика пользователя;
- список последних интервью.

Статистика:

```text
Количество завершённых интервью
Средний результат
Самая сильная тема
Самая слабая тема
Последние интервью
```

Пример:

```text
Пройдено интервью: 4
Средний результат: 68%
Самая сильная тема: Docker
Самая слабая тема: SQL
```

Если пользователь ещё не проходил интервью, dashboard должен показывать пустое состояние и предлагать начать первое интервью.

---

## 9. Страница интервью

URL:

```text
/interviews/{interview_id}
```

Страница интервью — основной экран продукта.

На странице должны быть:

- выбранная роль;
- выбранный уровень;
- статус интервью;
- текущий номер вопроса;
- промежуточный score;
- вкладки;
- чат;
- результаты после завершения.

Пример структуры:

```text
-----------------------------------------------------
AI Interviewer
Backend-разработчик / Junior
-----------------------------------------------------
[Чат] [Уровень знаний] [Рекомендации] [История]
-----------------------------------------------------
Контент выбранной вкладки
-----------------------------------------------------
Вопрос 2 из 5 | Текущий результат: 14/20
-----------------------------------------------------
```

---

## 10. Вкладка “Чат”

Вкладка “Чат” используется для прохождения интервью.

На вкладке должны быть:

- область сообщений;
- сообщение от AI-интервьюера с вопросом;
- сообщение пользователя с ответом;
- feedback от системы;
- поле ввода ответа;
- кнопка отправки ответа;
- индикатор прогресса по вопросам.

Сценарий работы:

1. Система показывает первый вопрос.
2. Пользователь вводит ответ.
3. Пользователь нажимает “Отправить”.
4. Backend отправляет ответ на оценку.
5. Оценка выполняется через локальную LLM.
6. Если LLM недоступна, используется fallback scoring.
7. В чат добавляется сообщение с оценкой и feedback.
8. Система показывает следующий вопрос.
9. После последнего вопроса интервью завершается.
10. Поле ввода блокируется.
11. В чате появляется итоговое сообщение.

Пример сообщения AI:

```text
AI Interviewer:
Что такое REST API?
```

Пример ответа пользователя:

```text
Вы:
REST API — это архитектурный стиль для построения API вокруг ресурсов.
```

Пример feedback:

```text
AI Interviewer:
Оценка: 7/10

Ответ частично верный. Ты правильно указал, что REST связан с ресурсами, но не упомянул stateless-подход, HTTP-методы и status codes.
```

Итоговое сообщение:

```text
AI Interviewer:
Интервью завершено.

Итоговый результат: 64%.

Я подготовил оценку по темам и рекомендации. Открой вкладки “Уровень знаний” и “Рекомендации”, чтобы посмотреть подробности.
```

---

## 11. Вкладка “Уровень знаний”

Вкладка “Уровень знаний” показывает, насколько хорошо пользователь знает отдельные темы.

Данные формируются на основе:

- вопросов интервью;
- ответов пользователя;
- оценок за ответы;
- skill score по каждой теме;
- пропущенных evaluation points.

На вкладке должны отображаться:

- общий результат интервью;
- список тем;
- процент знания по каждой теме;
- статус каждой темы;
- краткое объяснение.

Правила статусов:

```text
>= 70%  -> Хорошо
40–69%  -> Нужно повторить
< 40%   -> Слабая тема
```

Пример:

```text
Общий результат: 64%

HTTP              80%   Хорошо
REST              70%   Хорошо
SQL               40%   Нужно повторить
Transactions      35%   Слабая тема
Docker            95%   Хорошо
```

Пример карточки темы:

```text
SQL

Уровень: 40%
Статус: Нужно повторить

Ты частично понимаешь базовые SQL-запросы, но слабо раскрыл индексы, JOIN и транзакции.
```

---

## 12. Вкладка “Рекомендации”

Вкладка “Рекомендации” показывает персональный план обучения.

Рекомендации формируются на основе слабых тем пользователя.

На вкладке должны быть:

- список слабых тем;
- приоритет изучения;
- текущий уровень по теме;
- причина рекомендации;
- список тем для изучения;
- список практических заданий.

Пример рекомендации:

```text
SQL

Приоритет: высокий
Текущий уровень: 40%

Почему:
Ты дал неполный ответ по SQL и не раскрыл индексы, JOIN и транзакции.

Что выучить:
- JOIN;
- индексы;
- транзакции;
- EXPLAIN ANALYZE;
- уровни изоляции.

Практика:
- решить 10 задач на JOIN;
- разобрать 5 SQL-запросов через EXPLAIN;
- написать пример транзакции с rollback.
```

---

## 13. Вкладка “История ответов”

Вкладка “История ответов” показывает все вопросы и ответы текущего интервью.

Для каждого вопроса нужно отображать:

- номер вопроса;
- тему;
- текст вопроса;
- ответ пользователя;
- оценку;
- verdict;
- feedback;
- раскрытые пункты;
- пропущенные пункты.

Пример:

```text
Вопрос 1. HTTP

Вопрос:
Что такое HTTP и чем отличаются GET и POST?

Ответ пользователя:
GET получает данные, POST отправляет данные.

Оценка:
7/10

Вердикт:
Частично верно

Раскрыто:
- GET используется для получения данных;
- POST используется для отправки данных.

Пропущено:
- идемпотентность;
- безопасность;
- изменение состояния сервера.
```

---

## 14. Роли интервью

Поддерживаемые роли:

```text
backend
ml_engineer
llm_engineer
```

Отображаемые названия:

```text
backend      -> Backend-разработчик
ml_engineer  -> ML-инженер
llm_engineer -> LLM-инженер
```

---

## 15. Уровни интервью

Поддерживаемые уровни:

```text
junior
middle
senior
```

Отображаемые названия:

```text
junior -> Junior
middle -> Middle
senior -> Senior
```

---

## 16. Seed-вопросы

В MVP должен быть подготовлен seed-набор из **45 вопросов**.

Формула:

```text
3 роли × 3 уровня × 5 вопросов = 45 вопросов
```

Для каждой комбинации `role + level` должно быть минимум 5 вопросов.

Каждый вопрос должен иметь:

```text
role
level
skill
text
ideal_answer
evaluation_points
max_score
is_active
```

`max_score` для каждого вопроса равен `10`.

Seed-команда должна быть идемпотентной: повторный запуск не должен создавать дубликаты.

---

## 17. Принцип выбора вопросов

При создании интервью система должна:

1. Получить `role` и `level`.
2. Найти активные вопросы по этой комбинации.
3. Случайно выбрать 5 вопросов.
4. Сохранить выбранные вопросы в таблицу `interview_questions`.
5. Зафиксировать порядок через `order_number`.

После создания интервью последовательность вопросов не должна меняться.

Повторное открытие интервью должно возвращать те же вопросы в том же порядке.

---

## 18. Количество вопросов в интервью

Для MVP каждое интервью содержит 5 вопросов.

Значение вынести в конфиг:

```text
INTERVIEW_QUESTIONS_COUNT=5
```

Пользователь в MVP не выбирает количество вопросов.

---

## 19. Статусы интервью

Использовать enum:

```text
in_progress
finished
```

Правила:

1. При создании интервью оно сразу получает статус `in_progress`.
2. После ответа на последний вопрос интервью автоматически получает статус `finished`.
3. Endpoint `/finish` используется для досрочного завершения.
4. После `finished` нельзя отправлять новые ответы.
5. Результат можно получить только для интервью со статусом `finished`.

Причина завершения:

```text
completed -> завершено после последнего ответа
manual    -> завершено досрочно через /finish
```

Поле `finished_reason` может быть `null`, пока интервью находится в статусе `in_progress`.

---

## 20. Scoring

Оценка ответа должна быть гибридной и расширяемой.

В MVP основной scoring выполняется через локальную LLM.

Если LLM недоступна или возвращает невалидный результат, используется rule-based fallback.

Архитектурно должен быть отдельный слой:

```text
ScoringService
```

Он должен уметь:

- отправлять ответ в `llm-service`;
- получать structured JSON;
- валидировать результат;
- сохранять provider;
- запускать fallback при ошибке.

Ожидаемый результат оценки:

```json
{
  "score": 7,
  "max_score": 10,
  "verdict": "partially_correct",
  "feedback": "Ответ частично верный...",
  "matched_points": ["..."],
  "missing_points": ["..."],
  "scoring_provider": "local_llm"
}
```

Допустимые verdict:

```text
correct
partially_correct
incorrect
```

Правила verdict:

```text
score >= 8 -> correct
score >= 4 -> partially_correct
score < 4  -> incorrect
```

---

## 21. Rule-based fallback scoring

Fallback нужен обязательно.

Он срабатывает, если:

- Ollama недоступна;
- LLM-service недоступен;
- превышен timeout;
- LLM вернула невалидный JSON;
- LLM вернула пустой ответ;
- произошла ошибка соединения.

Логика fallback:

1. У вопроса есть `evaluation_points`.
2. Ответ пользователя нормализуется:
   - lower case;
   - trim;
   - удаление лишних пробелов.
3. Сервис проверяет, какие evaluation points частично покрыты ответом.
4. Score рассчитывается пропорционально количеству найденных пунктов:

```text
score = round(max_score * matched_points_count / total_points_count)
```

Если ответ пустой, вернуть ошибку валидации.

В response нужно показывать provider:

```text
local_llm
rule_based_fallback
```

---

## 22. Рекомендательная модель

В системе должна быть отдельная логика формирования рекомендаций.

В MVP она реализуется как rule-based recommendation model.

Архитектурно она должна быть выделена в отдельный слой:

```text
RecommendationService
```

Эта логика не должна быть смешана с router-слоем, LLM-сервисом или frontend.

RecommendationService принимает:

```text
role
level
answers
answer scores
skill scores
weak skills
verdict по каждому ответу
matched evaluation points
missing evaluation points
```

RecommendationService возвращает:

```text
список слабых тем
уровень знания по каждой теме
приоритет изучения
объяснение рекомендации
список тем для изучения
список практических заданий
```

Пример структуры:

```json
{
  "skill": "SQL",
  "priority": "high",
  "current_percentage": 40,
  "reason": "Нужно лучше разобраться с SQL, потому что в ответах были пропущены индексы, JOIN и транзакции.",
  "topics_to_learn": [
    "JOIN",
    "индексы",
    "транзакции",
    "EXPLAIN ANALYZE"
  ],
  "practice_tasks": [
    "Решить 10 задач на JOIN",
    "Разобрать 5 SQL-запросов через EXPLAIN",
    "Написать пример транзакции с rollback"
  ]
}
```

Правила приоритета:

```text
< 40%   -> high
40–69%  -> medium
>= 70%  -> рекомендация не нужна
```

---

## 23. Роль ML в проекте

ML в проекте нужен не как формальность, а как отдельный слой анализа пользователя.

Цель ML-части:

- показать умение готовить датасет;
- обучать baseline-модели;
- считать метрики;
- сохранять модели;
- поднимать inference API;
- интегрировать модель в backend;
- использовать предсказания для рекомендаций и аналитики.

### 23.1. MVP

В первой версии ML-модель может быть не полноценной нейросетью, а rule-based моделью рекомендаций и аналитики.

Но данные должны сохраняться так, чтобы позже на них можно было обучить ML-модели:

```text
ответы пользователя
оценки
verdict
темы вопросов
missing evaluation points
matched evaluation points
итоговый score
роль
уровень
история интервью
```

### 23.2. Следующая итерация ML

Во второй ML-итерации нужно добавить отдельный `ml-service`.

Он должен решать минимум две задачи:

#### 1. Topic Weakness Classifier

Задача: определить слабую тему пользователя на основе ответов, missing points и score.

Тип задачи:

```text
multi-class classification
```

Пример классов:

```text
SQL
REST
Docker
Transactions
RAG
Embeddings
Metrics
Overfitting
Model Deployment
```

Модель:

```text
TfidfVectorizer + LogisticRegression
```

Метрики:

```text
accuracy
macro F1
classification report
confusion matrix
```

#### 2. Candidate Level Predictor

Задача: предсказать текущий уровень пользователя.

Классы:

```text
junior
middle
senior
```

Признаки:

```text
average_score
backend_score
ml_score
llm_score
answers_count
correct_answers_count
partial_answers_count
wrong_answers_count
weak_skills_count
average_answer_length
```

Модель:

```text
RandomForestClassifier
```

Метрики:

```text
accuracy
macro F1
confusion matrix
```

### 23.3. ML-service endpoints

```text
GET /health
POST /ml/predict-level
POST /ml/classify-weak-topic
POST /ml/recommendations/rank
```

### 23.4. Интеграция ML с продуктом

ML-предсказания должны использоваться для:

- уточнения уровня пользователя;
- ранжирования рекомендаций;
- определения слабых тем;
- отображения аналитики на dashboard.

---

## 24. Локальная LLM

В проекте должна использоваться локально развёрнутая LLM, а не внешний коммерческий API.

LLM должна запускаться внутри инфраструктуры проекта через Docker Compose.

Цель:

- показать локальный inference;
- показать отдельный LLM-сервис;
- показать prompt engineering;
- показать structured output;
- показать fallback;
- показать возможность заменить модель без переписывания backend.

---

## 25. Архитектура LLM-части

В системе должны быть два компонента:

```text
llm-service
ollama
```

Где:

```text
llm-service -> наш FastAPI-сервис-обёртка
ollama      -> локальный runtime для open-source LLM
```

Архитектура:

```text
Frontend
   |
   v
API Service
   |
   v
LLM Service
   |
   v
Ollama / Local LLM Runtime
```

`api-service` не должен напрямую обращаться к Ollama. Все обращения к локальной модели должны проходить через `llm-service`.

---

## 26. LLM-service

`llm-service` должен быть отдельным FastAPI-приложением.

Он отвечает за:

- prompt templates;
- генерацию сообщений интервьюера;
- оценку ответов пользователя;
- генерацию feedback;
- возврат structured JSON;
- обработку ошибок локальной модели;
- fallback-сигналы для api-service;
- логирование latency;
- возможность заменить runtime.

Структура:

```text
services/
└── llm-service/
    ├── app/
    │   ├── main.py
    │   ├── core/
    │   │   └── config.py
    │   ├── schemas/
    │   │   ├── evaluation.py
    │   │   └── chat.py
    │   ├── services/
    │   │   ├── ollama_client.py
    │   │   ├── prompt_builder.py
    │   │   └── evaluation_service.py
    │   └── api/
    │       └── v1/
    │           ├── health.py
    │           └── llm.py
    ├── Dockerfile
    └── requirements.txt
```

---

## 27. LLM-service endpoints

### GET /health

Response:

```json
{
  "status": "ok",
  "runtime": "ollama"
}
```

### GET /llm/health

Response:

```json
{
  "status": "ok",
  "provider": "ollama",
  "model": "llama3.1:8b",
  "available": true
}
```

### POST /llm/interviewer-message

Request:

```json
{
  "role": "backend",
  "level": "junior",
  "question_text": "Что такое REST API?",
  "context": {
    "question_number": 2,
    "total_questions": 5
  }
}
```

Response:

```json
{
  "message": "Следующий вопрос: что такое REST API и какие основные принципы REST ты знаешь?"
}
```

### POST /llm/evaluate-answer

Request:

```json
{
  "role": "backend",
  "level": "junior",
  "skill": "REST",
  "question_text": "Что такое REST API?",
  "ideal_answer": "REST API — это архитектурный стиль для построения API вокруг ресурсов...",
  "evaluation_points": [
    "REST это архитектурный стиль",
    "API строится вокруг ресурсов",
    "Используются HTTP методы",
    "Взаимодействие stateless",
    "Используются HTTP status codes"
  ],
  "user_answer": "REST API — это когда клиент общается с сервером через HTTP."
}
```

Response:

```json
{
  "score": 5,
  "max_score": 10,
  "verdict": "partially_correct",
  "feedback": "Ответ частично верный. Ты указал связь REST с HTTP и клиент-серверным взаимодействием, но не раскрыл ресурсы, stateless-подход и HTTP status codes.",
  "matched_points": [
    "Используются HTTP методы"
  ],
  "missing_points": [
    "REST это архитектурный стиль",
    "API строится вокруг ресурсов",
    "Взаимодействие stateless",
    "Используются HTTP status codes"
  ]
}
```

---

## 28. Prompt для оценки ответа

`llm-service` должен использовать prompt template:

```text
Ты технический интервьюер.

Твоя задача — оценить ответ кандидата на вопрос собеседования.

Роль: {role}
Уровень: {level}
Тема: {skill}

Вопрос:
{question_text}

Идеальный ответ:
{ideal_answer}

Критерии оценки:
{evaluation_points}

Ответ кандидата:
{user_answer}

Оцени ответ строго по критериям.

Верни только JSON без markdown и без дополнительного текста.

Формат JSON:
{
  "score": number from 0 to 10,
  "max_score": 10,
  "verdict": "correct" | "partially_correct" | "incorrect",
  "feedback": "короткий feedback на русском языке",
  "matched_points": ["список раскрытых критериев"],
  "missing_points": ["список пропущенных критериев"]
}
```

Если LLM возвращает невалидный JSON, `llm-service` должен вернуть контролируемую ошибку, а `api-service` должен использовать fallback scoring.

---

## 29. Логирование LLM-запросов

Добавить таблицу:

```text
llm_requests
```

Поля:

```text
id
interview_id
answer_id
provider
model
prompt_type
latency_ms
success
error_message
created_at
```

Не нужно сохранять полный prompt и полный ответ модели в MVP. Достаточно metadata.

---

## 30. Backend API

Базовый prefix:

```text
/api/v1
```

Frontend должен использовать endpoints:

```text
POST /api/v1/auth/register
POST /api/v1/auth/login
GET  /api/v1/users/me

GET  /api/v1/roles

POST /api/v1/interviews
GET  /api/v1/interviews
GET  /api/v1/interviews/{id}
POST /api/v1/interviews/{id}/answers
POST /api/v1/interviews/{id}/finish
GET  /api/v1/interviews/{id}/result

GET  /api/v1/analytics/summary
GET  /api/v1/analytics/skills
GET  /api/v1/analytics/progress
```

---

## 31. Auth API

### POST /api/v1/auth/register

Request:

```json
{
  "email": "user@example.com",
  "password": "StrongPassword123",
  "full_name": "Иван Иванов"
}
```

Response 201:

```json
{
  "id": "uuid",
  "email": "user@example.com",
  "full_name": "Иван Иванов",
  "created_at": "2026-07-08T12:00:00Z"
}
```

Rules:

- email unique;
- password min length 8;
- password stored only as hash.

### POST /api/v1/auth/login

Request:

```json
{
  "email": "user@example.com",
  "password": "StrongPassword123"
}
```

Response:

```json
{
  "access_token": "jwt_token",
  "token_type": "bearer"
}
```

### GET /api/v1/users/me

Response:

```json
{
  "id": "uuid",
  "email": "user@example.com",
  "full_name": "Иван Иванов",
  "created_at": "2026-07-08T12:00:00Z"
}
```

---

## 32. Roles API

### GET /api/v1/roles

Response:

```json
[
  {
    "slug": "backend",
    "title": "Backend-разработчик",
    "levels": ["junior", "middle", "senior"]
  },
  {
    "slug": "ml_engineer",
    "title": "ML-инженер",
    "levels": ["junior", "middle", "senior"]
  },
  {
    "slug": "llm_engineer",
    "title": "LLM-инженер",
    "levels": ["junior", "middle", "senior"]
  }
]
```

---

## 33. Interviews API

### POST /api/v1/interviews

Request:

```json
{
  "role": "backend",
  "level": "junior"
}
```

Response 201:

```json
{
  "id": "uuid",
  "role": "backend",
  "level": "junior",
  "status": "in_progress",
  "total_questions": 5,
  "answered_questions": 0,
  "current_question": {
    "interview_question_id": "uuid",
    "order_number": 1,
    "skill": "HTTP",
    "text": "Что такое HTTP и чем отличаются методы GET и POST?"
  },
  "created_at": "2026-07-08T12:00:00Z"
}
```

### GET /api/v1/interviews

Response:

```json
[
  {
    "id": "uuid",
    "role": "backend",
    "level": "junior",
    "status": "finished",
    "total_score": 32,
    "max_score": 50,
    "percentage": 64,
    "created_at": "2026-07-08T12:00:00Z",
    "finished_at": "2026-07-08T12:20:00Z"
  }
]
```

### GET /api/v1/interviews/{interview_id}

Response:

```json
{
  "id": "uuid",
  "role": "backend",
  "level": "junior",
  "status": "in_progress",
  "total_score": 12,
  "total_questions": 5,
  "answered_questions": 2,
  "current_question": {
    "interview_question_id": "uuid",
    "order_number": 3,
    "skill": "SQL",
    "text": "Что такое индекс в SQL и зачем он нужен?"
  },
  "created_at": "2026-07-08T12:00:00Z",
  "finished_at": null
}
```

### POST /api/v1/interviews/{interview_id}/answers

Request:

```json
{
  "interview_question_id": "uuid",
  "answer_text": "GET используется для получения данных, POST — для отправки данных..."
}
```

Business rules:

- интервью должно принадлежать текущему пользователю;
- статус должен быть `in_progress`;
- вопрос должен принадлежать этому интервью;
- пользователь может отвечать только на текущий unanswered вопрос;
- нельзя ответить на один вопрос дважды;
- после сохранения ответа обновляется `total_score`;
- если это последний вопрос, интервью завершается автоматически.

Response when interview continues:

```json
{
  "answer": {
    "id": "uuid",
    "score": 7,
    "max_score": 10,
    "verdict": "partially_correct",
    "feedback": "Ответ частично верный...",
    "matched_points": ["GET используется для получения данных"],
    "missing_points": ["Идемпотентность"],
    "scoring_provider": "local_llm"
  },
  "interview_status": "in_progress",
  "next_question": {
    "interview_question_id": "uuid",
    "order_number": 2,
    "skill": "REST",
    "text": "Что такое REST API?"
  }
}
```

Response when interview completed:

```json
{
  "answer": {
    "id": "uuid",
    "score": 8,
    "max_score": 10,
    "verdict": "correct",
    "feedback": "Ответ хороший. Основные пункты раскрыты.",
    "matched_points": ["..."],
    "missing_points": [],
    "scoring_provider": "local_llm"
  },
  "interview_status": "finished",
  "next_question": null,
  "result_url": "/api/v1/interviews/{interview_id}/result"
}
```

### POST /api/v1/interviews/{interview_id}/finish

Manual early finish.

Response:

```json
{
  "id": "uuid",
  "status": "finished",
  "finished_reason": "manual",
  "total_score": 18,
  "max_score": 50,
  "percentage": 36,
  "result_url": "/api/v1/interviews/{interview_id}/result"
}
```

### GET /api/v1/interviews/{interview_id}/result

Response:

```json
{
  "interview": {
    "id": "uuid",
    "role": "backend",
    "level": "junior",
    "status": "finished",
    "finished_reason": "completed",
    "total_score": 32,
    "max_score": 50,
    "percentage": 64,
    "started_at": "2026-07-08T12:00:00Z",
    "finished_at": "2026-07-08T12:20:00Z"
  },
  "skill_scores": [
    {
      "skill": "HTTP",
      "score": 8,
      "max_score": 10,
      "percentage": 80,
      "status": "good"
    },
    {
      "skill": "SQL",
      "score": 4,
      "max_score": 10,
      "percentage": 40,
      "status": "need_repeat"
    }
  ],
  "answers": [
    {
      "order_number": 1,
      "question_text": "Что такое HTTP и чем отличаются методы GET и POST?",
      "skill": "HTTP",
      "answer_text": "GET используется...",
      "score": 7,
      "max_score": 10,
      "verdict": "partially_correct",
      "feedback": "...",
      "matched_points": ["..."],
      "missing_points": ["..."]
    }
  ],
  "recommendations": [
    {
      "skill": "SQL",
      "priority": "medium",
      "current_percentage": 40,
      "reason": "Нужно лучше разобраться с SQL.",
      "topics_to_learn": ["JOIN", "индексы", "транзакции"],
      "practice_tasks": ["Решить задачи на JOIN", "Разобрать EXPLAIN ANALYZE"]
    }
  ]
}
```

---

## 34. Analytics API

### GET /api/v1/analytics/summary

Response:

```json
{
  "total_interviews": 5,
  "finished_interviews": 4,
  "average_percentage": 67,
  "best_role": "backend",
  "strongest_skill": "Docker",
  "weakest_skills": ["SQL", "RAG"]
}
```

Empty state:

```json
{
  "total_interviews": 0,
  "finished_interviews": 0,
  "average_percentage": null,
  "best_role": null,
  "strongest_skill": null,
  "weakest_skills": []
}
```

### GET /api/v1/analytics/skills

Response:

```json
[
  {
    "skill": "SQL",
    "average_percentage": 55,
    "answers_count": 4
  }
]
```

### GET /api/v1/analytics/progress

Response:

```json
[
  {
    "interview_id": "uuid",
    "role": "backend",
    "level": "junior",
    "finished_at": "2026-07-08T12:00:00Z",
    "percentage": 64
  }
]
```

Sort:

```text
finished_at ASC
```

---

## 35. Database schema

Use PostgreSQL UUID primary keys.

Use timezone-aware timestamps.

### users

```text
id UUID PK
email VARCHAR(320) UNIQUE NOT NULL
password_hash TEXT NOT NULL
full_name VARCHAR(255) NULL
created_at TIMESTAMPTZ NOT NULL DEFAULT now()
updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
```

### questions

```text
id UUID PK
role VARCHAR(50) NOT NULL
level VARCHAR(50) NOT NULL
skill VARCHAR(100) NOT NULL
text TEXT NOT NULL
ideal_answer TEXT NOT NULL
evaluation_points JSONB NOT NULL
max_score INTEGER NOT NULL DEFAULT 10
is_active BOOLEAN NOT NULL DEFAULT true
created_at TIMESTAMPTZ NOT NULL DEFAULT now()
updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
```

Indexes:

```text
(role, level)
skill
unique(role, level, text)
```

### interviews

```text
id UUID PK
user_id UUID FK users(id) ON DELETE CASCADE
role VARCHAR(50) NOT NULL
level VARCHAR(50) NOT NULL
status VARCHAR(50) NOT NULL DEFAULT 'in_progress'
finished_reason VARCHAR(50) NULL
total_score INTEGER NOT NULL DEFAULT 0
started_at TIMESTAMPTZ NOT NULL DEFAULT now()
finished_at TIMESTAMPTZ NULL
created_at TIMESTAMPTZ NOT NULL DEFAULT now()
updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
```

### interview_questions

```text
id UUID PK
interview_id UUID FK interviews(id) ON DELETE CASCADE
question_id UUID FK questions(id)
order_number INTEGER NOT NULL
created_at TIMESTAMPTZ NOT NULL DEFAULT now()
```

Constraints:

```text
unique(interview_id, question_id)
unique(interview_id, order_number)
```

### answers

```text
id UUID PK
interview_id UUID FK interviews(id) ON DELETE CASCADE
interview_question_id UUID FK interview_questions(id) ON DELETE CASCADE
answer_text TEXT NOT NULL
score INTEGER NOT NULL
max_score INTEGER NOT NULL DEFAULT 10
verdict VARCHAR(50) NOT NULL
feedback TEXT NOT NULL
matched_points JSONB NOT NULL
missing_points JSONB NOT NULL
scoring_provider VARCHAR(50) NOT NULL
llm_score INTEGER NULL
keyword_score INTEGER NULL
ml_score INTEGER NULL
created_at TIMESTAMPTZ NOT NULL DEFAULT now()
```

Constraints:

```text
score >= 0
score <= max_score
max_score > 0
unique(interview_question_id)
```

### llm_requests

```text
id UUID PK
interview_id UUID FK interviews(id) NULL
answer_id UUID FK answers(id) NULL
provider VARCHAR(50) NOT NULL
model VARCHAR(100) NOT NULL
prompt_type VARCHAR(100) NOT NULL
latency_ms INTEGER NULL
success BOOLEAN NOT NULL
error_message TEXT NULL
created_at TIMESTAMPTZ NOT NULL DEFAULT now()
```

---

## 36. Backend project structure

```text
services/
└── api-service/
    ├── app/
    │   ├── main.py
    │   ├── api/
    │   │   ├── deps.py
    │   │   └── routers/
    │   │       ├── auth.py
    │   │       ├── users.py
    │   │       ├── roles.py
    │   │       ├── interviews.py
    │   │       └── analytics.py
    │   ├── core/
    │   │   ├── config.py
    │   │   ├── security.py
    │   │   └── errors.py
    │   ├── db/
    │   │   ├── base.py
    │   │   ├── session.py
    │   │   └── models.py
    │   ├── repositories/
    │   │   ├── users.py
    │   │   ├── questions.py
    │   │   ├── interviews.py
    │   │   ├── answers.py
    │   │   └── analytics.py
    │   ├── schemas/
    │   │   ├── auth.py
    │   │   ├── users.py
    │   │   ├── interviews.py
    │   │   ├── answers.py
    │   │   └── analytics.py
    │   ├── services/
    │   │   ├── auth.py
    │   │   ├── llm_client.py
    │   │   ├── scoring.py
    │   │   ├── interviews.py
    │   │   ├── recommendations.py
    │   │   └── analytics.py
    │   └── scripts/
    │       └── seed_questions.py
    ├── alembic/
    ├── Dockerfile
    └── requirements.txt
```

---

## 37. Frontend project structure

```text
frontend/
├── src/
│   ├── app/
│   │   ├── login/
│   │   ├── register/
│   │   ├── dashboard/
│   │   └── interviews/[id]/
│   ├── components/
│   │   ├── AuthForm.tsx
│   │   ├── RoleSelector.tsx
│   │   ├── LevelSelector.tsx
│   │   ├── InterviewChat.tsx
│   │   ├── ChatMessage.tsx
│   │   ├── AnswerInput.tsx
│   │   ├── KnowledgeLevelPanel.tsx
│   │   ├── RecommendationsPanel.tsx
│   │   ├── AnswerHistoryPanel.tsx
│   │   ├── ProgressBar.tsx
│   │   ├── SkillScoreCard.tsx
│   │   ├── DashboardStats.tsx
│   │   └── InterviewHistoryList.tsx
│   ├── lib/
│   │   ├── api.ts
│   │   ├── auth.ts
│   │   └── types.ts
│   └── styles/
├── Dockerfile
└── package.json
```

Frontend stack:

```text
Next.js
TypeScript
Tailwind CSS
fetch or Axios
React Hook Form
simple progress bars or Recharts
```

---

## 38. Docker Compose

Docker Compose должен запускать:

```text
frontend
api-service
llm-service
ollama
postgres
redis
```

Example:

```yaml
services:
  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    depends_on:
      - api-service

  api-service:
    build: ./services/api-service
    ports:
      - "8000:8000"
    env_file:
      - .env
    depends_on:
      - postgres
      - redis
      - llm-service

  llm-service:
    build: ./services/llm-service
    ports:
      - "8001:8001"
    env_file:
      - .env
    depends_on:
      - ollama

  ollama:
    image: ollama/ollama:latest
    container_name: ai_interviewer_ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama

  postgres:
    image: postgres:16
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: ai_interviewer
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7
    ports:
      - "6379:6379"

volumes:
  postgres_data:
  ollama_data:
```

---

## 39. Environment variables

`.env.example`:

```text
APP_NAME=AI Interviewer
APP_ENV=local
DEBUG=true

DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/ai_interviewer
REDIS_URL=redis://redis:6379/0

JWT_SECRET_KEY=change_me
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

INTERVIEW_QUESTIONS_COUNT=5

LLM_PROVIDER=ollama
LLM_SERVICE_URL=http://llm-service:8001
OLLAMA_BASE_URL=http://ollama:11434
LLM_MODEL=llama3.1:8b
LLM_TIMEOUT_SECONDS=60
LLM_TEMPERATURE=0.2
LLM_MAX_TOKENS=700
SCORING_FALLBACK_ENABLED=true

NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

---

## 40. Commands

Start services:

```bash
docker compose up --build
```

Run migrations:

```bash
docker compose exec api-service alembic upgrade head
```

Seed questions:

```bash
docker compose exec api-service python -m app.scripts.seed_questions
```

Pull local LLM model:

```bash
docker compose up -d ollama
docker exec -it ai_interviewer_ollama ollama pull llama3.1:8b
```

Run tests:

```bash
docker compose exec api-service pytest
```

---

## 41. Development phases

Проект должен разрабатываться поэтапно.

### Phase 1 — Full-stack MVP skeleton

Цель: запустить сайт, авторизацию, dashboard, создание интервью и прохождение интервью через rule-based scoring.

Состав:

```text
frontend
api-service
postgres
auth
seed questions
interview chat
rule-based scoring
recommendations
analytics
Docker Compose
```

### Phase 2 — Local LLM integration

Цель: заменить основной scoring на локальную LLM.

Состав:

```text
llm-service
ollama
prompt templates
structured JSON
fallback scoring
llm_requests logs
```

### Phase 3 — ML-service

Цель: добавить собственные baseline ML-модели.

Состав:

```text
ml-service
synthetic dataset
training scripts
topic classifier
level predictor
model metrics
model inference endpoints
```

### Phase 4 — Product polish

Цель: улучшить UX и демонстрационную ценность.

Состав:

```text
better dashboard
charts
loading states
error states
README screenshots
architecture docs
```

Каждая фаза должна оставлять проект в рабочем состоянии.

---

## 42. Testing requirements

Use pytest for backend.

Minimum unit tests:

```text
ScoringService:
- empty answer validation
- full answer high score
- partial answer medium score
- irrelevant answer low score
- fallback works

RecommendationService:
- high priority for score < 40
- medium priority for 40-69
- no recommendation for >= 70
- empty answers returns empty recommendations

Interview state:
- cannot answer finished interview
- cannot answer non-current question
- cannot answer same question twice
- last answer finishes interview automatically
```

Minimum API tests:

```text
Auth:
- register
- duplicate email fails
- login returns token
- invalid login fails
- /users/me works

Interviews:
- create interview
- interview has 5 fixed questions
- answer question
- feedback contains score and verdict
- auto finish after 5th answer
- manual finish works
- result works only after finish
- user cannot access another user's interview

Analytics:
- empty state
- summary after finished interviews
- skills aggregation
- progress sorted by finished_at
```

LLM-service tests:

```text
- health endpoint works
- invalid LLM response is handled
- evaluation response schema validates
- timeout returns controlled error
```

---

## 43. Security requirements

1. Passwords must never be stored in plain text.
2. JWT secret must be configured through environment variables.
3. Protected endpoints must require Bearer token.
4. User must not access another user's resources.
5. For another user's interview return 404, not 403.
6. Do not expose `password_hash`.
7. Do not log passwords or tokens.
8. CORS origins must be configurable.

---

## 44. Non-functional requirements

### Maintainability

```text
routers contain HTTP logic
services contain business logic
repositories contain DB queries
schemas contain Pydantic models
models contain SQLAlchemy models
```

### Reliability

- Interview creation and question assignment must be done in one transaction.
- Answer submission and score update must be done in one transaction.
- LLM errors must not break interview flow.
- Fallback scoring must keep the product usable.

### Performance

MVP does not need heavy optimization, but avoid obvious N+1 queries.

Indexes required on:

```text
user_id
interview_id
role + level
status
skill
```

---

## 45. Out of scope for first version

Do not implement in first version:

```text
video interview
voice interview
WebSocket
payments
admin panel
OAuth
refresh tokens
vector database
RAG
PDF export
email notifications
mobile app
complex neural network recommendation model
```

Chat can work through regular REST requests. WebSocket is not required.

---

## 46. README requirements

README must include:

1. Project description.
2. Architecture diagram in text.
3. Tech stack.
4. How to run Docker Compose.
5. How to run migrations.
6. How to seed questions.
7. How to pull local LLM model.
8. How to run tests.
9. Main API endpoints.
10. Example user flow.
11. Explanation of local LLM.
12. Explanation of fallback scoring.
13. Explanation of RecommendationService.
14. Future roadmap.

---

## 47. Acceptance criteria

Project is considered ready when:

1. Site starts locally.
2. Backend starts locally.
3. PostgreSQL starts locally.
4. Ollama starts locally.
5. LLM-service starts locally.
6. User can register.
7. User can login.
8. User can open dashboard.
9. User can select role.
10. User can select level.
11. User can start interview.
12. User sees first question in chat.
13. User can send answer.
14. Answer is evaluated by local LLM when available.
15. Rule-based fallback works when LLM is unavailable.
16. User receives score and feedback in chat.
17. User can continue to next question.
18. Interview auto-finishes after last question.
19. Input is blocked after interview finished.
20. User sees final percentage.
21. User can open “Уровень знаний”.
22. User sees skill scores.
23. User can open “Рекомендации”.
24. User sees recommendations from RecommendationService.
25. User can open “История ответов”.
26. User sees all questions, answers, scores and feedback.
27. Dashboard updates statistics after interview.
28. Backend prevents access to another user's interviews.
29. Docker Compose runs all required services.
30. README contains full startup instructions.
31. Core backend logic is covered by tests.
32. LLM-service has healthcheck and controlled error handling.
33. Phase 9 принимает ключ внешнего LLM API только через environment variables.
34. The project can be demonstrated as a complete portfolio pet-project.

---

## 48. Instructions for Codex

Implement the project according to this PRD.

Do not ask additional clarification.

Use the simplest production-like approach consistent with the stack.

Do not implement features marked as out of scope.

Keep the code modular.

Do not put business logic into routers.

Do not hardcode secrets.

Не хардкодить ключ внешнего LLM API и не передавать его в frontend.

Начиная с Phase 9 использовать внешний OpenAI-compatible API только через
`llm-service`; `api-service` не обращается к провайдеру напрямую.

Make sure every phase can run independently.

The first implementation should focus on a working full-stack MVP with clean architecture and clear extension points for LLM and ML.

---

## 49. Phase 9 — адаптивное интервью и граф знаний

### 49.1. Цель

Интервью должно адаптироваться к знаниям пользователя. Заранее задаётся только
минимальный стартовый пул вопросов; следующие вопросы формируются по слабым или
недостаточно проверенным подтемам.

### 49.2. Сценарий

1. Для каждой комбинации `role + level` система назначает 3 seed-вопроса.
2. До показа вопроса LLM определяет темы и подтемы вопроса и вес каждой из них.
3. После ответа LLM оценивает общее качество ответа и степень раскрытия каждой
   темы вопроса.
4. Модель знаний обновляет граф пользователя по узлам `topic -> subtopic`,
   сохраняя оценку, уверенность и число наблюдений.
5. После стартового пула модель выбирает слабую или недостаточно проверенную
   подтему.
6. LLM генерирует следующий вопрос, эталонный ответ, критерии оценки и веса тем
   для выбранной подтемы.
7. Цикл повторяется до достижения настроенного количества вопросов.

Значения по умолчанию:

```text
INTERVIEW_SEED_QUESTIONS_COUNT=3
INTERVIEW_QUESTIONS_COUNT=5
```

Количество seed-вопросов должно быть положительным и не превышать общее
количество вопросов.

### 49.3. Контракты LLM

Все LLM-ответы возвращаются как строгий JSON и валидируются на границе
`llm-service`.

Анализ вопроса возвращает непустой список:

```json
{
  "topics": [
    {"topic": "Databases", "subtopic": "SQL joins", "weight": 0.6},
    {"topic": "Databases", "subtopic": "Indexes", "weight": 0.4}
  ]
}
```

Веса находятся в диапазоне `(0, 1]` и в сумме равны `1` с допустимой погрешностью
`0.01`. Темы одного вопроса уникальны по паре `topic + subtopic`.

Оценка ответа дополняет существующий scoring:

```json
{
  "score": 7,
  "max_score": 10,
  "verdict": "partially_correct",
  "feedback": "...",
  "matched_points": ["..."],
  "missing_points": ["..."],
  "topic_coverage": [
    {"topic": "Databases", "subtopic": "SQL joins", "coverage": 0.8},
    {"topic": "Databases", "subtopic": "Indexes", "coverage": 0.3}
  ]
}
```

Пары `topic + subtopic` в `topic_coverage` должны точно совпадать с анализом
вопроса. `coverage` находится в диапазоне `[0, 1]`.

Генерация вопроса получает `role`, `level`, целевые `topic/subtopic` и тексты
уже заданных вопросов. Ответ содержит `text`, `ideal_answer`, непустые
`evaluation_points` и валидные `topics` с весами. Повторять уже заданный вопрос
нельзя.

### 49.4. Модель и граф знаний

Для первого рабочего варианта не нужна graph database. Граф хранится в
PostgreSQL как уникальные узлы пользователя:

```text
user_id
role
level
topic
subtopic
score              # 0..100
confidence         # 0..1
evidence_count
evidence_weight
updated_at
```

Обновление должно учитывать `question topic weight` и `answer coverage`.
Baseline-модель использует накопительное взвешенное среднее. Следующая подтема
выбирается детерминированно по сочетанию низкой оценки и низкой уверенности.
Обученную модель можно подключить позднее без изменения LLM-контрактов и схемы
данных.

### 49.5. Внешний LLM API

`llm-service` обращается к OpenAI-compatible Chat Completions API стандартным
HTTP-клиентом. Провайдер, URL, модель, timeout и ключ задаются environment
variables. Ключ остаётся только в `llm-service`, не логируется и не попадает в
ответы API.

```text
LLM_API_BASE_URL
LLM_API_KEY
LLM_MODEL
LLM_TIMEOUT_SECONDS
LLM_TEMPERATURE
LLM_MAX_TOKENS
```

`api-service` продолжает общаться только с `llm-service`.

### 49.6. Fallback и устойчивость

- Если анализ вопроса недоступен, единственной темой становится существующий
  `skill` с весом `1.0`.
- Если оценка LLM недоступна, используется rule-based score, а одинаковый
  коэффициент покрытия применяется ко всем темам вопроса.
- Если модель знаний недоступна, используется тот же детерминированный baseline
  внутри API.
- Если генерация вопроса недоступна или невалидна, назначается ещё не заданный
  вопрос из сохранённого банка для той же `role + level`.
- Сетевые вызовы не должны удерживать DB-транзакцию. Перед сохранением ответа и
  следующего вопроса состояние интервью повторно проверяется под блокировкой.

### 49.7. Хранение и API

- `questions` хранит источник (`seed` или `generated`), целевую подтему и веса
  тем.
- `answers` хранит покрытие тем.
- `interviews` хранит целевое количество вопросов.
- `llm_requests` логирует только metadata для операций `analyze_question`,
  `evaluate_answer` и `generate_question`.
- Текущие interviews endpoints сохраняются; `total_questions` означает целевое
  количество, даже если адаптивные вопросы ещё не созданы.
- Повторное открытие возвращает уже созданные вопросы в неизменном порядке.

### 49.8. Критерии приёмки Phase 9

1. Новое интервью начинается с 3 seed-вопросов.
2. Веса тем и покрытие ответа проходят строгую валидацию.
3. После каждого ответа обновляются узлы графа знаний.
4. После стартового пула следующий вопрос создаётся для выбранной подтемы.
5. Сгенерированный вопрос сохраняется и не меняется после перезагрузки.
6. После 5 ответов интервью завершается автоматически.
7. Все четыре fallback-сценария оставляют интервью проходимым.
8. Ключ LLM API отсутствует в коде, БД, логах и frontend.
9. Миграции, backend-тесты, линтеры и production build проходят.
