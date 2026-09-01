from app.schemas.chat import InterviewerMessageRequest
from app.schemas.evaluation import EvaluationRequest


def build_evaluation_prompt(request: EvaluationRequest) -> str:
    evaluation_points = "\n".join(f"- {point}" for point in request.evaluation_points)
    return f"""Ты технический интервьюер.

Твоя задача — оценить ответ кандидата на вопрос собеседования.

Роль: {request.role}
Уровень: {request.level}
Тема: {request.skill}

Вопрос:
{request.question_text}

Идеальный ответ:
{request.ideal_answer}

Критерии оценки:
{evaluation_points}

Ответ кандидата:
{request.user_answer}

Оцени ответ строго по критериям.

Верни только JSON без markdown и без дополнительного текста.

Формат JSON:
{{
  "score": number from 0 to 10,
  "max_score": 10,
  "verdict": "correct" | "partially_correct" | "incorrect",
  "feedback": "короткий feedback на русском языке",
  "matched_points": ["список раскрытых критериев"],
  "missing_points": ["список пропущенных критериев"]
}}"""


def build_interviewer_prompt(request: InterviewerMessageRequest) -> str:
    return f"""Ты технический интервьюер.

Сформулируй короткий естественный переход к следующему вопросу без подсказки ответа.

Роль: {request.role}
Уровень: {request.level}
Вопрос {request.context.question_number} из {request.context.total_questions}:
{request.question_text}

Верни только JSON без markdown и дополнительного текста:
{{"message": "сообщение интервьюера на русском языке"}}"""
