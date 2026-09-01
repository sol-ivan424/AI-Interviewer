"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";

import { AuthShell } from "@/components/AuthShell";
import { ApiError, apiRequest, setToken } from "@/lib/api";
import type { TokenResponse } from "@/lib/types";

type LoginFormValues = {
  email: string;
  password: string;
};

const fieldClassName =
  "mt-2 w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-ink outline-none transition placeholder:text-slate-500 focus:border-brand focus:ring-4 focus:ring-indigo-100 disabled:cursor-not-allowed disabled:bg-slate-100";

export default function LoginPage() {
  const router = useRouter();
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [registered, setRegistered] = useState(false);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginFormValues>({ defaultValues: { email: "", password: "" } });

  useEffect(() => {
    const timeout = window.setTimeout(() => {
      setRegistered(new URLSearchParams(window.location.search).get("registered") === "1");
    }, 0);
    return () => window.clearTimeout(timeout);
  }, []);

  const onSubmit = handleSubmit(async (values) => {
    setSubmitError(null);
    try {
      const token = await apiRequest<TokenResponse>("/auth/login", {
        method: "POST",
        body: { email: values.email.trim(), password: values.password },
        auth: false,
      });
      setToken(token.access_token);
      router.replace("/dashboard");
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        setSubmitError("Неверный email или пароль.");
        return;
      }
      if (error instanceof ApiError && error.status === 422) {
        setSubmitError("Проверьте email и пароль.");
        return;
      }
      setSubmitError("Не удалось войти. Проверьте соединение и повторите попытку.");
    }
  });

  return (
    <AuthShell
      eyebrow="Вход"
      title="С возвращением"
      description="Войдите, чтобы продолжить интервью и посмотреть свой прогресс."
      footerText="Ещё нет аккаунта?"
      footerHref="/register"
      footerLinkText="Зарегистрироваться"
    >
      {registered && (
        <p role="status" className="mb-5 rounded-xl bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
          Аккаунт создан. Теперь войдите с указанными данными.
        </p>
      )}

      <form className="space-y-5" onSubmit={onSubmit} noValidate>
        <div>
          <label className="text-sm font-semibold text-slate-700" htmlFor="email">
            Email
          </label>
          <input
            id="email"
            type="email"
            autoComplete="email"
            className={fieldClassName}
            disabled={isSubmitting}
            placeholder="name@example.com"
            aria-invalid={Boolean(errors.email)}
            aria-describedby={errors.email ? "email-error" : undefined}
            {...register("email", {
              required: "Введите email.",
              pattern: {
                value: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
                message: "Введите корректный email.",
              },
            })}
          />
          {errors.email && (
            <p id="email-error" className="mt-2 text-sm text-red-600">
              {errors.email.message}
            </p>
          )}
        </div>

        <div>
          <label className="text-sm font-semibold text-slate-700" htmlFor="password">
            Пароль
          </label>
          <input
            id="password"
            type="password"
            autoComplete="current-password"
            className={fieldClassName}
            disabled={isSubmitting}
            aria-invalid={Boolean(errors.password)}
            aria-describedby={errors.password ? "password-error" : undefined}
            {...register("password", {
              required: "Введите пароль.",
              maxLength: { value: 128, message: "Пароль не должен превышать 128 символов." },
            })}
          />
          {errors.password && (
            <p id="password-error" className="mt-2 text-sm text-red-600">
              {errors.password.message}
            </p>
          )}
        </div>

        {submitError && (
          <p role="alert" className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">
            {submitError}
          </p>
        )}

        <button
          type="submit"
          disabled={isSubmitting}
          className="w-full rounded-xl bg-brand px-5 py-3 font-semibold text-white shadow-sm transition hover:bg-brand-dark focus:outline-none focus:ring-2 focus:ring-brand focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {isSubmitting ? "Входим…" : "Войти"}
        </button>
      </form>
    </AuthShell>
  );
}
