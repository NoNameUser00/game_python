import { useEffect, useState } from 'react'
import { getProgress, me } from '../api/client'
import type { Progress, User } from '../api/client'
import XPBar from '../components/XPBar'

export default function ProfilePage() {
  const [user, setUser] = useState<User | null>(null)
  const [progress, setProgress] = useState<Progress | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    Promise.all([me(), getProgress()])
      .then(([u, p]) => {
        setUser(u)
        setProgress(p)
      })
      .catch((err: unknown) => setError(err instanceof Error ? err.message : 'Не удалось загрузить профиль'))
  }, [])

  if (error) {
    return (
      <div className="center-message">
        <div className="big-emoji">😿</div>
        <p>{error}</p>
      </div>
    )
  }

  if (!user || !progress) {
    return (
      <div className="center-message">
        <div className="big-emoji pulse">🐍</div>
        <p>Загружаем профиль…</p>
      </div>
    )
  }

  const level = progress.level
  const monogram = (user.username.trim()[0] ?? '?').toUpperCase()

  return (
    <div className="profile-page">
      <section className="profile-card">
        <div className="monogram" aria-hidden="true">
          {monogram}
        </div>
        <div className="profile-info">
          <h1>{user.username}</h1>
          {user.email ? (
            <p className="profile-email">📧 {user.email}</p>
          ) : (
            user.class_name && <p className="profile-email">🏫 Класс: {user.class_name}</p>
          )}
          <p className="profile-email">
            {user.role === 'teacher' ? '🧑‍🏫 Учитель' : '🐼 Ученик'}
          </p>
          <span className="level-badge big">⭐ Уровень {level}</span>
        </div>
      </section>

      <section className="profile-xp card">
        <h2>📈 Опыт</h2>
        <XPBar xp={progress.xp} level={level} />
        <p className="xp-note">
          До уровня {level + 1} осталось {Math.max(0, level * 100 - progress.xp)} XP — ты справишься! 🚀
        </p>
      </section>

      <section className="stats-grid">
        <div className="stat-card card stat-green">
          <div className="stat-emoji">✅</div>
          <div className="stat-value">{progress.completed_tasks.length}</div>
          <div className="stat-label">решено задач</div>
        </div>
        <div className="stat-card card stat-blue">
          <div className="stat-emoji">🚀</div>
          <div className="stat-value">{progress.submissions}</div>
          <div className="stat-label">отправок кода</div>
        </div>
        <div className="stat-card card stat-purple">
          <div className="stat-emoji">💡</div>
          <div className="stat-value">{progress.hints_used}</div>
          <div className="stat-label">подсказок использовано</div>
        </div>
      </section>
    </div>
  )
}
