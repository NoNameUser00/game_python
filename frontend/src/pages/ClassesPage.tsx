import { useCallback, useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { useAuth } from '../auth'
import { createClass, getClassStudents, getClasses } from '../api/client'
import type { ClassDetail, SchoolClass } from '../api/client'

/** Панель учителя: создать класс, показать код ученикам, посмотреть прогресс. */
export default function ClassesPage() {
  const { user } = useAuth()
  const [classes, setClasses] = useState<SchoolClass[] | null>(null)
  const [name, setName] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [copiedId, setCopiedId] = useState<number | null>(null)
  const [detail, setDetail] = useState<ClassDetail | null>(null)
  const [busy, setBusy] = useState(false)

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

  async function toggleStudents(klass: SchoolClass) {
    if (detail?.class.id === klass.id) {
      setDetail(null)
      return
    }
    try {
      setDetail(await getClassStudents(klass.id))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось загрузить учеников')
    }
  }

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
      </section>

      {!classes && <p>Загружаем классы…</p>}

      {classes && classes.length === 0 && (
        <div className="center-message">
          <div className="big-emoji">📋</div>
          <p>Классов пока нет — создай первый!</p>
        </div>
      )}

      {classes?.map((klass) => (
        <section className="card class-card" key={klass.id}>
          <div className="class-head">
            <div>
              <h2>{klass.name}</h2>
              <span className="xp-note">👥 Учеников: {klass.students_count}</span>
            </div>
            <button
              type="button"
              className="class-code"
              onClick={() => copyCode(klass)}
              title="Нажми, чтобы скопировать код"
            >
              {copiedId === klass.id ? '✅ скопировано!' : `Код: ${klass.code}`}
            </button>
          </div>

          <button type="button" className="btn btn-ghost" onClick={() => toggleStudents(klass)}>
            {detail?.class.id === klass.id ? 'Скрыть учеников' : '👥 Показать учеников'}
          </button>

          {detail?.class.id === klass.id && (
            <div className="students-list">
              {detail.students.length === 0 && <p className="xp-note">Пока никого нет 🙂</p>}
              {detail.students.map((s, i) => (
                <div className="student-row" key={s.id}>
                  <span className="student-pos">#{i + 1}</span>
                  <span className="student-name">{s.username}</span>
                  <span className="student-stat">⭐ ур. {s.level}</span>
                  <span className="student-stat">✅ {s.completed_tasks}</span>
                  <span className="student-stat">✨ {s.xp} XP</span>
                </div>
              ))}
            </div>
          )}
        </section>
      ))}
    </div>
  )
}
