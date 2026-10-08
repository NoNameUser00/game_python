// Обёртка над fetch для API «Подземелья Python».
// Базовый путь /api, авторизация Bearer-токеном из localStorage, ошибки {detail}.

export const TOKEN_KEY = 'token'
export const API_BASE = '/api'

export class ApiError extends Error {
  status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

/* ---------- типы ответов (см. docs/API.md) ---------- */

export interface User {
  id: number
  email: string | null
  username: string
  xp: number
  level: number
  role: 'teacher' | 'pupil'
  class_name: string | null
  created_at: string
}

export interface SchoolClass {
  id: number
  name: string
  code: string
  students_count: number
  created_at: string
}

export interface ClassStudent {
  id: number
  username: string
  xp: number
  level: number
  completed_tasks: number
  hints_used: number
}

export interface ClassDetail {
  class: { id: number; name: string; code: string }
  students: ClassStudent[]
}

export interface AuthResponse {
  access_token: string
  token_type: string
  user: User
}

export interface TaskNode {
  id: number
  title: string
  difficulty: number
  completed: boolean
}

export interface Lesson {
  id: number
  slug: string
  title: string
  order: number
  tasks: TaskNode[]
}

export interface Topic {
  id: number
  slug: string
  title: string
  icon: string
  order: number
  lessons: Lesson[]
}

export interface Task {
  id: number
  topic_id: number
  lesson_id: number
  title: string
  prompt_md: string
  starter_code: string
  difficulty: number
  xp_reward: number
  function: string
  completed: boolean
  attempts: number
  hints_used: number
}

export interface TestResult {
  name: string
  passed: boolean
  message: string | null
}

export type SubmitStatus = 'accepted' | 'failed' | 'error'

export interface SubmitResult {
  status: SubmitStatus
  xp_gained: number
  completed: boolean
  tests: TestResult[]
  message: string | null
  new_achievements: Achievement[]
}

export interface HintResult {
  index: number
  hint: string
  hints_used: number
}

export interface Progress {
  xp: number
  level: number
  completed_tasks: number[]
  submissions: number
  hints_used: number
}

/* ---------- расширенный режим учителя (№7) и достижения (№10) ---------- */

export interface LeaderRow {
  place: number
  id: number
  username: string
  xp: number
  level: number
  completed_tasks: number
}

export interface TopicStat {
  title: string
  icon: string
  tasks: number
  solved: number
}

export interface TaskStat {
  id: number
  title: string
  topic: string
  done_count: number
}

export interface ClassStats {
  students: number
  active_7d: number
  avg_xp: number
  total_completed: number
  total_tasks: number
  per_topic: TopicStat[]
  per_task: TaskStat[]
}

export interface Assignment {
  id: number
  task_id: number
  title: string
  topic: string
  icon: string
  difficulty: number
  created_at: string
  completed?: boolean
  done_count?: number
  students_count?: number
}

export interface Achievement {
  key: string
  emoji: string
  title: string
  desc: string
  unlocked?: boolean
}

export interface AchievementsResponse {
  unlocked: string[]
  items: Achievement[]
}

/* ---------- токен ---------- */

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY)
}

/* ---------- низкоуровневый запрос ---------- */

function extractDetail(data: unknown): string | null {
  if (!data || typeof data !== 'object') return null
  const detail = (data as { detail?: unknown }).detail
  // Коды ошибок fastapi-users → человеческий русский
  const RU: Record<string, string> = {
    RESET_PASSWORD_BAD_TOKEN: 'Ссылка недействительна или уже устарела 😕',
    RESET_PASSWORD_INVALID_PASSWORD: 'Пароль не подходит — попробуй другой',
    VERIFY_USER_BAD_TOKEN: 'Ссылка недействительна или уже устарела 😕',
    VERIFY_USER_ALREADY_VERIFIED: 'Почта уже подтверждена ✅',
    LOGIN_BAD_CREDENTIALS: 'Неверный email/имя или пароль',
  }
  if (typeof detail === 'string') return RU[detail] ?? detail
  if (detail && typeof detail === 'object' && 'code' in detail) {
    const code = String((detail as { code?: unknown }).code)
    const reason = (detail as { reason?: unknown }).reason
    const base = RU[code] ?? code
    return typeof reason === 'string' ? `${base} (${reason})` : base
  }
  // FastAPI 422: detail — массив ошибок валидации
  if (Array.isArray(detail)) {
    const msgs = detail
      .map((d) => {
        if (typeof d === 'string') return d
        if (d && typeof d === 'object' && 'msg' in d) {
          const msg = (d as { msg?: unknown }).msg
          const loc = (d as { loc?: unknown }).loc
          if (typeof msg === 'string') {
            return Array.isArray(loc) && loc.length ? `${msg} (${loc.slice(1).join('.')})` : msg
          }
        }
        return null
      })
      .filter((m): m is string => Boolean(m))
    if (msgs.length) return msgs.join('; ')
  }
  return null
}

function redirectToLogin(): void {
  clearToken()
  if (window.location.pathname !== '/login' && window.location.pathname !== '/register') {
    window.location.assign('/login')
  }
}

async function request<T>(path: string, options: RequestInit = {}, auth = true): Promise<T> {
  const headers: Record<string, string> = {
    Accept: 'application/json',
    ...(options.headers as Record<string, string> | undefined),
  }
  if (options.body !== undefined) headers['Content-Type'] = 'application/json'

  const token = getToken()
  if (auth && token) headers['Authorization'] = `Bearer ${token}`

  let res: Response
  try {
    res = await fetch(API_BASE + path, { ...options, headers })
  } catch {
    throw new ApiError('Не получилось связаться с сервером. Проверь соединение 🤔', 0)
  }

  if (res.status === 401 && auth) {
    redirectToLogin()
    throw new ApiError('Сессия истекла — войди заново', 401)
  }

  const text = await res.text()
  let data: unknown = null
  if (text) {
    try {
      data = JSON.parse(text)
    } catch {
      data = null
    }
  }

  if (!res.ok) {
    const detail = extractDetail(data)
    throw new ApiError(detail ?? `Что-то пошло не так (ошибка ${res.status})`, res.status)
  }

  return data as T
}

/* ---------- эндпоинты ---------- */

export async function register(payload: {
  email: string
  username: string
  password: string
}): Promise<AuthResponse> {
  return request<AuthResponse>('/auth/register', { method: 'POST', body: JSON.stringify(payload) }, false)
}

export async function login(payload: { login: string; password: string }): Promise<AuthResponse> {
  return request<AuthResponse>('/auth/login', { method: 'POST', body: JSON.stringify(payload) }, false)
}

/** Регистрация ученика по коду класса — почта не нужна. */
export async function registerClass(payload: {
  code: string
  username: string
  password: string
}): Promise<AuthResponse> {
  return request<AuthResponse>(
    '/auth/register-class',
    { method: 'POST', body: JSON.stringify(payload) },
    false,
  )
}

export async function createClass(name: string): Promise<SchoolClass> {
  return request<SchoolClass>('/classes', { method: 'POST', body: JSON.stringify({ name }) })
}

export async function getClasses(): Promise<SchoolClass[]> {
  return request<SchoolClass[]>('/classes')
}

/* ---------- fastapi-users: сброс пароля и подтверждение почты ---------- */

/** «Забыли пароль» — письмо со ссылкой (dev: лежит в outbox-файле бэкенда). */
export async function forgotPassword(email: string): Promise<void> {
  await request<unknown>('/auth/forgot-password', {
    method: 'POST',
    body: JSON.stringify({ email }),
  })
}

/** Новый пароль по токену из ссылки письма. */
export async function resetPassword(token: string, password: string): Promise<void> {
  await request<unknown>('/auth/reset-password', {
    method: 'POST',
    body: JSON.stringify({ token, password }),
  })
}

/** Подтверждение почты по токену из ссылки письма. */
export async function verifyEmail(token: string): Promise<{ is_verified?: boolean }> {
  return request<{ is_verified?: boolean }>('/auth/verify', {
    method: 'POST',
    body: JSON.stringify({ token }),
  })
}

export async function getClassStudents(id: number): Promise<ClassDetail> {
  return request<ClassDetail>(`/classes/${id}/students`)
}

export async function me(): Promise<User> {
  return request<User>('/me')
}

export async function getTopics(): Promise<Topic[]> {
  return request<Topic[]>('/topics')
}

export async function getTask(id: number): Promise<Task> {
  return request<Task>(`/tasks/${id}`)
}

export async function submitTask(id: number, code: string): Promise<SubmitResult> {
  return request<SubmitResult>(`/tasks/${id}/submit`, {
    method: 'POST',
    body: JSON.stringify({ code }),
  })
}

export async function requestHint(id: number): Promise<HintResult> {
  return request<HintResult>(`/tasks/${id}/hint`, { method: 'POST' })
}

export async function getProgress(): Promise<Progress> {
  return request<Progress>('/me/progress')
}

export async function getAchievements(): Promise<AchievementsResponse> {
  return request<AchievementsResponse>('/me/achievements')
}

/** Лидерборд класса (видит учитель-владелец и ученики класса). */
export async function getLeaderboard(classId: number): Promise<LeaderRow[]> {
  return request<LeaderRow[]>(`/classes/${classId}/leaderboard`)
}

/** Расширенная статистика класса — только для учителя-владельца. */
export async function getClassStats(classId: number): Promise<ClassStats> {
  return request<ClassStats>(`/classes/${classId}/stats`)
}

/** Назначить задачу классу. */
export async function createAssignment(classId: number, taskId: number): Promise<unknown> {
  return request(`/classes/${classId}/assignments`, {
    method: 'POST',
    body: JSON.stringify({ task_id: taskId }),
  })
}

export async function getClassAssignments(classId: number): Promise<Assignment[]> {
  return request<Assignment[]>(`/classes/${classId}/assignments`)
}

export async function deleteAssignment(id: number): Promise<void> {
  await request(`/assignments/${id}`, { method: 'DELETE' })
}

/** Мои задания от учителя (для ученика). */
export async function getMyAssignments(): Promise<Assignment[]> {
  return request<Assignment[]>('/assignments')
}

/** Учитель задаёт ученику новый пароль. */
export async function resetStudentPassword(
  classId: number,
  studentId: number,
  password: string,
): Promise<{ ok: boolean; username: string }> {
  return request(`/classes/${classId}/students/${studentId}/password`, {
    method: 'POST',
    body: JSON.stringify({ password }),
  })
}
