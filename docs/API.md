# Контракт API (v1)

Базовый путь: `/api`. Все ответы — JSON, кодировка UTF-8.
Аутентификация: заголовок `Authorization: Bearer <access_token>` (JWT, срок 7 дней).

Локальная разработка: фронтенд (Vite, порт 5173) проксирует `/api` → `http://127.0.0.1:8000`.

Ошибки: HTTP 4xx/5xx с телом `{"detail": "<человеческое сообщение по-русски>"}`.

---

## Общие типы

```jsonc
// User
{
  "id": 1,
  "email": "vasya@school.ru",
  "username": "Вася",
  "xp": 120,
  "level": 2,          // level = xp // 100 + 1
  "created_at": "2026-10-07T12:00:00"
}
```

## Эндпоинты

### POST /api/auth/register
Запрос:
```json
{"email": "vasya@school.ru", "username": "Вася", "password": "123456"}
```
- `email` — валидный email, уникален;
- `password` — минимум 6 символов;
- `username` — 1–30 символов.

Ответ `200`:
```json
{"access_token": "<jwt>", "token_type": "bearer", "user": { ...User }}
```
Ошибки: `409` «Пользователь с таким email уже существует», `422` при невалидном теле.

### POST /api/auth/login
Запрос: `{"email": "...", "password": "..."}`.
Ответ `200` — как register. Ошибка `401` «Неверный email или пароль».

### GET /api/me
Заголовок авторизации. Ответ `200`: `User`. Ошибки: `401`.

### GET /api/topics
Авторизация обязательна. Ответ `200` — дерево контента с прогрессом:
```jsonc
[
  {
    "id": 1, "slug": "basics", "title": "Основы Python", "icon": "🐍", "order": 1,
    "lessons": [
      {
        "id": 1, "slug": "vars", "title": "Переменные", "order": 1,
        "tasks": [
          {"id": 1, "title": "Приветствие", "difficulty": 1, "completed": false}
        ]
      }
    ]
  }
]
```
`difficulty` — 1..3. `completed` — решена ли задача текущим пользователем.

### GET /api/tasks/{id}
Авторизация. Ответ `200`:
```jsonc
{
  "id": 1, "topic_id": 1, "lesson_id": 1,
  "title": "Приветствие",
  "prompt_md": "Напиши функцию `hello(name)`, ...",   // Markdown
  "starter_code": "def hello(name):\n    # твой код\n    pass",
  "difficulty": 1,
  "xp_reward": 20,
  "hints": ["Подсказка 1", "Подсказка 2"],           // подсказки отдаются только через POST hint? (см. ниже)
  "function": "hello",                                 // имя вызываемой функции
  "completed": false,
  "attempts": 3,                                       // сколько сабмитов сделано
  "hints_used": 0
}
```
> ⚠️ Поле `hints` содержит тексты подсказок — фронтенд показывает их ТОЛЬКО по кнопке
> «Подсказка» через `POST /api/tasks/{id}/hint` (который возвращает текст и увеличивает `hints_used`).
> Для простоты v1 поле `hints` в GET /api/tasks/{id} можно НЕ отдавать вовсе (фронт его не использует).

Ошибки: `404` «Задача не найдена», `401`.

### POST /api/tasks/{id}/hint
Авторизация. Ответ:
```json
{"index": 1, "hint": "Подсказка 1", "hints_used": 1}
```
Если подсказки кончились: `400` «Подсказки закончились».
Эффект: `hints_used` растёт, зачтённая задача даёт **половину** XP.

### POST /api/tasks/{id}/submit
Авторизация. Запрос:
```json
{"code": "def hello(name):\n    return f'Привет, {name}!'"}
```
Ответ `200`:
```jsonc
{
  "status": "accepted",          // "accepted" | "failed" | "error"
  "xp_gained": 20,               // 0, если уже решено или не принято; иначе xp_reward (половина, если были подсказки)
  "completed": true,             // решена ли задача ПОСЛЕ этой попытки
  "tests": [
    {"name": "тест 1: hello('Мир')", "passed": true,  "message": null},
    {"name": "тест 2: hello('Python')", "passed": false, "message": "ожидалось 'Привет, Python!', получено 'Привет!'"}
  ],
  "message": null                // при status="error": дружелюбная причина (например "Ошибка выполнения: SyntaxError ...")
}
```
Семантика статусов:
- `accepted` — все тесты прошли;
- `failed` — тесты запускались, но хотя бы один не прошёл (или время/память вышли);
- `error` — код не скомпилировался / упал ДО запуска тестов (SyntaxError и т.п.) — `tests` пустой `[]`.

Ошибки: `404`, `401`. Тело валидируется: `code` — непустая строка ≤ 20000 символов.

### GET /api/me/progress
Авторизация. Ответ:
```jsonc
{
  "xp": 120, "level": 2,
  "completed_tasks": [1, 4],     // id решённых задач
  "submissions": 15,             // всего отправок кода
  "hints_used": 2
}
```

### GET /api/health
Без авторизации. `{"status": "ok"}`.

---

## Форматы контента (для бэкенда и наполнения)

См. `docs/CONTENT.md`.
