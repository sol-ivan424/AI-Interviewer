"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import {
  FormEvent,
  KeyboardEvent,
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";

import { AuthGuard } from "@/components/AuthGuard";
import { ApiError, apiRequest, clearToken } from "@/lib/api";
import type { InterviewDetail, InterviewResult } from "@/lib/types";

type Tab = "chat" | "knowledge" | "recommendations" | "history";

const tabs: Array<{ id: Tab; label: string }> = [
  { id: "chat", label: "Чат" },
  { id: "knowledge", label: "Уровень знаний" },
  { id: "recommendations", label: "Рекомендации" },
  { id: "history", label: "История" },
];

const roleTitles: Record<string, string> = {
  backend: "Backend-разработчик",
  ml_engineer: "ML-инженер",
  llm_engineer: "LLM-инженер",
};

const levelTitles: Record<string, string> = {
  junior: "Junior",
  middle: "Middle",
  senior: "Senior",
};

const verdictTitles: Record<string, string> = {
  correct: "Верно",
  partially_correct: "Частично верно",
  incorrect: "Нужно улучшить",
};

const skillStatusTitles: Record<string, string> = {
  good: "Хорошо",
  need_repeat: "Нужно повторить",
  weak: "Слабая тема",
};

function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 404) return "Интервью не найдено.";
    return error.message;
  }
  return "Не удалось связаться с сервером. Попробуйте ещё раз.";
}

function InterviewLoading() {
  return (
    <main className="min-h-screen bg-canvas px-4 py-8" aria-busy="true">
      <div className="mx-auto max-w-7xl animate-pulse space-y-6" role="status">
        <div className="h-40 rounded-3xl bg-slate-200" />
        <div className="h-16 rounded-2xl bg-slate-200" />
        <div className="mx-auto max-w-4xl space-y-4">
          <div className="h-28 rounded-2xl bg-slate-200" />
          <div className="ml-auto h-24 w-5/6 rounded-2xl bg-slate-200" />
          <div className="h-52 rounded-3xl bg-slate-200" />
        </div>
        <span className="sr-only">Загружаем интервью</span>
      </div>
    </main>
  );
}

function InterviewPageContent() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const interviewId = params.id;
  const [detail, setDetail] = useState<InterviewDetail | null>(null);
  const [result, setResult] = useState<InterviewResult | null>(null);
  const [activeTab, setActiveTab] = useState<Tab>("chat");
  const [draft, setDraft] = useState("");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [finishing, setFinishing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [answerError, setAnswerError] = useState<string | null>(null);

  const loadInterview = useCallback(async () => {
    setError(null);
    try {
      const nextDetail = await apiRequest<InterviewDetail>(`/interviews/${interviewId}`);
      setDetail(nextDetail);
      if (nextDetail.status === "finished") {
        const nextResult = await apiRequest<InterviewResult>(
          `/interviews/${interviewId}/result`,
        );
        setResult(nextResult);
      } else {
        setResult(null);
      }
    } catch (requestError) {
      setError(errorMessage(requestError));
    } finally {
      setLoading(false);
    }
  }, [interviewId]);

  useEffect(() => {
    const timeout = window.setTimeout(() => void loadInterview(), 0);
    return () => window.clearTimeout(timeout);
  }, [loadInterview]);

  const progress = useMemo(() => {
    if (!detail?.total_questions) return 0;
    return Math.round((detail.answered_questions * 100) / detail.total_questions);
  }, [detail]);
  const answeredMaxScore = useMemo(
    () => detail?.answers.reduce((total, answer) => total + answer.max_score, 0) ?? 0,
    [detail],
  );
  const knowledgeGraph = result?.knowledge_graph ?? detail?.knowledge_graph ?? [];

  function handleTabKeyDown(event: KeyboardEvent<HTMLButtonElement>, currentIndex: number) {
    if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
    event.preventDefault();
    const direction = event.key === "ArrowRight" ? 1 : -1;
    const nextIndex = (currentIndex + direction + tabs.length) % tabs.length;
    setActiveTab(tabs[nextIndex].id);
    document.getElementById(`interview-tab-${tabs[nextIndex].id}`)?.focus();
  }

  async function submitAnswer(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!detail?.current_question || !draft.trim() || submitting) return;

    setSubmitting(true);
    setAnswerError(null);
    try {
      await apiRequest(`/interviews/${interviewId}/answers`, {
        method: "POST",
        body: {
          interview_question_id: detail.current_question.interview_question_id,
          answer_text: draft.trim(),
        },
      });
      setDraft("");
      await loadInterview();
    } catch (requestError) {
      if (requestError instanceof ApiError && requestError.status === 409) {
        await loadInterview();
        setAnswerError("Состояние интервью обновилось. Проверьте текущий вопрос.");
      } else {
        setAnswerError(
          `${errorMessage(requestError)} Текст ответа сохранён — можно повторить отправку.`,
        );
      }
    } finally {
      setSubmitting(false);
    }
  }

  async function finishInterview() {
    if (!detail || detail.status === "finished" || finishing) return;
    if (!window.confirm("Завершить интервью досрочно? Неотвеченные вопросы получат 0 баллов.")) {
      return;
    }

    setFinishing(true);
    setAnswerError(null);
    try {
      await apiRequest(`/interviews/${interviewId}/finish`, { method: "POST" });
      await loadInterview();
    } catch (requestError) {
      setAnswerError(errorMessage(requestError));
    } finally {
      setFinishing(false);
    }
  }

  function logout() {
    clearToken();
    router.replace("/login");
  }

  if (loading) return <InterviewLoading />;

  if (error || !detail) {
    return (
      <main className="grid min-h-screen place-items-center px-5">
        <section className="w-full max-w-lg rounded-3xl bg-white p-8 text-center shadow-panel">
          <h1 className="text-2xl font-bold">Не удалось открыть интервью</h1>
          <p className="mt-3 text-slate-600">{error ?? "Интервью недоступно."}</p>
          <div className="mt-6 flex justify-center gap-3">
            <button
              className="rounded-xl bg-brand px-5 py-3 font-semibold text-white"
              onClick={() => {
                setLoading(true);
                void loadInterview();
              }}
              type="button"
            >
              Повторить
            </button>
            <Link className="rounded-xl border border-slate-200 px-5 py-3" href="/dashboard">
              На главную
            </Link>
          </div>
        </section>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-canvas pb-16">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-4 sm:px-6 lg:px-8">
          <Link
            className="rounded font-bold text-brand-dark focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-indigo-200"
            href="/dashboard"
          >
            AI Interviewer
          </Link>
          <div className="flex items-center gap-3 text-sm">
            <Link
              className="rounded text-slate-600 hover:text-ink focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-indigo-200"
              href="/dashboard"
            >
              Dashboard
            </Link>
            <button
              className="rounded text-slate-500 hover:text-ink focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-indigo-200"
              onClick={logout}
              type="button"
            >
              Выйти
            </button>
          </div>
        </div>
      </header>

      <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
        <section className="rounded-3xl bg-ink p-6 text-white shadow-panel sm:p-8">
          <div className="flex flex-wrap items-start justify-between gap-5">
            <div>
              <p className="text-sm font-medium text-indigo-200">
                {roleTitles[detail.role] ?? detail.role} · {levelTitles[detail.level] ?? detail.level}
              </p>
              <h1 className="mt-2 text-2xl font-bold sm:text-3xl">
                Техническое интервью
              </h1>
            </div>
            <span
              className={`rounded-full px-4 py-2 text-sm font-semibold ${
                detail.status === "finished"
                  ? "bg-emerald-400/15 text-emerald-200"
                  : "bg-indigo-400/15 text-indigo-100"
              }`}
            >
              {detail.status === "finished" ? "Завершено" : "В процессе"}
            </span>
          </div>
          <div className="mt-7 grid gap-4 sm:grid-cols-[1fr_auto_auto] sm:items-end">
            <div>
              <div className="flex justify-between text-sm text-slate-300">
                <span>Прогресс</span>
                <span>
                  {detail.answered_questions}/{detail.total_questions}
                </span>
              </div>
              <div
                className="mt-2 h-2 overflow-hidden rounded-full bg-white/10"
                role="progressbar"
                aria-label="Прогресс интервью"
                aria-valuemin={0}
                aria-valuemax={detail.total_questions}
                aria-valuenow={detail.answered_questions}
              >
                <div className="h-full rounded-full bg-indigo-400" style={{ width: `${progress}%` }} />
              </div>
            </div>
            <div className="text-sm text-slate-300">
              Баллы{" "}
              <strong className="ml-1 text-lg text-white">
                {detail.total_score}/{answeredMaxScore}
              </strong>
            </div>
            {result ? (
              <div className="text-sm text-slate-300">
                Результат{" "}
                <strong className="ml-1 text-lg text-white">{result.interview.percentage}%</strong>
              </div>
            ) : null}
          </div>
        </section>

        <nav
          className="mt-6 flex gap-2 overflow-x-auto rounded-2xl bg-white p-2 shadow-sm"
          aria-label="Разделы интервью"
          role="tablist"
        >
          {tabs.map((tab, index) => (
            <button
              className={`whitespace-nowrap rounded-xl px-4 py-3 text-sm font-semibold transition focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-indigo-200 ${
                activeTab === tab.id
                  ? "bg-brand text-white"
                  : "text-slate-600 hover:bg-slate-100"
              }`}
              id={`interview-tab-${tab.id}`}
              role="tab"
              aria-selected={activeTab === tab.id}
              aria-controls={`interview-panel-${tab.id}`}
              tabIndex={activeTab === tab.id ? 0 : -1}
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              onKeyDown={(event) => handleTabKeyDown(event, index)}
              type="button"
            >
              {tab.label}
            </button>
          ))}
        </nav>

        <div className="mt-6">
          {activeTab === "chat" ? (
            <section
              className="mx-auto max-w-4xl space-y-5"
              id="interview-panel-chat"
              role="tabpanel"
              aria-labelledby="interview-tab-chat"
              tabIndex={0}
            >
              {detail.answers.map((answer) => (
                <article className="space-y-3" key={answer.id}>
                  <div className="mr-auto max-w-3xl rounded-2xl rounded-tl-md bg-white p-5 shadow-sm">
                    <p className="text-xs font-semibold uppercase tracking-wide text-brand-dark">
                      Вопрос {answer.order_number} · {answer.skill}
                    </p>
                    <p className="mt-2 leading-7 text-ink">{answer.question_text}</p>
                  </div>
                  <div className="ml-auto max-w-3xl rounded-2xl rounded-tr-md bg-brand p-5 text-white shadow-sm">
                    <p className="text-xs font-semibold uppercase tracking-wide text-indigo-100">
                      Ваш ответ
                    </p>
                    <p className="mt-2 whitespace-pre-wrap break-words leading-7">
                      {answer.answer_text}
                    </p>
                  </div>
                  <div className="mr-auto max-w-3xl rounded-2xl border border-indigo-100 bg-indigo-50 p-5">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <strong className="text-brand-dark">
                        {answer.score}/{answer.max_score} · {verdictTitles[answer.verdict] ?? answer.verdict}
                      </strong>
                      <span className="text-xs text-slate-500">{answer.scoring_provider}</span>
                    </div>
                    <p className="mt-2 text-sm leading-6 text-slate-700">{answer.feedback}</p>
                  </div>
                </article>
              ))}

              {detail.status === "in_progress" && detail.current_question ? (
                <article className="rounded-3xl bg-white p-5 shadow-panel sm:p-7">
                  <p className="text-xs font-semibold uppercase tracking-wide text-brand-dark">
                    Вопрос {detail.current_question.order_number} · {detail.current_question.skill}
                  </p>
                  <h2 className="mt-3 text-xl font-semibold leading-8">
                    {detail.current_question.text}
                  </h2>
                  <form className="mt-6" onSubmit={submitAnswer}>
                    <label className="text-sm font-semibold text-slate-700" htmlFor="answer">
                      Ваш ответ
                    </label>
                    <textarea
                      className="mt-2 min-h-36 w-full resize-y rounded-2xl border border-slate-200 bg-slate-50 p-4 outline-none transition placeholder:text-slate-500 focus:border-brand focus:ring-4 focus:ring-indigo-100 disabled:opacity-60"
                      disabled={submitting}
                      id="answer"
                      onChange={(event) => setDraft(event.target.value)}
                      placeholder="Раскройте основные понятия и приведите пример…"
                      value={draft}
                    />
                    {answerError ? (
                      <p role="alert" className="mt-3 text-sm text-rose-700">
                        {answerError}
                      </p>
                    ) : null}
                    <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
                      <button
                        className="w-full rounded-xl border border-rose-200 px-4 py-3 text-sm font-semibold text-rose-700 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-rose-200 disabled:opacity-50 sm:w-auto"
                        disabled={submitting || finishing}
                        onClick={() => void finishInterview()}
                        type="button"
                      >
                        {finishing ? "Завершаем…" : "Завершить досрочно"}
                      </button>
                      <button
                        className="w-full rounded-xl bg-brand px-6 py-3 font-semibold text-white shadow-sm focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-indigo-200 disabled:cursor-not-allowed disabled:opacity-50 sm:w-auto"
                        disabled={submitting || !draft.trim()}
                        type="submit"
                      >
                        {submitting ? "Отправляем…" : "Отправить ответ"}
                      </button>
                    </div>
                  </form>
                </article>
              ) : (
                <article
                  className="rounded-3xl border border-emerald-200 bg-emerald-50 p-7 text-center"
                  aria-live="polite"
                >
                  <h2 className="text-2xl font-bold text-emerald-900">Интервью завершено</h2>
                  <p className="mt-2 text-emerald-800">
                    Итоговый результат: {result?.interview.percentage ?? 0}%. Откройте вкладки знаний и рекомендаций.
                  </p>
                </article>
              )}
            </section>
          ) : null}

          {activeTab === "knowledge" ? (
            <section
              id="interview-panel-knowledge"
              role="tabpanel"
              aria-labelledby="interview-tab-knowledge"
              tabIndex={0}
            >
              {knowledgeGraph.length === 0 ? (
                <EmptyResultState text="Граф знаний появится после первого ответа." />
              ) : (
                <div className="space-y-8">
                  <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
                    {knowledgeGraph.map((node) => {
                      const score = Math.round(node.score);
                      const confidence = Math.round(node.confidence * 100);
                      return (
                        <article
                          className="rounded-2xl bg-white p-6 shadow-sm"
                          key={`${node.topic}:${node.subtopic}`}
                        >
                          <p className="text-xs font-bold uppercase tracking-wide text-slate-500">
                            {node.topic}
                          </p>
                          <div className="mt-2 flex items-center justify-between gap-3">
                            <h2 className="font-bold">{node.subtopic}</h2>
                            <span className="text-xl font-bold text-brand-dark">{score}%</span>
                          </div>
                          <div
                            className="mt-4 h-2 rounded-full bg-slate-100"
                            role="progressbar"
                            aria-label={`Знание подраздела ${node.subtopic}`}
                            aria-valuemin={0}
                            aria-valuemax={100}
                            aria-valuenow={score}
                          >
                            <div
                              className="h-full rounded-full bg-brand"
                              style={{ width: `${score}%` }}
                            />
                          </div>
                          <p className="mt-4 text-sm text-slate-600">
                            Уверенность: {confidence}% · ответов: {node.evidence_count}
                          </p>
                        </article>
                      );
                    })}
                  </div>

                  {result ? <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
                    {result.skill_scores.map((skill) => (
                    <article className="rounded-2xl bg-white p-6 shadow-sm" key={skill.skill}>
                      <div className="flex items-center justify-between gap-3">
                        <h2 className="font-bold">{skill.skill}</h2>
                        <span className="text-xl font-bold text-brand-dark">{skill.percentage}%</span>
                      </div>
                      <div
                        className="mt-4 h-2 rounded-full bg-slate-100"
                        role="progressbar"
                        aria-label={`Знание темы ${skill.skill}`}
                        aria-valuemin={0}
                        aria-valuemax={100}
                        aria-valuenow={skill.percentage}
                      >
                        <div className="h-full rounded-full bg-brand" style={{ width: `${skill.percentage}%` }} />
                      </div>
                      <p className="mt-4 text-sm font-semibold text-slate-700">
                        {skillStatusTitles[skill.status] ?? skill.status}
                      </p>
                      <p className="mt-2 text-sm leading-6 text-slate-500">
                        {skill.status === "good"
                          ? "Тема раскрыта уверенно. Продолжайте закреплять практикой."
                          : skill.status === "need_repeat"
                            ? "Основы понятны, но отдельные критерии стоит повторить."
                            : "Вернитесь к основам темы и разберите пропущенные критерии."}
                      </p>
                    </article>
                    ))}
                  </div> : null}
                </div>
              )}
            </section>
          ) : null}

          {activeTab === "recommendations" ? (
            <section
              id="interview-panel-recommendations"
              role="tabpanel"
              aria-labelledby="interview-tab-recommendations"
              tabIndex={0}
            >
              {!result ? (
                <EmptyResultState text="Рекомендации появятся после завершения интервью." />
              ) : result.recommendations.length === 0 ? (
                <EmptyResultState text="Все темы освоены на хорошем уровне. Так держать!" />
              ) : (
                <div className="grid gap-5 lg:grid-cols-2">
                  {result.recommendations.map((recommendation) => (
                    <article className="rounded-2xl bg-white p-6 shadow-sm" key={recommendation.skill}>
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <h2 className="text-xl font-bold">{recommendation.skill}</h2>
                        <span
                          className={`rounded-full px-3 py-1 text-xs font-bold uppercase ${
                            recommendation.priority === "high"
                              ? "bg-rose-100 text-rose-700"
                              : "bg-amber-100 text-amber-700"
                          }`}
                        >
                          {recommendation.priority === "high" ? "Высокий приоритет" : "Средний приоритет"}
                        </span>
                      </div>
                      <p className="mt-3 text-sm text-slate-600">Текущий уровень: {recommendation.current_percentage}%</p>
                      <p className="mt-4 leading-7 text-slate-700">{recommendation.reason}</p>
                      <h3 className="mt-5 font-semibold">Что повторить</h3>
                      <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-600">
                        {recommendation.topics_to_learn.map((topic) => <li key={topic}>{topic}</li>)}
                      </ul>
                      <h3 className="mt-5 font-semibold">Практика</h3>
                      <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-600">
                        {recommendation.practice_tasks.map((task) => <li key={task}>{task}</li>)}
                      </ul>
                    </article>
                  ))}
                </div>
              )}
            </section>
          ) : null}

          {activeTab === "history" ? (
            <section
              className="space-y-5"
              id="interview-panel-history"
              role="tabpanel"
              aria-labelledby="interview-tab-history"
              tabIndex={0}
            >
              {detail.answers.length === 0 ? (
                <EmptyResultState text="История появится после первого ответа." />
              ) : (
                detail.answers.map((answer) => (
                  <article className="rounded-2xl bg-white p-6 shadow-sm" key={answer.id}>
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <p className="text-xs font-bold uppercase tracking-wide text-brand-dark">
                          Вопрос {answer.order_number} · {answer.skill}
                        </p>
                        <h2 className="mt-2 text-lg font-semibold">{answer.question_text}</h2>
                      </div>
                      <strong className="rounded-xl bg-indigo-50 px-3 py-2 text-brand-dark">
                        {answer.score}/{answer.max_score} ·{" "}
                        {verdictTitles[answer.verdict] ?? answer.verdict}
                      </strong>
                    </div>
                    <p className="mt-4 break-words rounded-xl bg-slate-50 p-4 text-sm leading-6">
                      {answer.answer_text}
                    </p>
                    <p className="mt-4 text-sm leading-6 text-slate-600">{answer.feedback}</p>
                    <div className="mt-5 grid gap-4 md:grid-cols-2">
                      <CriteriaList title="Раскрыто" items={answer.matched_points} tone="good" />
                      <CriteriaList title="Стоит дополнить" items={answer.missing_points} tone="weak" />
                    </div>
                  </article>
                ))
              )}
            </section>
          ) : null}
        </div>
      </div>
    </main>
  );
}

function EmptyResultState({ text }: { text: string }) {
  return (
    <div className="rounded-3xl border border-dashed border-slate-300 bg-white p-10 text-center text-slate-600">
      {text}
    </div>
  );
}

function CriteriaList({
  title,
  items,
  tone,
}: {
  title: string;
  items: string[];
  tone: "good" | "weak";
}) {
  return (
    <div className={`rounded-xl p-4 ${tone === "good" ? "bg-emerald-50" : "bg-rose-50"}`}>
      <h3 className={`text-sm font-bold ${tone === "good" ? "text-emerald-800" : "text-rose-800"}`}>
        {title}
      </h3>
      {items.length ? (
        <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-600">
          {items.map((item) => <li key={item}>{item}</li>)}
        </ul>
      ) : (
        <p className="mt-2 text-sm text-slate-500">Нет пунктов</p>
      )}
    </div>
  );
}

export default function InterviewPage() {
  return (
    <AuthGuard>
      <InterviewPageContent />
    </AuthGuard>
  );
}
