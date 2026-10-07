import { XP_PER_LEVEL } from '../constants'

interface XPBarProps {
  xp: number
  level: number
  showNumbers?: boolean
}

/** Полоса опыта до следующего уровня.
 *  level = xp // 100 + 1, следующий уровень — на отметке level * 100 XP. */
export default function XPBar({ xp, level, showNumbers = true }: XPBarProps) {
  const levelStart = (level - 1) * XP_PER_LEVEL
  const levelEnd = level * XP_PER_LEVEL
  const current = Math.max(0, Math.min(XP_PER_LEVEL, xp - levelStart))
  const pct = (current / XP_PER_LEVEL) * 100

  return (
    <div className="xp-bar-wrap">
      <div
        className="xp-bar"
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={XP_PER_LEVEL}
        aria-valuenow={Math.round(current)}
      >
        <div className="xp-bar-fill" style={{ width: `${pct}%` }} />
      </div>
      {showNumbers && (
        <span className="xp-bar-label">
          {xp} / {levelEnd} XP
        </span>
      )}
    </div>
  )
}
