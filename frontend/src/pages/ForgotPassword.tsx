import { useState } from 'react'
import type { FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { forgotPassword } from '../api/client'
import { APP_NAME } from '../constants'

/** «Забыли пароль»: отправляем письмо со ссылкой для смены пароля. */
export default function ForgotPassword() {
  const [email, setEmail] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [sent, setSent] = useState(false)
  const [busy, setBusy] = useState(false)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setBusy(true)
    try {
      await forgotPassword(email.trim())
      setSent(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не получилось отправить письмо 😕')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-logo">🔑</div>
        <h1 className="auth-title">Забыли пароль?</h1>

        {sent ? (
          <>
            <p className="auth-subtitle">
              Если такая почта есть у нас, мы отправили письмо со ссылкой для смены
              пароля 📨 Проверь почту и перейди по ссылке.
            </p>
            <p className="auth-hint">Письмо не пришло? Проверь папку «Спам».</p>
          </>
        ) : (
          <p className="auth-subtitle">
            Оставь почту, на которую зарегистрирован аккаунт, — пришлём ссылку.
          </p>
        )}

        {!sent && (
          <form onSubmit={handleSubmit} className="auth-form">
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
            {error && <div className="form-error">⚠️ {error}</div>}
            <button className="btn btn-primary btn-block" type="submit" disabled={busy}>
              {busy ? 'Отправляем…' : 'Отправить ссылку'}
            </button>
          </form>
        )}

        <p className="auth-switch">
          <Link to="/login">← Вспомнил пароль? Войти</Link>
        </p>
        <p className="auth-switch">
          <Link to="/">На главную — {APP_NAME}</Link>
        </p>
      </div>
    </div>
  )
}
