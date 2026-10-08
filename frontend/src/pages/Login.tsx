import { useState } from 'react'
import type { FormEvent } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { login, setToken } from '../api/client'
import { APP_NAME } from '../constants'

export default function Login() {
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const resetOk = params.get('reset') === 'ok'
  const [loginIdent, setLoginIdent] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setBusy(true)
    try {
      const res = await login({ login: loginIdent.trim(), password })
      setToken(res.access_token)
      navigate('/', { replace: true })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не получилось войти 😕')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-logo">🐍</div>
        <h1 className="auth-title">{APP_NAME}</h1>
        <p className="auth-subtitle">С возвращением! Продолжим изучать Python?</p>

        <form onSubmit={handleSubmit} className="auth-form">
          <label className="field">
            <span className="field-label">📧 Email (учитель) или 🐼 Имя (ученик)</span>
            <input
              className="input"
              type="text"
              value={loginIdent}
              onChange={(e) => setLoginIdent(e.target.value)}
              placeholder="vasya@school.ru или Маша"
              required
              autoFocus
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
            />
          </label>

          <p className="forgot-link">
            <Link to="/forgot-password">Забыли пароль? 🔑</Link>
          </p>

          {resetOk && <div className="form-ok">✅ Пароль изменён — войди с новым!</div>}
          {error && <div className="form-error">⚠️ {error}</div>}

          <button className="btn btn-primary btn-block" type="submit" disabled={busy}>
            {busy ? 'Входим…' : 'Войти'}
          </button>
        </form>

        <p className="auth-switch">
          <Link to="/register">Нет аккаунта? Регистрация</Link>
        </p>
      </div>
    </div>
  )
}
