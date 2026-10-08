// Обёртка над fetch для API «Питонята».
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
  if (typeof detail === 'string') return detail
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
