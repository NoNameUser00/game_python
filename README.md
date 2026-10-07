# 🐍 Питонята — обучающая игра

Онлайн-игра для школьников: изучаем Python, алгоритмы и программирование
через решение задач с автопроверкой, XP и прогрессом на карте.

## Структура

```
docs/       — планы и контракты (API.md, CONTENT.md)
backend/    — FastAPI + SQLModel, движок проверки кода в песочнице
frontend/   — React + Vite + CodeMirror (карта, задачи, профиль)
```

## Локальный запуск

### Бэкенд
```bash
cd backend
python3.12 -m venv .venv            # или: uv venv --python 3.12 .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app.main:app --reload --port 8000
```
Сервер: http://127.0.0.1:8000 (Swagger: /docs, проверка: /api/health).

### Фронтенд
```bash
cd frontend
npm install
npm run dev
```
Игра: http://localhost:5173 (Vite проксирует `/api` на порт 8000).

### Тесты
```bash
cd backend && .venv/bin/python -m pytest tests/ -q
```

## Как это работает

- Ученик пишет функцию в редакторе CodeMirror → нажимает «Проверить».
- Код выполняется в **изолированном процессе** с лимитами
  (3 с / 2 с CPU / 256 МБ, stdin закрыт) — см. `backend/app/runner/`.
- Пройдено все тесты → XP, задача отмечена решённой; подсказки уменьшают награду.
- Контент задач — YAML-файлы в `backend/app/content/` (правится без кода).

## Планы

- [ ] Регистрация по почте через отдельный auth-сервис (репозиторий будет предоставлен)
- [ ] Docker-песочница для публичного сервера (`RUNNER_MODE=docker`)
- [ ] Деплой на Oracle Cloud Always Free
- [ ] Новые темы: словари, рекурсия, сортировки, графы
