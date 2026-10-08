import { useEffect, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { verifyEmail } from '../api/client'

type State = 'loading' | 'ok' | 'error'

/** Подтверждение почты по ссылке из письма (/verify?token=...). */
export default function VerifyEmail() {
  const [params] = useSearchParams()
  const token = params.get('token') ?? ''
  const [state, setState] = useState<State>(token ? 'loading' : 'error')
  const [message, setMessage] = useState<string>('')
  const started = useRef(false)

  useEffect(() => {
    if (!token || started.current) return
    started.current = true
    verifyEmail(token)
      .then((user) => {
        setState('ok')
        setMessage(user.is_verified ? 'Почта подтверждена ✅' : 'Готово!')
      })
      .catch((err: unknown) => {
        setState('error')
        setMessage(err instanceof Error ? err.message : 'Не получилось подтвердить почту 😕')
      })
  }, [token])

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-logo">{state === 'ok' ? '🎉' : state === 'loading' ? '⏳' : '🙈'}</div>
        <h1 className="auth-title">Подтверждение почты</h1>

        {state === 'loading' && <p className="auth-subtitle">Проверяем ссылку…</p>}
        {state === 'ok' && (
          <p className="auth-subtitle">
            {message} Теперь всё в порядке — можно пользоваться игрой!
          </p>
        )}
        {state === 'error' && <div className="form-error">⚠️ {message}</div>}

        <p className="auth-switch">
          <Link to="/login">Перейти ко входу</Link>
        </p>
        <p className="auth-switch">
          <Link to="/">На главную</Link>
        </p>
      </div>
    </div>
  )
}
