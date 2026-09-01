"use client";

import type { ReactNode } from "react";
import { useCallback, useEffect, useState } from "react";

import { apiRequest, getToken } from "@/lib/api";
import type { User } from "@/lib/types";

interface AuthGuardProps {
  children: ReactNode;
}

type AuthState = "checking" | "authenticated" | "error";

export function AuthGuard({ children }: AuthGuardProps) {
  const [state, setState] = useState<AuthState>("checking");

  const verifySession = useCallback(async () => {
    setState("checking");

    if (!getToken()) {
      window.location.replace("/login");
      return;
    }

    try {
      await apiRequest<User>("/users/me");
      setState("authenticated");
    } catch {
      if (window.location.pathname !== "/login") {
        setState("error");
      }
    }
  }, []);

  useEffect(() => {
    const timeout = window.setTimeout(() => void verifySession(), 0);
    return () => window.clearTimeout(timeout);
  }, [verifySession]);

  if (state === "checking") {
    return (
      <main className="flex min-h-screen items-center justify-center px-5" aria-busy="true">
        <p className="text-sm font-medium text-slate-600" role="status">
          Проверяем авторизацию…
        </p>
      </main>
    );
  }

  if (state === "error") {
    return (
      <main className="flex min-h-screen items-center justify-center px-5">
        <section className="max-w-md rounded-2xl border border-slate-200 bg-white p-6 text-center shadow-sm">
          <h1 className="text-lg font-semibold text-ink">Не удалось проверить авторизацию</h1>
          <p className="mt-2 text-sm leading-6 text-slate-600">
            Проверьте соединение с API и попробуйте ещё раз.
          </p>
          <button
            type="button"
            onClick={() => void verifySession()}
            className="mt-5 rounded-xl bg-brand px-4 py-2 font-semibold text-white"
          >
            Повторить
          </button>
        </section>
      </main>
    );
  }

  return children;
}
