import { useEffect, useState } from 'react'
import { getHealthFull } from '../api/health'
import type { Verdict } from '../api/health'

const ICONS: Record<Verdict, string> = {
  ok: '🟢',
  warn: '🟡',
  stale: '🔴',
}

const LABELS: Record<Verdict, string> = {
  ok: 'Sistema operativo',
  warn: 'Advertencia',
  stale: 'Datos desactualizados',
}

const POLL_INTERVAL_MS = 60_000

export function StatusBadge() {
  const [verdict, setVerdict] = useState<Verdict | null>(null)

  useEffect(() => {
    let cancelled = false

    async function poll() {
      try {
        const data = await getHealthFull()
        if (!cancelled) setVerdict(data.overall)
      } catch {
        if (!cancelled) setVerdict('stale')
      }
    }

    void poll()
    const id = setInterval(poll, POLL_INTERVAL_MS)
    return () => {
      cancelled = true
      clearInterval(id)
    }
  }, [])

  if (verdict === null) {
    return (
      <span
        role="status"
        aria-label="Verificando sistema"
        className="text-text-muted text-base"
        title="Verificando sistema..."
      >
        ⚪
      </span>
    )
  }

  return (
    <span
      role="status"
      aria-label={LABELS[verdict]}
      className="text-base"
      title={LABELS[verdict]}
    >
      {ICONS[verdict]}
    </span>
  )
}
