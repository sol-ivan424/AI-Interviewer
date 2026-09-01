import Link from "next/link";
import type { ReactNode } from "react";

type AuthShellProps = Readonly<{
  eyebrow: string;
  title: string;
  description: string;
  children: ReactNode;
  footerText: string;
  footerHref: string;
  footerLinkText: string;
}>;

export function AuthShell({
  eyebrow,
  title,
  description,
  children,
  footerText,
  footerHref,
  footerLinkText,
}: AuthShellProps) {
  return (
    <main className="relative isolate flex min-h-screen items-center overflow-hidden px-5 py-12 sm:px-8">
      <div
        aria-hidden="true"
        className="absolute inset-x-0 top-0 -z-10 h-96 bg-gradient-to-b from-indigo-100 via-violet-50 to-transparent"
      />
      <section className="mx-auto w-full max-w-md rounded-3xl border border-white/80 bg-white/95 p-7 shadow-panel backdrop-blur sm:p-10">
        <Link
          href="/"
          className="inline-flex rounded-full bg-indigo-50 px-4 py-2 text-sm font-semibold text-brand-dark transition hover:bg-indigo-100 focus:outline-none focus:ring-2 focus:ring-brand focus:ring-offset-2"
        >
          AI Interviewer
        </Link>
        <p className="mt-8 text-sm font-semibold uppercase tracking-[0.16em] text-brand-dark">
          {eyebrow}
        </p>
        <h1 className="mt-3 text-3xl font-bold tracking-tight text-ink">{title}</h1>
        <p className="mt-3 text-sm leading-6 text-slate-600">{description}</p>

        <div className="mt-8">{children}</div>

        <p className="mt-7 text-center text-sm text-slate-600">
          {footerText}{" "}
          <Link
            href={footerHref}
            className="font-semibold text-brand-dark underline-offset-4 hover:underline focus:outline-none focus:ring-2 focus:ring-brand focus:ring-offset-2"
          >
            {footerLinkText}
          </Link>
        </p>
      </section>
    </main>
  );
}

