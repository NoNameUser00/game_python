interface StarsProps {
  difficulty: number
  /** всего звёздочек (по умолчанию 3) */
  total?: number
  size?: 'small' | 'big'
}

/** Звёздочки сложности: ★★★ (заполненные / пустые). */
export default function Stars({ difficulty, total = 3, size = 'small' }: StarsProps) {
  const d = Math.max(0, Math.min(total, difficulty))
  return (
    <span className={`stars stars-${size}`} title={`Сложность ${d} из ${total}`} aria-label={`Сложность ${d} из ${total}`}>
      {Array.from({ length: total }, (_, i) => (
        <span key={i} className={i < d ? 'star star-on' : 'star star-off'}>
          ★
        </span>
      ))}
    </span>
  )
}
