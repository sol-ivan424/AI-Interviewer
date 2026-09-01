"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";

import { AuthShell } from "@/components/AuthShell";
import { ApiError, apiRequest } from "@/lib/api";
import type { User } from "@/lib/types";

type RegisterFormValues = {
  fullName: string;
  email: string;
  password: string;
  passwordConfirmation: string;
};

const fieldClassName =
  "mt-2 w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-ink outline-none transition placeholder:text-slate-500 focus:border-brand focus:ring-4 focus:ring-indigo-100 disabled:cursor-not-allowed disabled:bg-slate-100";

export default function RegisterPage() {
  const router = useRouter();
  const [submitError, setSubmitError] = useState<string | null>(null);
  const {
    register,
    getValues,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<RegisterFormValues>({
    defaultValues: {
      fullName: "",
      email: "",
      password: "",
      passwordConfirmation: "",
    },
  });

  const onSubmit = handleSubmit(async (values) => {
    setSubmitError(null);
    try {
      await apiRequest<User>("/auth/register", {
        method: "POST",
        body: {
          full_name: values.fullName.trim() || null,
          email: values.email.trim(),
          password: values.password,
        },
        auth: false,
      });
      router.replace("/login?registered=1");
    } catch (error) {
      if (error instanceof ApiError && error.status === 409) {
        setSubmitError("Пользователь с таким email уже зарегистрирован.");
        return;
      }
      if (error instanceof ApiError && error.status === 422) {
        setSubmitError("Проверьте введённые данные и попробуйте ещё раз.");
        return;
      }
      setSubmitError("Не удалось зарегистрироваться. Проверьте соединение и повторите попытку.");
    }
  });

  return (
    <AuthShell
      eyebrow="Новый аккаунт"
      title="Начните подготовку"
      description="Создайте аккаунт, чтобы проходить интервью и сохранять результаты."
      footerText="Уже есть аккаунт?"
      footerHref="/login"
      footerLinkText="Войти"
    >
      <form className="space-y-5" onSubmit={onSubmit} noValidate>
        <div>
          <label className="text-sm font-semibold text-slate-700" htmlFor="fullName">
            Имя
          </label>
          <input
            id="fullName"
            autoComplete="name"
            className={fieldClassName}
            disabled={isSubmitting}
            placeholder="Как к вам обращаться"
            aria-invalid={Boolean(errors.fullName)}
            aria-describedby={errors.fullName ? "fullName-error" : undefined}
            {...register("fullName", {
              required: "Введите имя.",
              maxLength: { value: 255, message: "Имя не должно превышать 255 символов." },
            })}
          />
          {errors.fullName && (
            <p id="fullName-error" className="mt-2 text-sm text-red-600">
              {errors.fullName.message}
            </p>
          )}
        </div>

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
            autoComplete="new-password"
            className={fieldClassName}
            disabled={isSubmitting}
            placeholder="Не менее 8 символов"
            aria-invalid={Boolean(errors.password)}
            aria-describedby={errors.password ? "password-error" : "password-hint"}
            {...register("password", {
              required: "Введите пароль.",
              minLength: { value: 8, message: "Пароль должен содержать не менее 8 символов." },
              maxLength: { value: 128, message: "Пароль не должен превышать 128 символов." },
            })}
          />
          {errors.password ? (
            <p id="password-error" className="mt-2 text-sm text-red-600">
              {errors.password.message}
            </p>
          ) : (
            <p id="password-hint" className="mt-2 text-xs text-slate-500">
              От 8 до 128 символов.
            </p>
          )}
        </div>

        <div>
          <label
            className="text-sm font-semibold text-slate-700"
            htmlFor="passwordConfirmation"
          >
            Повторите пароль
          </label>
          <input
            id="passwordConfirmation"
            type="password"
            autoComplete="new-password"
            className={fieldClassName}
            disabled={isSubmitting}
            aria-invalid={Boolean(errors.passwordConfirmation)}
            aria-describedby={
              errors.passwordConfirmation ? "passwordConfirmation-error" : undefined
            }
            {...register("passwordConfirmation", {
              required: "Повторите пароль.",
              validate: (value) => value === getValues("password") || "Пароли не совпадают.",
            })}
          />
          {errors.passwordConfirmation && (
            <p id="passwordConfirmation-error" className="mt-2 text-sm text-red-600">
              {errors.passwordConfirmation.message}
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
          {isSubmitting ? "Создаём аккаунт…" : "Зарегистрироваться"}
        </button>
      </form>
    </AuthShell>
  );
}
