# 🐍 Питонята — обучающая игра «Изучай Python»

Фронтенд SPA для школьников: карта тем, задачи с автопроверкой, подсказки, XP и уровни.

## Стек

- React 18+ (установлена 19) + TypeScript + Vite (шаблон `react-ts`)
- `react-router-dom` — маршруты
- `@uiw/react-codemirror` + `@codemirror/lang-python` + `@uiw/codemirror-themes` — редактор кода с темой Dracula (создана через `createTheme` в `src/theme.ts`)
- `react-markdown` — отрисовка `prompt_md` (Markdown)
- Обычный CSS одним файлом: `src/styles.css` (без CSS-фреймворков)

## Запуск

```bash
npm install
npm run dev      # http://localhost:5173, прокси /api → http://127.0.0.1:8000
npm run build    # сборка в dist/ (tsc -b && vite build)
```

Прокси на бэкенд настроен в `vite.config.ts` (`server.proxy`).

## Структура

```
src/
  api/client.ts        # обёртка над fetch: /api, Bearer-токен, 401 → /login, {detail}
  auth.tsx             # контекст пользователя (me/logout)
  constants.ts         # APP_NAME = «Питонята», XP_PER_LEVEL
  components/          # Layout (шапка), ProtectedRoute, XPBar, Stars
  pages/               # Login, Register, MapPage, TaskPage, ProfilePage
  theme.ts             # тема Dracula для CodeMirror
  styles.css           # весь стиль
```

## Роуты

- `/login`, `/register` — авторизация (токен в `localStorage["token"]`)
- `/` — карта: темы → уроки → задачи (номер, ✔ если решено, ★ сложность), приветствие + XP-бар
- `/task/:id` — условие (Markdown) + подсказки слева, редактор и проверка справа (Ctrl/Cmd+Enter)
- `/profile` — монограмма, уровень, XP-бар, статистика
- без токена любой защищённый маршрут → `/login`
