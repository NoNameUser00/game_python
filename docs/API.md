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
  "email": "teacher@school.ru",  // null у учеников — они регистрируются по коду класса
  "username": "Вася",
  "xp": 120,
  "level": 2,          // level = xp // 100 + 1
  "role": "teacher",   // "teacher" | "pupil"
  "class_name": null,  // "7А" у учеников, иначе null
  "created_at": "2026-10-07T12:00:00"
}
```

## Эндпоинты

### POST /api/auth/register — регистрация учителя (по email)
Запрос:
```json
{"email": "teacher@school.ru", "username": "Иван Петрович", "password": "123456"}
```
- `email` — валидный email, уникален;
- `password` — минимум 6 символов;
- `username` — 1–30 символов.
Создаёт пользователя с `role = "teacher"` и отправляет письмо с ссылкой подтверждения почты (в dev — в outbox-файл `backend/outbox.log`, см. `docs/DECISIONS.md` №28).

Ответ `200`:
```json
{"access_token": "<jwt>", "token_type": "bearer", "user": { ...User }}
```
Ошибки: `409` «Пользователь с таким email уже существует», `422` при невалидном теле.

### POST /api/auth/register-class — регистрация ученика (по коду класса, без почты)
Запрос:
```json
{"code": "44FPYA", "username": "Коля", "password": "123456"}
```
- `code` — 6-значный код класса (регистр не важен), выдаёт учитель;
- `username` — 1–30 символов, уникален **в пределах класса**;
- `email` не нужен (приватность детей) — создаётся `role = "pupil"` с `email = null` (внутри для fastapi-users хранится синтетический адрес, наружу он не отдаётся и письма на него не уходят).

Ответ `200` — как register (`user.class_name` = название класса).
Ошибки: `400` «Неверный код класса», `409` «В этом классе уже есть ученик …», `422`.

### POST /api/auth/login
Запрос: `{"login": "...", "password": "..."}`.
`login` — email (учитель) или username (ученик).
Ответ `200` — как register. Ошибка `401` «Неверный email/имя или пароль».
Если включён `REQUIRE_EMAIL_VERIFICATION=1` (на сервере с SMTP): `403` «Почта не подтверждена — открой ссылку из письма».

### POST /api/auth/forgot-password — «забыли пароль» (fastapi-users)
Запрос: `{"email": "teacher@school.ru"}`.
Ответ **всегда `202`** (даже для несуществующей почты — не раскрываем список учётов); письмо со ссылкой `/reset-password?token=…` уходит только для реально зарегистрированных адресов (dev — outbox-файл).

### POST /api/auth/reset-password — новый пароль по ссылке из письма
Запрос: `{"token": "<из ссылки>", "password": "<новый, ≥6>"}`.
Ответ `200`. Ошибки: `400` `RESET_PASSWORD_BAD_TOKEN` (ссылка недействительна/устарела/уже использована), `400` `RESET_PASSWORD_INVALID_PASSWORD`. После успеха отправляется письмо-уведомление «пароль изменён».

### POST /api/auth/request-verify-token — выслать ссылку подтверждения почты
Запрос: `{"email": "..."}`. Ответ `202` (та же маскировка, что у forgot-password). Уже подтверждённой почте — `400` `VERIFY_USER_ALREADY_VERIFIED`.

### POST /api/auth/verify — подтвердить почту по ссылке
Запрос: `{"token": "<из ссылки>"}`.
Ответ `200`: `UserRead` — `{id, email, username, role, xp, is_active, is_superuser, is_verified, ...}`.
Ошибки: `400` `VERIFY_USER_BAD_TOKEN`, `400` `VERIFY_USER_ALREADY_VERIFIED` (коды fastapi-users, фронт переводит их на русский).

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
          {"id": 1, "slug": "greeting", "title": "Приветствие", "difficulty": 1, "completed": false}
        ]
      }
    ]
  }
]
```
`difficulty` — 1..3. `completed` — решена ли задача текущим пользователем. `slug` — уникальный код задачи (удобно для поиска и ссылок).

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
  "message": null,               // при status="error": дружелюбная причина (например "Ошибка выполнения: SyntaxError ...")
  "new_achievements": [          // значки, открытые ИМЕННО этой отправкой (иначе [])
    {"key": "first_task", "emoji": "🌱", "title": "Первая победа", "desc": "Решил свою первую задачу"}
  ]
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

### POST /api/classes — создать класс (только учитель)
Запрос: `{"name": "7А"}` (1–50 символов).
Ответ `200`:
```jsonc
{"id": 1, "name": "7А", "code": "44FPYA", "students_count": 0, "created_at": "..."}
```
`code` — 6 символов без омнибусных букв (нет 0/O/1/I/L), раздаётся ученикам.
Ошибки: `403` «Классы может создавать только учитель», `401`.

### GET /api/classes — список своих классов (только учитель)
Ответ `200`: массив как POST /api/classes.

### GET /api/classes/{id}/students — ученики класса с прогрессом (владелец-учитель)
Ответ `200`:
```jsonc
{
  "class": {"id": 1, "name": "7А", "code": "44FPYA"},
  "students": [
    {"id": 2, "username": "Коля", "xp": 40, "level": 1, "completed_tasks": 2, "hints_used": 1}
  ]  // отсортировано по XP ↓
}
```
Ошибки: `404` «Класс не найден», `403` «Это не ваш класс» (или «Доступ только для учителей»).

### GET /api/classes/{id}/leaderboard — лидерборд класса
Доступ: учитель-владелец **или ученик этого класса** (иначе `403`; `404` — класса нет).
Ответ `200` — массив по XP ↓ (при равенстве: больше решённых задач, затем имя):
```jsonc
[{"place": 1, "id": 3, "username": "Коля", "xp": 40, "level": 1, "completed_tasks": 2},
 {"place": 2, "id": 5, "username": "Маша", "xp": 0, "level": 1, "completed_tasks": 0}]
```

### GET /api/classes/{id}/stats — расширенная статистика класса (владелец-учитель)
Ответ `200`:
```jsonc
{
  "students": 4, "active_7d": 3, "avg_xp": 30,
  "total_completed": 12,          // решено задач-учеников
  "total_tasks": 24,              // всего задач в игре (4 = students × total_tasks — потолок)
  "per_topic": [{"title": "Циклы", "icon": "🔁", "tasks": 4, "solved": 3}],
  "per_task":   [{"id": 9, "title": "Сумма чисел от 1 до n", "topic": "Циклы", "done_count": 3}]
}
```
Ошибки: `403` для чужого учителя/ученика, `404`.

### POST /api/classes/{id}/students/{sid}/password — новый пароль ученику (владелец-учитель)
Запрос: `{"password": "минимум 6"}`. Ответ: `{"ok": true, "username": "Коля"}`.
Старый пароль перестаёт работать. Ошибки: `404` (ученик не в этом классе), `400` (не ученик), `403`, `422` (короткий пароль).

### POST /api/classes/{id}/assignments — назначить задачу классу (владелец-учитель)
Запрос: `{"task_id": 9}`. Ответ: `{"id": 1, "task_id": 9, "title": "...", "topic": "...", "icon": "🔁", "difficulty": 2}`.
Ошибки: `404` (задачи нет), `409` (уже назначена), `403`.

### GET /api/classes/{id}/assignments — назначенные задачи + прогресс (владелец-учитель)
```jsonc
[{"id": 1, "task_id": 9, "title": "...", "topic": "Циклы", "icon": "🔁", "difficulty": 2,
  "created_at": "...", "done_count": 2, "students_count": 4}]
```

### DELETE /api/assignments/{assignment_id} — убрать задание (владелец-учитель)
Ответ: `{"ok": true}`. Ошибки: `404`, `403`.

### GET /api/assignments — мои задания от учителя (для ученика)
Ученику без класса и учителю — пустой массив `[]`.
```jsonc
[{"id": 1, "task_id": 9, "title": "...", "topic": "Циклы", "icon": "🔁",
  "difficulty": 2, "created_at": "...", "completed": false}]
```

### GET /api/me/achievements — достижения (значки)
Ответ `200`:
```jsonc
{
  "unlocked": ["first_task", "first_try"],
  "items": [
    {"key": "first_task", "emoji": "🌱", "title": "Первая победа",
     "desc": "Решил свою первую задачу", "unlocked": true},
    {"key": "topic:loops", "emoji": "🔁", "title": "Знаток «Циклы»",
     "desc": "Решил все задачи темы «Циклы»", "unlocked": false}
  ]
}
```
15 значков: 9 общих (первая задача, 5/10/20 задач, уровни 3/5, 3 задачи без подсказок, решение первой отправкой, серия 3 дней) + 6 «Знаток темы». Состояние считается на лету, своей таблицы нет.

### GET /api/health
Без авторизации. `{"status": "ok"}`.

---

## Форматы контента (для бэкенда и наполнения)

См. `docs/CONTENT.md`.
