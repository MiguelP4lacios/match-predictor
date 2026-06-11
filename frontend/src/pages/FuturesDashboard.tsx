/**
 * FuturesDashboard — Vista de probabilidades de futuros WC2026.
 *
 * Secciones:
 *   - Tabla de campeones (ranked por p_champion DESC) con FlagLabel + %
 *   - Tabs: Campeón | Avance Grupo | Semi | Final
 *   - Señales +EV OUTRIGHT_WINNER con edge badge
 *
 * Invariantes:
 *   - staleTime: 55_000 (mismo criterio que otras vistas)
 *   - Solo primitivas del design system (Card, Badge, FlagLabel, Tabs, Spinner, ErrorState)
 *   - Sin colores hardcodeados — solo tokens semánticos
 */

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getFutures, getFuturesSignals } from '../api/futures'
import type { FutureTeamRow, FutureSignal } from '../api/types'
import { Card } from '../ui/Card'
import { Badge } from '../ui/Badge'
import { FlagLabel } from '../ui/FlagLabel'
import { Tabs } from '../ui/Tabs'
import { Spinner } from '../ui/Spinner'
import { ErrorState } from '../ui/ErrorState'

// ---------------------------------------------------------------------------
// Formatters puros — fáciles de testear unitariamente
// ---------------------------------------------------------------------------

/** Convierte un ratio [0,1] a porcentaje con 1 decimal (ej. 0.18 → "18.0%"). */
export function formatPct(value: number): string {
  return `${(value * 100).toFixed(1)}%`
}

/** Edge de señal con signo explícito (ej. 0.04 → "+4.0%"). */
export function formatEdgeSign(edge: number): string {
  const pct = (edge * 100).toFixed(1)
  return edge >= 0 ? `+${pct}%` : `${pct}%`
}

// ---------------------------------------------------------------------------
// Sub-componentes
// ---------------------------------------------------------------------------

const TABS = [
  { id: 'champion', label: 'Campeón' },
  { id: 'advance', label: 'Avance Grupo' },
  { id: 'semi', label: 'Semis' },
  { id: 'final', label: 'Final' },
]

function getProbForTab(row: FutureTeamRow, tab: string): number {
  switch (tab) {
    case 'advance':
      return row.p_advance_group
    case 'semi':
      return row.p_reach_sf
    case 'final':
      return row.p_reach_final
    default:
      return row.p_champion
  }
}

function getTabLabel(tab: string): string {
  switch (tab) {
    case 'advance':
      return 'P(Avance)'
    case 'semi':
      return 'P(Semifinal)'
    case 'final':
      return 'P(Final)'
    default:
      return 'P(Campeón)'
  }
}

interface ChampionTableProps {
  champions: FutureTeamRow[]
  activeTab: string
}

function ChampionTable({ champions, activeTab }: ChampionTableProps) {
  const probLabel = getTabLabel(activeTab)

  // Reordenar por la prob del tab activo
  const sorted = [...champions].sort(
    (a, b) => getProbForTab(b, activeTab) - getProbForTab(a, activeTab),
  )

  return (
    <div className="overflow-hidden rounded-lg border border-border">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border bg-surface">
            <th className="px-3 py-2 text-left font-semibold text-text-muted">#</th>
            <th className="px-3 py-2 text-left font-semibold text-text-muted">Equipo</th>
            <th className="px-3 py-2 text-right font-semibold text-text-muted">{probLabel}</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((row, idx) => (
            <tr
              key={row.team_id}
              data-testid="champion-row"
              className="border-b border-border last:border-0 hover:bg-surface/50 transition-colors"
            >
              <td className="px-3 py-2 text-text-muted tabular-nums">{idx + 1}</td>
              <td className="px-3 py-2">
                <FlagLabel team={row.team} size="sm" />
              </td>
              <td className="px-3 py-2 text-right tabular-nums text-text">
                {formatPct(getProbForTab(row, activeTab))}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

interface SignalsSectionProps {
  signals: FutureSignal[]
}

function SignalsSection({ signals }: SignalsSectionProps) {
  return (
    <Card title="Señales +EV Futuros">
      {signals.length === 0 ? (
        <p className="text-sm text-text-muted">
          Sin señales — capturá odds de OUTRIGHT_WINNER para ver edge.
        </p>
      ) : (
        <div className="overflow-hidden rounded border border-border">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border bg-surface">
                <th className="px-3 py-2 text-left font-semibold text-text-muted">Equipo</th>
                <th className="px-3 py-2 text-right font-semibold text-text-muted">P(Campeón)</th>
                <th className="px-3 py-2 text-right font-semibold text-text-muted">Cuota</th>
                <th className="px-3 py-2 text-right font-semibold text-text-muted">Edge</th>
                <th className="px-3 py-2 text-left font-semibold text-text-muted">Casa</th>
              </tr>
            </thead>
            <tbody>
              {signals.map((sig) => (
                <tr
                  key={sig.signal_id}
                  className="border-b border-border last:border-0 hover:bg-surface/50 transition-colors"
                >
                  <td className="px-3 py-2">
                    <FlagLabel team={sig.team} size="sm" />
                  </td>
                  <td className="px-3 py-2 text-right tabular-nums text-text">
                    {formatPct(sig.p_champion)}
                  </td>
                  <td className="px-3 py-2 text-right tabular-nums text-text">
                    {sig.best_odds.toFixed(2)}
                  </td>
                  <td className="px-3 py-2 text-right">
                    <Badge variant="success">{formatEdgeSign(sig.edge)}</Badge>
                  </td>
                  <td className="px-3 py-2 text-text-muted">{sig.bookmaker}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  )
}

// ---------------------------------------------------------------------------
// Componente principal
// ---------------------------------------------------------------------------

export default function FuturesDashboard() {
  const [activeTab, setActiveTab] = useState('champion')

  const {
    data: futures,
    isLoading,
    isError,
    refetch,
  } = useQuery({
    queryKey: ['futures-probabilities'],
    queryFn: getFutures,
    staleTime: 55_000,
    refetchInterval: 60_000,
  })

  const { data: signals } = useQuery({
    queryKey: ['futures-signals'],
    queryFn: getFuturesSignals,
    staleTime: 55_000,
    refetchInterval: 60_000,
  })

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-bold text-text">Futuros WC2026</h1>

      {isLoading && <Spinner />}
      {isError && <ErrorState onRetry={() => refetch()} />}

      {futures && (
        <>
          <Card>
            <Tabs tabs={TABS} value={activeTab} onChange={setActiveTab} className="mb-4" />
            {futures.champions.length > 0 ? (
              <ChampionTable champions={futures.champions} activeTab={activeTab} />
            ) : (
              <p className="text-sm text-text-muted">
                Sin datos — ejecutá run_futures simulate para generar predicciones.
              </p>
            )}
          </Card>

          <SignalsSection signals={signals?.items ?? []} />
        </>
      )}
    </div>
  )
}
