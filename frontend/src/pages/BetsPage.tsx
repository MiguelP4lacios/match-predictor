/**
 * BetsPage — página principal de apuestas (reemplaza PaperPage).
 * Ruta: /apuestas
 */
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { fetchAPI } from '../api/client'
import type { BetsPageStats, BetItem, UpcomingMatch } from '../api/types'
import BetForm from '../components/BetForm'
import BetListComponent from '../components/BetList'
import { Card } from '../ui/Card'
import { Stat } from '../ui/Stat'
import { Spinner } from '../ui/Spinner'
import { ErrorState } from '../ui/ErrorState'
import { formatROI, formatCop } from '../lib/formatters'

// ─── ModeStatsBlock ──────────────────────────────────────────────────────────

interface ModeStatsBlockProps {
  title: string
  stats: BetsPageStats['paper'] | BetsPageStats['real']
  /** Si true, formatea staked/returns en COP; si false, en unidades */
  isCop: boolean
}

function ModeStatsBlock({ title, stats, isCop }: ModeStatsBlockProps) {
  const formatValue = (val: string | null) => {
    if (val === null) return '—'
    const n = parseFloat(val)
    return isCop ? formatCop(n) : n.toFixed(2)
  }

  const roiValue = formatROI(stats.roi)
  const roiTone = stats.roi === null ? 'neutral' : stats.roi > 0 ? 'success' : 'danger'

  return (
    <Card title={title}>
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <Stat label="Apuestas" value={String(stats.total)} />
        <Stat label="Pendientes" value={String(stats.pending)} />
        <Stat label="Cerradas" value={String(stats.settled)} />
        <Stat label="ROI" value={roiValue} tone={roiTone} />
        <Stat label="Staked" value={formatValue(stats.staked)} />
        <Stat label="Returns" value={formatValue(stats.returns)} />
        <Stat label="Ganadas" value={String(stats.won)} tone={stats.won > 0 ? 'success' : 'neutral'} />
        <Stat label="Perdidas" value={String(stats.lost)} tone={stats.lost > 0 ? 'danger' : 'neutral'} />
      </div>
    </Card>
  )
}

// ─── BetsPage ────────────────────────────────────────────────────────────────

export default function BetsPage() {
  const qc = useQueryClient()

  const { data: pageStats, isLoading: loadingStats, isError: errStats } = useQuery<BetsPageStats>({
    queryKey: ['paper'],
    queryFn: () => fetchAPI<BetsPageStats>('/v1/paper'),
    staleTime: 60_000,
  })

  const { data: betList, isLoading: loadingBets, isError: errBets } = useQuery<BetItem[]>({
    queryKey: ['bets'],
    queryFn: () => fetchAPI<BetItem[]>('/v1/bets'),
    staleTime: 30_000,
  })

  const { data: matches = [] } = useQuery<UpcomingMatch[]>({
    queryKey: ['matches-upcoming-form'],
    queryFn: () => fetchAPI<UpcomingMatch[]>('/v1/matches/upcoming?limit=200'),
    staleTime: 120_000,
  })

  function invalidateAll() {
    qc.invalidateQueries({ queryKey: ['paper'] })
    qc.invalidateQueries({ queryKey: ['bets'] })
  }

  const isLoading = loadingStats || loadingBets
  const isError = errStats || errBets

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-bold text-text">Apuestas</h1>

      {isLoading && <Spinner />}
      {isError && <ErrorState onRetry={invalidateAll} />}

      {pageStats && (
        <div className="grid gap-4 md:grid-cols-2">
          <ModeStatsBlock title="Paper" stats={pageStats.paper} isCop={false} />
          <ModeStatsBlock title="Real" stats={pageStats.real} isCop={true} />
        </div>
      )}

      <BetForm matches={matches} onSuccess={invalidateAll} />

      <BetListComponent
        bets={betList ?? []}
        onRefresh={invalidateAll}
      />
    </div>
  )
}
