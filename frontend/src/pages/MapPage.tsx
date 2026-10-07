import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { getTopics } from '../api/client'
import type { Topic } from '../api/client'
import { useAuth } from '../auth'
import XPBar from '../components/XPBar'
import Stars from '../components/Stars'

export default function MapPage() {
  const navigate = useNavigate()
  const { user, refresh } = useAuth()
  const [topics, setTopics] = useState<Topic[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    void refresh()
    getTopics()
      .then(setTopics)
      .catch((err: unknown) => setError(err instanceof Error ? err.message : 'Не удалось загрузить карту'))
  }, [refresh])

  if (error) {
    return (
      <div className="center-message">
        <div className="big-emoji">😿</div>
        <p>{error}</p>
        <button type="button" className="btn btn-primary" onClick={() => window.location.reload()}>
          Попробовать снова
        </button>
      </div>
    )
  }

  if (!topics) {
    return (
      <div className="center-message">
        <div className="big-emoji pulse">🐍</div>
        <p>Загружаем карту приключений…</p>
      </div>
    )
  }

  const solvedCount = topics.reduce(
    (acc, topic) =>
      acc + topic.lessons.reduce((a, lesson) => a + lesson.tasks.filter((t) => t.completed).length, 0),
    0,
  )

  return (
    <div className="map-page">
      <section className="greeting-card">
        <div className="greeting-text">
          <h1>Привет, {user ? user.username : 'друг'}! 👋</h1>
          <p>Сегодня снова покорим Python? Выбирай тему и решай задачки!</p>
        </div>
        <div className="greeting-xp">
          <span className="level-badge big">⭐ Уровень {user ? user.level : 1}</span>
          <XPBar xp={user ? user.xp : 0} level={user ? user.level : 1} />
          <span className="solved-pill">✅ Решено задач: {solvedCount}</span>
        </div>
      </section>

      {topics.length === 0 && (
        <div className="center-message">
          <div className="big-emoji">🗒️</div>
          <p>Карты пока нет — скоро появятся задачи!</p>
        </div>
      )}

      <div className="topics">
        {topics.map((topic) => (
          <section className="topic-card" key={topic.id}>
            <header className="topic-header">
              <span className="topic-icon">{topic.icon}</span>
              <div>
                <h2 className="topic-title">{topic.title}</h2>
                <span className="topic-slug">{topic.slug}</span>
              </div>
            </header>

            {topic.lessons.map((lesson) => (
              <div className="lesson-block" key={lesson.id}>
                <h3 className="lesson-title">📘 {lesson.title}</h3>
                <div className="task-nodes">
                  {lesson.tasks.map((task, idx) => (
                    <button
                      type="button"
                      key={task.id}
                      className={task.completed ? 'task-node done' : 'task-node'}
                      onClick={() => navigate(`/task/${task.id}`)}
                      title={task.title}
                    >
                      <span className="node-circle">{task.completed ? '✔' : idx + 1}</span>
                      <span className="node-title">{task.title}</span>
                      <Stars difficulty={task.difficulty} />
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </section>
        ))}
      </div>

      <footer className="map-footer">
        <Link to="/profile">👤 Посмотреть профиль и статистику</Link>
      </footer>
    </div>
  )
}
