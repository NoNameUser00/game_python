import { useState } from 'react'
import type { FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { register, registerClass, setToken } from '../api/client'
import { APP_NAME } from '../constants'

type Mode = 'pupil' | 'teacher'

/**
 * Регистрация:
 *  - ученик — по коду класса от учителя, БЕЗ почты (приватность детей);
 *  - учитель — по email.
 */
export default function Register() {
  const navigate = useNavigate()
  const [mode, setMode] = useState<Mode>('pupil')
  const [code, setCode] = useState('')
  const [email, setEmail] = useState('')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  function switchMode(next: Mode) {
    setMode(next)
    setError(null)
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)

    if (password.length < 6) {
      setError('Пароль должен быть не короче 6 символов 🙈')
      return
    }
    if (username.trim().length < 1 || username.trim().length > 30) {
      setError('Имя должно быть от 1 до 30 символов 🙂')
      return
    }
    if (mode === 'pupil' && code.trim().length < 4) {
      setError('Введи код класса — его дал учитель 🏫')
      return
    }

    setBusy(true)
    try {
      const res =
        mode === 'pupil'
          ? await registerClass({
              code: code.trim().toUpperCase(),
              username: username.trim(),
              password,
            })
          : await register({ email, username: username.trim(), password })
      setToken(res.access_token)
      navigate('/', { replace: true })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не получилось зарегистрироваться 😕')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-logo">🎉</div>
        <h1 className="auth-title">Новый питонёнок</h1>
        <p className="auth-subtitle">Создай аккаунт в {APP_NAME} и начни приключение!</p>

        <div className="auth-tabs" role="tablist">
          <button
            type="button"
            role="tab"
            aria-selected={mode === 'pupil'}
            className={mode === 'pupil' ? 'auth-tab active' : 'auth-tab'}
            onClick={() => switchMode('pupil')}
          >
            🐼 Ученик
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={mode === 'teacher'}
            className={mode === 'teacher' ? 'auth-tab active' : 'auth-tab'}
            onClick={() => switchMode('teacher')}
          >
            🧑‍🏫 Учитель
          </button>
        </div>

        <form onSubmit={handleSubmit} className="auth-form">
          {mode === 'pupil' ? (
            <label className="field">
              <span className="field-label">🏫 Код класса</span>
              <input
                className="input code-input"
                type="text"
                value={code}
                onChange={(e) => setCode(e.target.value.toUpperCase())}
                placeholder="напр. K7M2Q9"
                required
                maxLength={12}
                autoFocus
              />
            </label>
          ) : (
            <label className="field">
              <span className="field-label">📧 Email</span>
              <input
                className="input"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="teacher@school.ru"
                required
                autoFocus
              />
            </label>
          )}

          <label className="field">
            <span className="field-label">🐼 Имя{mode === 'teacher' ? ' учителя' : ' ученика'}</span>
            <input
              className="input"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Как тебя зовут?"
              required
              maxLength={30}
            />
          </label>

          <label className="field">
            <span className="field-label">🔑 Пароль</span>
            <input
              className="input"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="минимум 6 символов"
              required
              minLength={6}
            />
          </label>

          {mode === 'pupil' && (
            <p className="auth-hint">
              Код класса выдаёт учитель — почта тебе не нужна 🔒
            </p>
          )}

          {error && <div className="form-error">⚠️ {error}</div>}

          <button className="btn btn-primary btn-block" type="submit" disabled={busy}>
            {busy ? 'Создаём…' : 'Зарегистрироваться'}
          </button>
        </form>

        <p className="auth-switch">
          <Link to="/login">Уже есть аккаунт? Войти</Link>
        </p>
      </div>
    </div>
  )
}
