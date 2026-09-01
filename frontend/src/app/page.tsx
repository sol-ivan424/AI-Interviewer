const capabilities = [
  "Интервью по выбранной роли и уровню",
  "Оценка ответов по техническим критериям",
  "Персональные рекомендации по темам",
];

export default function HomePage() {
  return (
    <main className="relative isolate flex min-h-screen items-center overflow-hidden px-5 py-16 sm:px-8">
      <div
        aria-hidden="true"
        className="absolute inset-x-0 top-0 -z-10 h-96 bg-gradient-to-b from-indigo-100 via-violet-50 to-transparent"
      />
      <section className="mx-auto w-full max-w-5xl overflow-hidden rounded-3xl border border-white/80 bg-white/90 shadow-panel backdrop-blur">
        <div className="grid gap-12 p-8 sm:p-12 lg:grid-cols-[1.35fr_0.65fr] lg:p-16">
          <div>
            <p className="mb-5 inline-flex rounded-full bg-indigo-50 px-4 py-2 text-sm font-semibold text-brand-dark">
              AI Interviewer
            </p>
            <h1 className="max-w-2xl text-4xl font-bold tracking-tight text-ink sm:text-6xl">
              Подготовка к интервью с понятной обратной связью
            </h1>
            <p className="mt-6 max-w-xl text-lg leading-8 text-slate-600">
              Пройдите структурированное техническое интервью, оцените сильные стороны и получите план для дальнейшей подготовки.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link className="rounded-xl bg-brand px-5 py-3 font-semibold text-white shadow-sm" href="/register">
                Начать подготовку
              </Link>
              <Link className="rounded-xl border border-slate-200 bg-white px-5 py-3 font-medium text-slate-600" href="/login">
                Войти
              </Link>
            </div>
          </div>

          <aside className="rounded-2xl bg-ink p-7 text-white">
            <h2 className="text-lg font-semibold">Что будет доступно</h2>
            <ul className="mt-6 space-y-5">
              {capabilities.map((capability, index) => (
                <li key={capability} className="flex gap-4 text-sm leading-6 text-slate-200">
                  <span className="flex size-7 shrink-0 items-center justify-center rounded-full bg-white/10 font-semibold text-indigo-200">
                    {index + 1}
                  </span>
                  <span>{capability}</span>
                </li>
              ))}
            </ul>
          </aside>
        </div>
      </section>
    </main>
  );
}
import Link from "next/link";
