import { useCallback, useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { useAuth } from '../auth'
import {
  createAssignment,
  createClass,
  deleteAssignment,
  getClassAssignments,
  getClassStats,
  getClassStudents,
  getClasses,
  getLeaderboard,
  getTopics,
  resetStudentPassword,
} from '../api/client'
import type {
  Assignment,
  ClassDetail,
  ClassStats,
  LeaderRow,
  SchoolClass,
  Topic,
} from '../api/client'

type Tab = 'students' | 'leaderboard' | 'stats' | 'tasks'

/** Панель учителя: классы, коды, ученики, лидерборд, статистика, задания. */
export default function ClassesPage() {
  const { user } = useAuth()
  const [classes, setClasses] = useState<SchoolClass[] | null>(null)
  const [name, setName] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [copiedId, setCopiedId] = useState<number | null>(null)
  const [detail, setDetail] = useState<ClassDetail | null>(null)
  const [busy, setBusy] = useState(false)

  // активная вкладка и её данные (для открытого класса)
  const [tab, setTab] = useState<Tab>('students')
  const [leaderboard, setLeaderboard] = useState<LeaderRow[] | null>(null)
  const [stats, setStats] = useState<ClassStats | null>(null)
  const [assignments, setAssignments] = useState<Assignment[] | null>(null)
  const [topics, setTopics] = useState<Topic[] | null>(null)
  const [assignTopic, setAssignTopic] = useState('')
  const [assignTask, setAssignTask] = useState('')
  const [notice, setNotice] = useState<string | null>(null)

  const load = useCallback(() => {
    getClasses()
      .then(setClasses)
      .catch((err: unknown) => setError(err instanceof Error ? err.message : 'Не удалось загрузить классы'))
  }, [])

  useEffect(() => {
    load()
  }, [load])

  if (user && user.role !== 'teacher') {
    return (
      <div className="center-message">
        <div className="big-emoji">🔒</div>
        <p>Раздел классов — только для учителей.</p>
      </div>
    )
  }

  async function handleCreate(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setBusy(true)
    try {
      await createClass(name.trim())
      setName('')
      load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось создать класс 😕')
    } finally {
      setBusy(false)
    }
  }

  async function copyCode(klass: SchoolClass) {
    try {
      await navigator.clipboard.writeText(klass.code)
      setCopiedId(klass.id)
      setTimeout(() => setCopiedId(null), 1500)
    } catch {
      setError('Не удалось скопировать — выдели код вручную')
    }
  }

  /** Открыть/закрыть карточку класса + подгрузить данные активной вкладки. */
  async function toggleClass(klass: SchoolClass) {
    if (detail?.class.id === klass.id) {
      setDetail(null)
      setLeaderboard(null)
      setStats(null)
      setAssignments(null)
      return
    }
    setError(null)
    try {
      setDetail(await getClassStudents(klass.id))
      await switchTab(tab, klass.id)
      if (!topics) getTopics().then(setTopics).catch(() => undefined)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось загрузить класс')
    }
  }

  async function switchTab(next: Tab, classId?: number) {
    const id = classId ?? detail?.class.id
    if (!id) return
    setTab(next)
    setError(null)
    try {
      if (next === 'leaderboard') setLeaderboard(await getLeaderboard(id))
      else if (next === 'stats') setStats(await getClassStats(id))
      else if (next === 'tasks') {
        setAssignments(await getClassAssignments(id))
        if (!topics) setTopics(await getTopics())
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось загрузить данные')
    }
  }

  async function handleAssign(e: FormEvent) {
    e.preventDefault()
    const classId = detail?.class.id
    if (!classId || !assignTask) return
    try {
      await createAssignment(classId, Number(assignTask))
      setAssignments(await getClassAssignments(classId))
      setAssignTask('')
      setNotice('📋 Задание назначено!')
      setTimeout(() => setNotice(null), 2500)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось назначить задачу')
    }
  }

  async function handleUnassign(a: Assignment) {
    const classId = detail?.class.id
    if (!classId) return
    try {
      await deleteAssignment(a.id)
      setAssignments(await getClassAssignments(classId))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось убрать задание')
    }
  }

  async function handleResetPassword(studentId: number, studentName: string) {
    const classId = detail?.class.id
    if (!classId) return
    const password = window.prompt(
      `Новый пароль для ученика «${studentName}» (минимум 6 символов):`,
      '',
    )
    if (password === null) return
    if (password.length < 6) {
      setError('Пароль слишком короткий — минимум 6 символов')
      return
    }
    try {
      await resetStudentPassword(classId, studentId, password)
      setNotice(`🔑 Пароль для «${studentName}» изменён`)
      setTimeout(() => setNotice(null), 3000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось сменить пароль')
    }
  }

  const klass = detail?.class ?? null
  const lessonTasks =
    topics?.flatMap((t) => t.lessons.flatMap((l) => l.tasks.map((task) => ({ ...task, topic: t.title })))) ?? []
  const topicOptions = topics?.map((t) => t.title) ?? []
  const filteredTasks = topics
    ? lessonTasks.filter((t) => t.topic === (assignTopic || topicOptions[0]))
    : []

  return (
    <div className="classes-page">
      <section className="card class-create">
        <h1>🏫 Мои классы</h1>
        <p className="xp-note">
          Создай класс и дай код ученикам — они зарегистрируются по нему без почты.
        </p>
        <form onSubmit={handleCreate} className="class-form">
          <input
            className="input"
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Название: напр. 7А"
            required
            maxLength={50}
          />
          <button className="btn btn-primary" type="submit" disabled={busy}>
            {busy ? 'Создаём…' : '➕ Создать класс'}
          </button>
        </form>
        {error && <div className="form-error">⚠️ {error}</div>}
        {notice && <div className="form-ok">{notice}</div>}
      </section>

      {!classes && <p>Загружаем классы…</p>}

      {classes && classes.length === 0 && (
        <div className="center-message">
          <div className="big-emoji">📋</div>
          <p>Классов пока нет — создай первый!</p>
        </div>
      )}

      {classes?.map((item) => (
        <section className="card class-card" key={item.id}>
          <div className="class-head">
            <div>
              <h2>{item.name}</h2>
              <span className="xp-note">👥 Учеников: {item.students_count}</span>
            </div>
            <button
              type="button"
              className="class-code"
              onClick={() => copyCode(item)}
              title="Нажми, чтобы скопировать код"
            >
              {copiedId === item.id ? '✅ скопировано!' : `Код: ${item.code}`}
            </button>
          </div>

          <button type="button" className="btn btn-ghost" onClick={() => void toggleClass(item)}>
            {detail?.class.id === item.id ? 'Свернуть' : '⚙️ Открыть класс'}
          </button>

          {klass?.id === item.id && detail && (
            <>
              <div className="class-tabs">
                <button
                  type="button"
                  className={tab === 'students' ? 'class-tab active' : 'class-tab'}
                  onClick={() => void switchTab('students')}
                >
                  👥 Ученики
                </button>
                <button
                  type="button"
                  className={tab === 'leaderboard' ? 'class-tab active' : 'class-tab'}
                  onClick={() => void switchTab('leaderboard')}
                >
                  🏆 Лидерборд
                </button>
                <button
                  type="button"
                  className={tab === 'stats' ? 'class-tab active' : 'class-tab'}
                  onClick={() => void switchTab('stats')}
                >
                  📊 Статистика
                </button>
                <button
                  type="button"
                  className={tab === 'tasks' ? 'class-tab active' : 'class-tab'}
                  onClick={() => void switchTab('tasks')}
                >
                  📋 Задания
                </button>
              </div>

              {tab === 'students' && (
                <div className="students-list">
                  {detail.students.length === 0 && <p className="xp-note">Пока никого нет 🙂</p>}
                  {detail.students.map((s, i) => (
                    <div className="student-row" key={s.id}>
                      <span className="student-pos">#{i + 1}</span>
                      <span className="student-name">{s.username}</span>
                      <span className="student-stat">⭐ ур. {s.level}</span>
                      <span className="student-stat">✅ {s.completed_tasks}</span>
                      <span className="student-stat">✨ {s.xp} XP</span>
                      <button
                        type="button"
                        className="icon-btn"
                        title="Задать ученику новый пароль"
                        onClick={() => void handleResetPassword(s.id, s.username)}
                      >
                        🔑 Пароль
                      </button>
                    </div>
                  ))}
                </div>
              )}

              {tab === 'leaderboard' && (
                <div className="students-list">
                  {leaderboard === null && <p className="xp-note">Загружаем…</p>}
                  {leaderboard?.length === 0 && <p className="xp-note">В классе пока нет учеников</p>}
                  {leaderboard?.map((row) => (
                    <div
                      className={`student-row leader-row ${row.place <= 3 ? `medal-${row.place}` : ''}`}
                      key={row.id}
                    >
                      <span className="leader-place">
                        {row.place === 1 ? '🥇' : row.place === 2 ? '🥈' : row.place === 3 ? '🥉' : `#${row.place}`}
                      </span>
                      <span className="student-name">{row.username}</span>
                      <span className="student-stat">⭐ ур. {row.level}</span>
                      <span className="student-stat">✅ {row.completed_tasks}</span>
                      <span className="student-stat">✨ {row.xp} XP</span>
                    </div>
                  ))}
                </div>
              )}

              {tab === 'stats' && (
                <div>
                  {stats === null && <p className="xp-note">Загружаем…</p>}
                  {stats && (
                    <>
                      <div className="stats-grid">
                        <div className="stat-card card stat-green">
                          <div className="stat-emoji">👥</div>
                          <div className="stat-value">{stats.students}</div>
                          <div className="stat-label">учеников</div>
                        </div>
                        <div className="stat-card card stat-blue">
                          <div className="stat-emoji">📅</div>
                          <div className="stat-value">{stats.active_7d}</div>
                          <div className="stat-label">заходили за 7 дней</div>
                        </div>
                        <div className="stat-card card stat-purple">
                          <div className="stat-emoji">✨</div>
                          <div className="stat-value">{stats.avg_xp}</div>
                          <div className="stat-label">средний XP</div>
                        </div>
                      </div>

                      <h3 className="xp-note" style={{ marginTop: 16 }}>
                        ✅ Решено задач-учеников: {stats.total_completed} из{' '}
                        {stats.students * stats.total_tasks}
                      </h3>
                      <div className="stats-bars">
                        {stats.per_topic.map((t) => {
                          const possible = t.tasks * stats.students
                          const pct = possible ? Math.round((t.solved / possible) * 100) : 0
                          return (
                            <div key={t.title}>
                              <div className="stat-bar-label">
                                <span>
                                  {t.icon} {t.title}
                                </span>
                                <span>
                                  {t.solved}/{possible} ({pct}%)
                                </span>
                              </div>
                              <div className="stat-bar-track">
                                <div className="stat-bar-fill" style={{ width: `${pct}%` }} />
                              </div>
                            </div>
                          )
                        })}
                      </div>
                    </>
                  )}
                </div>
              )}

              {tab === 'tasks' && (
                <div>
                  <form onSubmit={handleAssign} className="assign-form">
                    <select
                      className="input"
                      value={assignTopic || topicOptions[0] || ''}
                      onChange={(e) => {
                        setAssignTopic(e.target.value)
                        setAssignTask('')
                      }}
                    >
                      {topicOptions.map((t) => (
                        <option key={t} value={t}>
                          {t}
                        </option>
                      ))}
                    </select>
                    <select
                      className="input"
                      value={assignTask}
                      onChange={(e) => setAssignTask(e.target.value)}
                      required
                    >
                      <option value="">— выбери задачу —</option>
                      {filteredTasks.map((t) => (
                        <option key={t.id} value={t.id}>
                          {t.title}
                        </option>
                      ))}
                    </select>
                    <button className="btn btn-primary" type="submit">
                      📌 Назначить
                    </button>
                  </form>

                  <div className="students-list">
                    {assignments === null && <p className="xp-note">Загружаем…</p>}
                    {assignments?.length === 0 && (
                      <p className="xp-note">Заданий пока нет — назначь задачу классу 📌</p>
                    )}
                    {assignments?.map((a) => (
                      <div className="assign-row" key={a.id}>
                        <span className="assign-title">
                          {a.icon} {a.title} <span className="homework-topic">({a.topic})</span>
                        </span>
                        <span className="assign-progress">
                          ✅ {a.done_count} из {a.students_count}
                        </span>
                        <button
                          type="button"
                          className="assign-del"
                          title="Убрать задание"
                          onClick={() => void handleUnassign(a)}
                        >
                          ✕
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </section>
      ))}
    </div>
  )
}
