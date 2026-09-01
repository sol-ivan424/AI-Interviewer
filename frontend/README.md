# AI Interviewer frontend

Frontend приложения на Next.js App Router, TypeScript и Tailwind CSS.

## Локальный запуск

Требуется Node.js 22.13+ и pnpm через Corepack.

```bash
corepack enable
pnpm install
pnpm run dev
```

Приложение будет доступно на `http://localhost:3000`.

## Проверки

```bash
pnpm run lint
pnpm run typecheck
pnpm run build
```

Для обращения к API задайте `NEXT_PUBLIC_API_URL`. Значение для локального запуска по умолчанию будет определено корневой конфигурацией окружения проекта.
