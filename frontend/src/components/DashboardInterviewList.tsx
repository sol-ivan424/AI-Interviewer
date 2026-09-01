import Link from "next/link";

import type { InterviewListItem } from "@/lib/types";

type DashboardInterviewListProps = {
  interviews: InterviewListItem[];
};

const roleLabels: Record<string, string> = {
  backend: "Backend-разработчик",
  ml_engineer: "ML-инженер",
  llm_engineer: "LLM-инженер",
};

const levelLabels: Record<string, string> = {
  junior: "Junior",
  middle: "Middle",
  senior: "Senior",
};

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("ru-RU", {
    day: "numeric",
    month: "short",
    year: "numeric",
  }).format(new Date(value));
}

export function DashboardInterviewList({ interviews }: DashboardInterviewListProps) {
  return (
    <section aria-labelledby="recent-interviews-title" className="rounded-3xl bg-slate-950 p-6 text-white">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-blue-300">История</p>
          <h2 id="recent-interviews-title" className="mt-1 text-xl font-semibold">
            Последние интервью
          </h2>
        </div>
        {interviews.length > 0 ? (
          <span className="text-sm text-slate-400">Показано до 5 последних</span>
        ) : null}
      </div>

      {interviews.length === 0 ? (
        <div className="mt-6 rounded-2xl border border-dashed border-slate-700 p-6 text-center">
          <p className="font-medium">История пока пуста</p>
          <p className="mt-2 text-sm leading-6 text-slate-400">
            Выберите роль и уровень выше, чтобы начать первое тренировочное интервью.
          </p>
        </div>
      ) : (
        <ul className="mt-5 divide-y divide-slate-800">
          {interviews.slice(0, 5).map((interview) => (
            <li key={interview.id}>
              <Link
                href={`/interviews/${interview.id}`}
                className="group flex flex-col gap-3 py-4 outline-none transition hover:text-blue-200 focus-visible:rounded-xl focus-visible:ring-2 focus-visible:ring-blue-400 sm:flex-row sm:items-center sm:justify-between"
              >
                <div>
                  <p className="font-medium">
                    {roleLabels[interview.role] ?? interview.role} ·{" "}
                    {levelLabels[interview.level] ?? interview.level}
                  </p>
                  <p className="mt-1 text-sm text-slate-400">{formatDate(interview.created_at)}</p>
                </div>
                <div className="flex items-center gap-3">
                  <span
                    className={`rounded-full px-3 py-1 text-xs font-semibold ${
                      interview.status === "finished"
                        ? "bg-emerald-400/15 text-emerald-300"
                        : "bg-amber-400/15 text-amber-200"
                    }`}
                  >
                    {interview.status === "finished" ? "Завершено" : "В процессе"}
                  </span>
                  <span className="min-w-12 text-right text-lg font-semibold">
                    {interview.percentage}%
                  </span>
                  <span aria-hidden="true" className="text-slate-500 transition group-hover:translate-x-1">
                    →
                  </span>
                </div>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
