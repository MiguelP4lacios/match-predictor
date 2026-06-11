/**
 * EstadoPage — observabilidad del sistema en español de hincha.
 * Muestra métricas de /api/v1/health/full; no calcula veredictos.
 */

import { useQuery } from '@tanstack/react-query'
import { getHealthFull } from '../api/health'
import type { HealthMetric, Verdict } from '../api/health'
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
  if (v === 'ok') return 'ok'
  if (v === 'warn') return 'warn'
  return 'stale'
}

interface MetricRowProps {
  label: string
  metric: HealthMetric
}

function MetricRow({ label, metric }: MetricRowProps) {
  const displayValue =
    metric.value === null ? '—' : String(metric.value)

  return (
    <div className="flex items-center justify-between rounded-lg border border-border bg-surface p-4">
      <div>
        <p className="text-sm font-medium text-text">{label}</p>
        <p className="mt-0.5 text-xl font-bold text-text">{displayValue}</p>
        <p className="mt-0.5 text-xs text-text-muted">Umbral: {metric.threshold}</p>
      </div>
      <Badge variant={verdictToBadge(metric.verdict)}>
        {verdictLabel(metric.verdict)}
      </Badge>
    </div>
  )
}

const METRIC_LABELS: Record<string, string> = {
  last_odds_capture: 'Última captura de cuotas',
  odds_age: 'Antigüedad de cuotas',
  credits_remaining: 'Créditos restantes',
  model_version: 'Versión del modelo',
  last_finished: 'Último partido finalizado',
}

export default function EstadoPage() {
  const {
    data,
    isLoading,
    isError,
    refetch,
  } = useQuery({
    queryKey: ['health-full'],
    queryFn: getHealthFull,
    staleTime: 30_000,
    refetchInterval: 60_000,
  })

  if (isLoading) return <Spinner />

  if (isError || !data) {
    return <ErrorState onRetry={() => void refetch()} />
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <h1 className="text-2xl font-bold text-text">Estado del sistema</h1>
        <Badge variant={verdictToBadge(data.overall)}>
          {verdictLabel(data.overall)}
        </Badge>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <MetricRow label={METRIC_LABELS.last_odds_capture} metric={data.last_odds_capture} />
        <MetricRow label={METRIC_LABELS.odds_age} metric={data.odds_age} />
        <MetricRow label={METRIC_LABELS.credits_remaining} metric={data.credits_remaining} />
        <MetricRow label={METRIC_LABELS.model_version} metric={data.model_version} />
        <MetricRow label={METRIC_LABELS.last_finished} metric={data.last_finished} />
      </div>
    </div>
  )
}
