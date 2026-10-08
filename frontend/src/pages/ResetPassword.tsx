import { useState } from 'react'
import type { FormEvent } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { resetPassword } from '../api/client'

/** Смена пароля по токену из письма (/reset-password?token=...). */
export default function ResetPassword() {
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const token = params.get('token') ?? ''
  const [password, setPassword] = useState('')
  const [password2, setPassword2] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    if (password.length < 6) {
      setError('Пароль должен быть не короче 6 символов 🙈')
      return
    }
    if (password !== password2) {
      setError('Пароли не совпадают 🙈')
      return
    }
    setBusy(true)
    try {
      await resetPassword(token, password)
      navigate('/login?reset=ok', { replace: true })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не получилось сменить пароль 😕')
    } finally {
      setBusy(false)
    }
  }

  if (!token) {
    return (
      <div className="auth-page">
        <div className="auth-card">
          <div className="auth-logo">🔒</div>
          <h1 className="auth-title">Ссылка неполная</h1>
          <p className="auth-subtitle">В ссылке нет токена — открой её прямо из письма.</p>
          <p className="auth-switch">
            <Link to="/forgot-password">Запросить новую ссылку</Link>
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-logo">🛟</div>
        <h1 className="auth-title">Новый пароль</h1>
        <p className="auth-subtitle">Придумай новый пароль для аккаунта.</p>

        <form onSubmit={handleSubmit} className="auth-form">
          <label className="field">
            <span className="field-label">🔑 Новый пароль</span>
            <input
              className="input"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="минимум 6 символов"
              required
              minLength={6}
              autoFocus
            />
          </label>
          <label className="field">
            <span className="field-label">🔁 Ещё раз</span>
            <input
              className="input"
              type="password"
              value={password2}
              onChange={(e) => setPassword2(e.target.value)}
              placeholder="повтори пароль"
              required
              minLength={6}
            />
          </label>

          {error && <div className="form-error">⚠️ {error}</div>}

          <button className="btn btn-primary btn-block" type="submit" disabled={busy}>
            {busy ? 'Сохраняем…' : 'Сохранить пароль'}
          </button>
        </form>

        <p className="auth-switch">
          <Link to="/login">← Войти</Link>
        </p>
      </div>
    </div>
  )
}
