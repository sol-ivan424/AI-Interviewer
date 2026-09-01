import type { FormEvent } from "react";

import type { RoleOption } from "@/lib/types";

type DashboardInterviewStarterProps = {
  roles: RoleOption[];
  selectedRole: string;
  selectedLevel: string;
  isStarting: boolean;
  error: string | null;
  onRoleChange: (role: string) => void;
  onLevelChange: (level: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
};

const levelLabels: Record<string, string> = {
  junior: "Junior",
  middle: "Middle",
  senior: "Senior",
};

export function DashboardInterviewStarter({
  roles,
  selectedRole,
  selectedLevel,
  isStarting,
  error,
  onRoleChange,
  onLevelChange,
  onSubmit,
}: DashboardInterviewStarterProps) {
  const selectedRoleOption = roles.find((role) => role.slug === selectedRole);
  const levels = selectedRoleOption?.levels ?? [];

  return (
    <section
      aria-labelledby="start-interview-title"
      className="overflow-hidden rounded-3xl border border-blue-100 bg-gradient-to-br from-blue-600 via-blue-700 to-indigo-800 text-white shadow-xl shadow-blue-900/10"
    >
      <div className="grid gap-8 p-6 sm:p-8 lg:grid-cols-[1fr_1.15fr] lg:p-10">
        <div>
          <span className="inline-flex rounded-full bg-white/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-blue-100">
            Новая тренировка
          </span>
          <h2 id="start-interview-title" className="mt-4 text-3xl font-semibold tracking-tight">
            Проверьте знания в формате технического интервью
          </h2>
          <p className="mt-4 max-w-xl text-sm leading-6 text-blue-100 sm:text-base">
            Пять вопросов, мгновенная оценка каждого ответа и персональные рекомендации после
            завершения.
          </p>
        </div>

        <form onSubmit={onSubmit} className="rounded-2xl bg-white p-5 text-slate-950 shadow-lg sm:p-6">
          <fieldset disabled={isStarting} className="space-y-5 disabled:opacity-70">
            <div>
              <label htmlFor="interview-role" className="text-sm font-semibold text-slate-800">
                Роль
              </label>
              <select
                id="interview-role"
                value={selectedRole}
                onChange={(event) => onRoleChange(event.target.value)}
                className="mt-2 w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm outline-none transition focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
              >
                {roles.map((role) => (
                  <option key={role.slug} value={role.slug}>
                    {role.title}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label htmlFor="interview-level" className="text-sm font-semibold text-slate-800">
                Уровень
              </label>
              <select
                id="interview-level"
                value={selectedLevel}
                onChange={(event) => onLevelChange(event.target.value)}
                className="mt-2 w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm outline-none transition focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
              >
                {levels.map((level) => (
                  <option key={level} value={level}>
                    {levelLabels[level] ?? level}
                  </option>
                ))}
              </select>
            </div>

            {error ? (
              <p role="alert" className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">
                {error}
              </p>
            ) : null}

            <button
              type="submit"
              disabled={!selectedRole || !selectedLevel || isStarting}
              className="flex w-full items-center justify-center rounded-xl bg-slate-950 px-5 py-3 text-sm font-semibold text-white transition hover:bg-slate-800 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-slate-300 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isStarting ? "Создаём интервью…" : "Начать интервью"}
            </button>
          </fieldset>
        </form>
      </div>
    </section>
  );
}
