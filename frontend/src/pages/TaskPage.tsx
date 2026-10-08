import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import Markdown from 'react-markdown'
import { useNavigate, useParams } from 'react-router-dom'
import CodeMirror from '@uiw/react-codemirror'
import { python } from '@codemirror/lang-python'
import { Prec } from '@codemirror/state'
import { keymap } from '@codemirror/view'
import { getTask, requestHint, submitTask } from '../api/client'
import type { HintResult, SubmitResult, Task } from '../api/client'
import { useAuth } from '../auth'
import { draculaTheme } from '../theme'
import Stars from '../components/Stars'

export default function TaskPage() {
  const { id: idParam } = useParams()
  const navigate = useNavigate()
  const { refresh } = useAuth()

  const id = Number(idParam)

  const [task, setTask] = useState<Task | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [code, setCode] = useState('')

  const [hints, setHints] = useState<HintResult[]>([])
  const [hintError, setHintError] = useState<string | null>(null)
  const [hintBusy, setHintBusy] = useState(false)

  const [result, setResult] = useState<SubmitResult | null>(null)
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  /* Загрузка задачи (и сброс состояния при переходе к другой задаче) */
  useEffect(() => {
    setTask(null)
    setCode('')
    setHints([])
    setHintError(null)
    setResult(null)
    setSubmitError(null)
    setLoadError(null)

    if (!Number.isInteger(id) || id <= 0) {
      setLoadError('Такой задачи не существует 😕')
      return
    }
    let cancelled = false
    getTask(id)
      .then((t) => {
        if (cancelled) return
        setTask(t)
        setCode(t.starter_code)
      })
      .catch((err: unknown) => {
        if (!cancelled) setLoadError(err instanceof Error ? err.message : 'Не удалось загрузить задачу')
      })
    return () => {
      cancelled = true
    }
  }, [id])

  /* Отправка решения */
  const inFlight = useRef(false)
  const submit = useCallback(async () => {
    if (!task || inFlight.current) return
    inFlight.current = true
    setSubmitting(true)
    setSubmitError(null)
    setResult(null)
    try {
      const res = await submitTask(task.id, code)
      setResult(res)
      setTask((prev) => (prev ? { ...prev, completed: res.completed, attempts: prev.attempts + 1 } : prev))
      void refresh()
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : 'Не получилось отправить решение 😕')
    } finally {
      inFlight.current = false
      setSubmitting(false)
    }
  }, [task, code, refresh])

  const submitRef = useRef(submit)
  useEffect(() => {
    submitRef.current = submit
  }, [submit])

  /* Ctrl/Cmd + Enter — отправка решения (работает и внутри редактора, и снаружи) */
  const editorExtensions = useMemo(
    () => [
      python(),
      Prec.high(
        keymap.of([
          {
            key: 'Mod-Enter',
            run: () => {
              void submitRef.current()
              return true
            },
          },
        ]),
      ),
    ],
    [],
  )

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        e.preventDefault()
        void submitRef.current()
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [])

  /* Подсказка */
  async function askHint() {
    if (!task || hintBusy) return
    setHintBusy(true)
    setHintError(null)
    try {
      const h = await requestHint(task.id)
      setHints((prev) => (prev.some((p) => p.index === h.index) ? prev : [...prev, h]))
      setTask((prev) => (prev ? { ...prev, hints_used: h.hints_used } : prev))
      void refresh()
    } catch (err) {
      setHintError(err instanceof Error ? err.message : 'Подсказки закончились 🙈')
    } finally {
      setHintBusy(false)
    }
  }

  if (loadError) {
    return (
      <div className="center-message">
        <div className="big-emoji">🙈</div>
        <p>{loadError}</p>
        <button type="button" className="btn btn-primary" onClick={() => navigate('/')}>
          ← К карте
        </button>
      </div>
    )
  }

  if (!task) {
    return (
      <div className="center-message">
        <div className="big-emoji pulse">🐍</div>
        <p>Открываем задачку…</p>
      </div>
    )
  }

  return (
    <div className="task-page">
      {/* ЛЕВАЯ ПАНЕЛЬ — условие */}
      <section className="task-panel">
        <button type="button" className="btn btn-ghost back-btn" onClick={() => navigate('/')}>
          ← К карте
        </button>

        <div className="task-head">
          <h1 className="task-title">{task.title}</h1>
          <div className="task-meta">
            <Stars difficulty={task.difficulty} size="big" />
            <span className="xp-pill">🎁 +{task.xp_reward} XP</span>
            {task.completed && <span className="done-pill">✅ Решено</span>}
          </div>
        </div>

        <div className="prompt-md">
          <Markdown>{task.prompt_md}</Markdown>
        </div>

        <div className="hint-box">
          <button type="button" className="btn btn-hint" onClick={() => void askHint()} disabled={hintBusy}>
            💡 Подсказка
          </button>
          <span className="hint-counter">использовано: {task.hints_used}</span>
          {hintError && <div className="form-error">⚠️ {hintError}</div>}
        </div>

        <div className="hint-cards">
          {hints.map((h) => (
            <div className="hint-card" key={h.index}>
              <span className="hint-card-num">💡 {h.index}</span>
              <p>{h.hint}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ПРАВАЯ ПАНЕЛЬ — код и проверка */}
      <section className="editor-panel">
        <div className="editor-toolbar">
          <span className="editor-label">🐍 Твой код</span>
          <span className="editor-hint">Ctrl + Enter — проверить</span>
        </div>

        <div className="editor-host">
          <CodeMirror
            className="code-editor"
            value={code}
            height="100%"
            theme={draculaTheme}
            extensions={editorExtensions}
            onChange={setCode}
            basicSetup={{ lineNumbers: true, highlightActiveLine: true, autocompletion: true }}
          />
        </div>

        <button
          type="button"
          className="btn btn-primary btn-run"
          onClick={() => void submit()}
          disabled={submitting}
        >
          {submitting ? 'Проверяем…' : '▶ Проверить'}
        </button>

        {submitError && <div className="platter platter-error">❌ {submitError}</div>}

        {result && (
          <>
            {result.new_achievements.length > 0 && (
              <div className="ach-toast pop">
                {result.new_achievements.map((a) => (
                  <div className="ach-toast-row" key={a.key}>
                    <span className="ach-toast-emoji">{a.emoji}</span>
                    <span>
                      <strong>Новое достижение: {a.title}!</strong>
                      <br />
                      {a.desc}
                    </span>
                  </div>
                ))}
              </div>
            )}

            {result.status === 'accepted' ? (
              <div className="platter platter-ok pop">
                🎉 Задача решена!{' '}
                <strong>{result.xp_gained > 0 ? `+${result.xp_gained} XP` : 'молодец!'}</strong>
              </div>
            ) : (
              <div className="platter platter-error pop">
                ❌ {result.message ?? (result.status === 'error' ? 'Код упал с ошибкой' : 'Не все тесты прошли')}
              </div>
            )}

            {result.tests.length > 0 && (
              <ul className="test-list">
                {result.tests.map((t, i) => (
                  <li key={i} className={t.passed ? 'test-row passed' : 'test-row failed'}>
                    <span className="test-icon">{t.passed ? '✅' : '🚫'}</span>
                    <span className="test-name">{t.name}</span>
                    {!t.passed && t.message && <span className="test-msg">{t.message}</span>}
                  </li>
                ))}
              </ul>
            )}
          </>
        )}
      </section>
    </div>
  )
}
