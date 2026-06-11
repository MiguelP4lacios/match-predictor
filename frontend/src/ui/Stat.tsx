import type { ReactNode } from 'react'

type StatTone = 'success' | 'warn' | 'danger' | 'neutral'

const TONE_CLASSES: Record<StatTone, string> = {
  success: 'text-success',
  warn: 'text-warn',
  danger: 'text-danger',
  neutral: 'text-text',
}

interface StatProps {
  label: string
  value: ReactNode
  hint?: string
  tone?: StatTone
}

export function Stat({ label, value, hint, tone = 'neutral' }: StatProps) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-xs font-medium uppercase tracking-wide text-text-muted">{label}</span>
      <span className={`text-2xl font-bold tabular-nums ${TONE_CLASSES[tone]}`}>{value}</span>
      {hint && <span className="text-xs text-text-muted">{hint}</span>}
    </div>
  )
}
