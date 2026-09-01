"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";

import { AuthGuard } from "@/components/AuthGuard";
import { DashboardInterviewList } from "@/components/DashboardInterviewList";
import { DashboardInterviewStarter } from "@/components/DashboardInterviewStarter";
import { DashboardStats } from "@/components/DashboardStats";
import { apiRequest, clearToken } from "@/lib/api";
import type {
  AnalyticsSummary,
  AnalyticsProgress,
  AnalyticsSkill,
  InterviewCreateResponse,
  InterviewListItem,
  RoleOption,
  User,
} from "@/lib/types";

type DashboardData = {
  user: User;
  roles: RoleOption[];
  summary: AnalyticsSummary;
  interviews: InterviewListItem[];
  skills: AnalyticsSkill[];
  progress: AnalyticsProgress[];
};

function errorMessage(error: unknown, fallback: string): string {
  return error instanceof Error && error.message ? error.message : fallback;
}

function DashboardLoading() {
  return (
    <main className="min-h-screen bg-slate-50 px-4 py-8 sm:px-6 lg:px-8" aria-busy="true">
      <div className="mx-auto max-w-6xl animate-pulse space-y-8">
        <div className="h-24 rounded-3xl bg-slate-200" />
        <div className="h-80 rounded-3xl bg-slate-200" />
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {[0, 1, 2, 3].map((item) => (
            <div key={item} className="h-36 rounded-2xl bg-slate-200" />
          ))}
        </div>
      </div>
      <span className="sr-only">Загрузка dashboard</span>
    </main>
  );
}

function DashboardPageContent() {
  const router = useRouter();
  const [data, setData] = useState<DashboardData | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedRole, setSelectedRole] = useState("");
  const [selectedLevel, setSelectedLevel] = useState("");
  const [isStarting, setIsStarting] = useState(false);
  const [startError, setStartError] = useState<string | null>(null);

  const loadDashboard = useCallback(async () => {
    setIsLoading(true);
    setLoadError(null);

    try {
      const [user, roles, summary, interviews, skills, progress] = await Promise.all([
        apiRequest<User>("/users/me"),
        apiRequest<RoleOption[]>("/roles"),
        apiRequest<AnalyticsSummary>("/analytics/summary"),
        apiRequest<InterviewListItem[]>("/interviews"),
        apiRequest<AnalyticsSkill[]>("/analytics/skills"),
        apiRequest<AnalyticsProgress[]>("/analytics/progress"),
      ]);
      setData({ user, roles, summary, interviews, skills, progress });

      const firstRole = roles[0];
      setSelectedRole((current) => current || firstRole?.slug || "");
      setSelectedLevel((current) => current || firstRole?.levels[0] || "");
    } catch (error) {
      setLoadError(errorMessage(error, "Не удалось загрузить dashboard."));
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    const timeout = window.setTimeout(() => void loadDashboard(), 0);
    return () => window.clearTimeout(timeout);
  }, [loadDashboard]);

  function handleRoleChange(roleSlug: string) {
    const role = data?.roles.find((item) => item.slug === roleSlug);
    setSelectedRole(roleSlug);
    setSelectedLevel(role?.levels[0] ?? "");
    setStartError(null);
  }

  async function handleStartInterview(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedRole || !selectedLevel || isStarting) return;

    setIsStarting(true);
    setStartError(null);
    try {
      const interview = await apiRequest<InterviewCreateResponse>("/interviews", {
        method: "POST",
        body: { role: selectedRole, level: selectedLevel },
      });
      router.push(`/interviews/${interview.id}`);
    } catch (error) {
      setStartError(errorMessage(error, "Не удалось начать интервью. Попробуйте ещё раз."));
      setIsStarting(false);
    }
  }

  if (isLoading) return <DashboardLoading />;

  if (loadError || !data) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-slate-50 px-4">
        <section className="w-full max-w-md rounded-3xl border border-red-100 bg-white p-8 text-center shadow-sm">
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-red-600">
            Ошибка загрузки
          </p>
          <h1 className="mt-3 text-2xl font-semibold text-slate-950">Dashboard недоступен</h1>
          <p role="alert" className="mt-3 text-sm leading-6 text-slate-600">
            {loadError ?? "Не удалось получить данные."}
          </p>
          <button
            type="button"
            onClick={() => void loadDashboard()}
            className="mt-6 rounded-xl bg-slate-950 px-5 py-3 text-sm font-semibold text-white hover:bg-slate-800 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-slate-300"
          >
            Повторить
          </button>
        </section>
      </main>
    );
  }

  const firstName = data.user.full_name?.trim().split(/\s+/)[0] || "кандидат";
  const interviewStarter =
    data.roles.length > 0 ? (
      <DashboardInterviewStarter
        roles={data.roles}
        selectedRole={selectedRole}
        selectedLevel={selectedLevel}
        isStarting={isStarting}
        error={startError}
        onRoleChange={handleRoleChange}
        onLevelChange={(level) => {
          setSelectedLevel(level);
          setStartError(null);
        }}
        onSubmit={handleStartInterview}
      />
    ) : (
      <section className="rounded-3xl border border-amber-200 bg-amber-50 p-6">
        <h2 className="font-semibold text-amber-950">Роли пока недоступны</h2>
        <p className="mt-2 text-sm text-amber-800">
          Обновите страницу позже или повторите загрузку данных.
        </p>
        <button
          type="button"
          onClick={() => void loadDashboard()}
          className="mt-4 rounded-xl bg-amber-900 px-4 py-2 text-sm font-semibold text-white focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-amber-300"
        >
          Повторить
        </button>
      </section>
    );

  return (
    <main className="min-h-screen bg-slate-50 px-4 py-8 text-slate-950 sm:px-6 lg:px-8 lg:py-12">
      <div className="mx-auto max-w-6xl space-y-10">
        <header className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-sm font-medium text-blue-700">AI Interviewer</p>
            <h1 className="mt-2 text-3xl font-semibold tracking-tight sm:text-4xl">
              Привет, {firstName}!
            </h1>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600 sm:text-base">
              Выберите специализацию и уровень — мы соберём интервью и покажем, что уже получается
              хорошо, а что стоит повторить.
            </p>
          </div>
          <div className="flex min-w-0 items-center gap-3 text-sm">
            <span className="hidden max-w-64 truncate text-slate-500 sm:inline">
              {data.user.email}
            </span>
            <button
              className="rounded-lg border border-slate-200 px-3 py-2 font-medium text-slate-600 hover:bg-white focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-slate-300"
              onClick={() => {
                clearToken();
                router.replace("/login");
              }}
              type="button"
            >
              Выйти
            </button>
          </div>
        </header>

        {data.summary.finished_interviews === 0 ? interviewStarter : null}
        <DashboardStats summary={data.summary} skills={data.skills} progress={data.progress} />
        {data.summary.finished_interviews > 0 ? interviewStarter : null}
        <DashboardInterviewList interviews={data.interviews} />
      </div>
    </main>
  );
}

export default function DashboardPage() {
  return (
    <AuthGuard>
      <DashboardPageContent />
    </AuthGuard>
  );
}
