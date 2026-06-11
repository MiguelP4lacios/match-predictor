/**
 * EstadoPage — observabilidad del sistema en español de hincha.
 * Muestra métricas de /api/v1/health/full; no calcula veredictos (vienen del server).
 */

import { useQuery } from '@tanstack/react-query'
import { getHealthFull } from '../api/health'
import type { Verdict } from '../api/health'
import { Spinner } from '../ui/Spinner'
import { ErrorState } from '../ui/ErrorState'
import { Badge } from '../ui/Badge'
import type { BadgeVariant } from '../ui/Badge'

function verdictToBadge(v: Verdict): BadgeVariant {
  if (v === 'ok') return 'success'
  if (v === 'warn') return 'warn'
  return 'danger'
}

function verdictLabel(v: Verdict): string {
  if (v === 'ok') return 'Al día'
  if (v === 'warn') return 'Atención'
  return 'Desactualizado'
}

/** "hace 2h", "hace 5 min", "—" si no hay dato. */
function hace(ageHours: number | null): string {
  if (ageHours === null) return '—'
  if (ageHours < 1) {
    const min = Math.round(ageHours * 60)
    return min <= 0 ? 'recién' : `hace ${min} min`
  }
  return `hace ${Math.round(ageHours)}h`
}

interface MetricCardProps {
  label: string
  value: string
  detail: string
  verdict: Verdict
}

function MetricCard({ label, value, detail, verdict }: MetricCardProps) {
  return (
    <div className="flex items-center justify-between rounded-lg border border-border bg-surface p-4">
      <div>
        <p className="text-sm font-medium text-text-muted">{label}</p>
        <p className="mt-0.5 text-xl font-bold text-text">{value}</p>
        <p className="mt-0.5 text-xs text-text-muted">{detail}</p>
      </div>
      <Badge variant={verdictToBadge(verdict)}>{verdictLabel(verdict)}</Badge>
    </div>
  )
}

export default function EstadoPage() {
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['health-full'],
    queryFn: getHealthFull,
    staleTime: 30_000,
    refetchInterval: 60_000,
  })

  if (isLoading) return <Spinner />
  if (isError || !data) return <ErrorState onRetry={() => void refetch()} />

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <h1 className="text-2xl font-bold text-text">Estado del sistema</h1>
        <Badge variant={verdictToBadge(data.overall)}>{verdictLabel(data.overall)}</Badge>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <MetricCard
          label="📡 Captura de cuotas"
          value={hace(data.odds_capture.age_hours)}
          detail="Cada 8h automático · ideal < 10h"
          verdict={data.odds_capture.verdict}
        />
        <MetricCard
          label="💳 Créditos de The Odds API"
          value={data.odds_credits.remaining === null ? '—' : `${data.odds_credits.remaining} / 500`}
          detail="Alerta si bajan de 100"
          verdict={data.odds_credits.verdict}
        />
        <MetricCard
          label="🎯 Modelo activo"
          value={data.model.name ?? '—'}
          detail="Backtest aprobado"
          verdict={data.model.verdict}
        />
        <MetricCard
          label="⚽ Resultados al día"
          value={data.results.latest_date ?? '—'}
          detail="Último partido finalizado en la BD"
          verdict={data.results.verdict}
        />
      </div>
    </div>
  )
}
