import { useState } from 'react'
import type { FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { register, setToken } from '../api/client'
import { APP_NAME } from '../constants'

export default function Register() {
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

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

    setBusy(true)
    try {
      const res = await register({ email, username: username.trim(), password })
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

        <form onSubmit={handleSubmit} className="auth-form">
          <label className="field">
            <span className="field-label">📧 Email</span>
            <input
              className="input"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="vasya@school.ru"
              required
              autoFocus
            />
          </label>

          <label className="field">
            <span className="field-label">🐼 Имя</span>
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
