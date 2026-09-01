import type { AnalyticsProgress, AnalyticsSkill, AnalyticsSummary } from "@/lib/types";

type DashboardStatsProps = {
  summary: AnalyticsSummary;
  skills: AnalyticsSkill[];
  progress: AnalyticsProgress[];
};

type StatCardProps = {
  label: string;
  value: string;
  hint: string;
};

function StatCard({ label, value, hint }: StatCardProps) {
  return (
    <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <p className="text-sm font-medium text-slate-500">{label}</p>
      <p className="mt-2 text-3xl font-semibold tracking-tight text-slate-950">{value}</p>
      <p className="mt-2 text-xs leading-5 text-slate-500">{hint}</p>
    </article>
  );
}

export function DashboardStats({ summary, skills, progress }: DashboardStatsProps) {
  const recentProgress = progress.slice(-6);
  const weakestSkills = [...skills]
    .sort((left, right) => left.average_percentage - right.average_percentage)
    .slice(0, 5);

  return (
    <section aria-labelledby="dashboard-stats-title" className="space-y-5">
      <div className="mb-4 flex items-end justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-blue-600">
            Ваш прогресс
          </p>
          <h2 id="dashboard-stats-title" className="mt-1 text-xl font-semibold text-slate-950">
            Статистика подготовки
          </h2>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard
          label="Завершено интервью"
          value={String(summary.finished_interviews)}
          hint={`Всего создано: ${summary.total_interviews}`}
        />
        <StatCard
          label="Средний результат"
          value={summary.average_percentage === null ? "—" : `${summary.average_percentage}%`}
          hint="По всем завершённым интервью"
        />
        <StatCard
          label="Сильная тема"
          value={summary.strongest_skill ?? "—"}
          hint="Навык с лучшим средним результатом"
        />
        <StatCard
          label="Слабая тема"
          value={summary.weakest_skills[0] ?? "—"}
          hint={
            summary.best_role
              ? `Лучший результат в роли: ${summary.best_role}`
              : "Слабые темы пока не выявлены"
          }
        />
      </div>

      <div className="grid gap-5 lg:grid-cols-[1.2fr_1fr]">
        <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
          <div className="flex items-end justify-between gap-3">
            <div>
              <h3 className="font-semibold text-slate-950">Динамика результатов</h3>
              <p className="mt-1 text-sm text-slate-500">Последние завершённые интервью</p>
            </div>
            <span className="text-xs font-medium text-slate-400">0–100%</span>
          </div>
          {recentProgress.length ? (
            <ol
              className="mt-6 flex h-48 items-end gap-3 border-b border-slate-200 px-1"
              aria-label="Результаты последних интервью"
            >
              {recentProgress.map((item, index) => (
                <li
                  key={item.interview_id}
                  className="flex min-w-0 flex-1 flex-col justify-end gap-2"
                  aria-label={`Интервью ${index + 1}: ${item.percentage}%`}
                >
                  <span className="text-center text-xs font-semibold text-slate-600">
                    {item.percentage}%
                  </span>
                  <span className="flex h-32 items-end" aria-hidden="true">
                    <span
                      className="w-full min-h-1 rounded-t-lg bg-gradient-to-t from-blue-700 to-indigo-400"
                      style={{ height: `${Math.max(item.percentage, 3)}%` }}
                    />
                  </span>
                  <span className="truncate pb-2 text-center text-[0.65rem] uppercase text-slate-400">
                    {item.role.replace("_engineer", "")}
                  </span>
                </li>
              ))}
            </ol>
          ) : (
            <p className="mt-6 rounded-xl bg-slate-50 px-4 py-10 text-center text-sm text-slate-500">
              График появится после первого завершённого интервью.
            </p>
          )}
        </article>

        <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
          <h3 className="font-semibold text-slate-950">Темы для роста</h3>
          <p className="mt-1 text-sm text-slate-500">Сначала показаны самые слабые навыки</p>
          {weakestSkills.length ? (
            <ul className="mt-5 space-y-4">
              {weakestSkills.map((skill) => (
                <li key={skill.skill}>
                  <div className="flex justify-between gap-3 text-sm">
                    <span className="truncate font-medium text-slate-700">{skill.skill}</span>
                    <span className="font-semibold text-slate-950">
                      {skill.average_percentage}%
                    </span>
                  </div>
                  <div
                    className="mt-2 h-2 overflow-hidden rounded-full bg-slate-100"
                    role="progressbar"
                    aria-label={skill.skill}
                    aria-valuemin={0}
                    aria-valuemax={100}
                    aria-valuenow={skill.average_percentage}
                  >
                    <div
                      className="h-full rounded-full bg-blue-600"
                      style={{ width: `${skill.average_percentage}%` }}
                    />
                  </div>
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-6 rounded-xl bg-slate-50 px-4 py-10 text-center text-sm text-slate-500">
              Навыки появятся после первого ответа.
            </p>
          )}
        </article>
      </div>
    </section>
  );
}
