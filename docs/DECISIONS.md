# Принятые решения (без согласования с пользователем)

> Журнал решений, принятых мной самостоятельно (в т.ч. установки бесплатного ПО).
> Пользователь просил: перечислять их в следующем диалоге. Дата: 2026-10-07.

## Установлено (всё бесплатное)

| Что | Зачем | Как установлено |
|---|---|---|
| Python 3.12.15 | системный Python 3.8 устарел, FastAPI/SQLModel требуют современный | `uv python install 3.12` (утилита `uv` уже стояла в системе) |
| venv `backend/.venv` | изоляция зависимостей бэкенда | `uv venv --python 3.12 .venv` |
| pip: fastapi, uvicorn[standard], sqlmodel, pyyaml, pyjwt, email-validator, httpx, pytest | API, БД, JWT, YAML, тесты | `uv pip install -r backend/requirements.txt` |
| pip: psycopg[binary] | драйвер PostgreSQL для прод-БД (в compose) | там же |
| npm: react, react-router-dom, vite, @uiw/react-codemirror, @codemirror/lang-python, @uiw/codemirror-themes, react-markdown | фронтенд игры | делает субагент в `frontend/` (npm create vite) |
| Docker-образы: python:3.12-slim, node:20-slim, nginx:1.27-alpine, postgres:16-alpine | локальный «продакшн»-подобный запуск `docker compose up` | образы тянутся при сборке |

## Решения по фронтенду (приняты субагентом при сборке)

13. **Vite 6.x** (не 8): Vite 8 требует Node 20.19+, в системе Node 20.14.0 — нативные биндинги `@rolldown/*` не ставились. Связка: vite@6 + @vitejs/plugin-react@4.
14. **React 19, react-router-dom 7, TypeScript 6** — как поставил шаблон create-vite (условие ≥18 выполнено).
15. **Тема редактора** — Dracula собрана вручную через `createTheme` (`@uiw/codemirror-themes` не экспортирует готовых тем).
16. **Линтер oxlint не работает** на Node 20.14 (тот же нативный биндинг) — на сборку не влияет; при обновлении Node подключить ESLint.
17. **Проверка в браузере (e2e вручную)**: регистрация → карта (6 тем/12 задач) → задача → ввод кода → «Проверить» → 🎁 +15 XP, 3/3 теста ✅ → подсказка → профиль (15/100 XP) — всё зелёное, ошибок в консоли нет.

## Решения по архитектуре

1. **Стек**: FastAPI + SQLModel (backend), React + Vite + TS (frontend) — выбраны пользователем/согласованы.
2. **БД**: локально SQLite (`backend/game.db`), в docker-compose — PostgreSQL 16. Код не зависит от БД (`DATABASE_URL`).
3. **Auth**: временная самостоятельная регистрация (email+пароль, JWT PyJWT, 7 дней) **до** подключения присланного auth-сервиса — замена в одном месте (`app/security.py` + `app/api/auth.py`).
4. **Хеши паролей**: PBKDF2-SHA256, 120 000 итераций, соль — только стандартная библиотека (без bcrypt-зависимостей).
5. **JWT_SECRET**: dev-значение `dev-secret-change-me` — **обязательно заменить** через env при деплое.
6. **Песочница**: локально — subprocess с rlimits (CPU 2с, RAM 256 МБ, таймаут 3 с, stdin закрыт); на публичном сервере — Docker (`RUNNER_MODE=docker`, будет реализован при деплое). Сети в песочнице пока НЕ отключаются — только локально.
7. **Контент**: YAML-файлы в `backend/app/content/`, загрузка в БД при старте (upsert по slug) — правка заданий без изменения кода.
8. **XP**: 100 XP = уровень; подсказка уменьшает награду вдвое; повторное решение не даёт XP.
9. **Название-заглушка «Питонята»** (константа `APP_NAME` во фронтенде) — подлежит замене.
10. **Коммиты**: делаю сам от имени `teacher <teacher@local>` (имя/почта GitHub не настроены).
11. **Docker nginx**: SPA-роутинг + прокси `/api` + rate-limit 10 запросов/мин на отправку кода.
12. **Вдохновение**: статья Хабр «35 образовательных игр» + CodeCombat (подземелье/уровни), CheckiO (карта), WarriorJS (данж) — варианты дизайна в `docs/design/`.
