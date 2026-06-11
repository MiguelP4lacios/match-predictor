/**
 * BetsPage — página principal de apuestas (reemplaza PaperPage).
 * Ruta: /apuestas
 * Muestra:
 *   - 2 ModeStatsBlock (PAPER / REAL)
 *   - BetForm (registro de nueva apuesta)
 *   - BetList (lista de apuestas existentes)
 */
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { fetchAPI } from '../api/client'
import type { BetsPageStats, BetList, UpcomingMatch } from '../api/types'
import BetForm from '../components/BetForm'
import BetListComponent from '../components/BetList'
import Loading from '../components/Loading'
import ErrorBanner from '../components/ErrorBanner'
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

  return (
    <div className="rounded-lg border bg-white p-4 shadow-sm">
      <h3 className="mb-3 text-sm font-bold uppercase tracking-wide text-gray-600">{title}</h3>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Stat label="Apuestas" value={String(stats.total)} />
        <Stat label="Pendientes" value={String(stats.pending)} />
        <Stat label="Cerradas" value={String(stats.settled)} />
        <Stat
          label="ROI"
          value={formatROI(stats.roi)}
          highlight={stats.roi !== null && stats.roi > 0}
        />
        <Stat label="Staked" value={formatValue(stats.staked)} />
        <Stat label="Returns" value={formatValue(stats.returns)} />
        <Stat label="Ganadas" value={String(stats.won)} />
        <Stat label="Perdidas" value={String(stats.lost)} />
      </div>
    </div>
  )
}

function Stat({ label, value, highlight = false }: { label: string; value: string; highlight?: boolean }) {
  return (
    <div>
      <p className="text-xs font-medium uppercase text-gray-500">{label}</p>
      <p className={`mt-0.5 text-lg font-bold ${highlight ? 'text-green-600' : 'text-gray-800'}`}>
        {value}
      </p>
    </div>
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

  const { data: betList, isLoading: loadingBets, isError: errBets } = useQuery<BetList>({
    queryKey: ['bets'],
    queryFn: () => fetchAPI<BetList>('/v1/bets'),
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
      <h1 className="text-xl font-bold">Apuestas</h1>

      {isLoading && <Loading />}
      {isError && <ErrorBanner onRetry={invalidateAll} />}

      {pageStats && (
        <div className="grid gap-4 md:grid-cols-2">
          <ModeStatsBlock title="Paper" stats={pageStats.paper} isCop={false} />
          <ModeStatsBlock title="Real" stats={pageStats.real} isCop={true} />
        </div>
      )}

      <BetForm matches={matches} onSuccess={invalidateAll} />

      <BetListComponent
        bets={betList?.items ?? []}
        onRefresh={invalidateAll}
      />
    </div>
  )
}
