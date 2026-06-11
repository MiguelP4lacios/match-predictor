/**
 * BetList — lista de apuestas con estado coloreado y PnL formateado.
 * - Filas ordenadas por placed_at DESC
 * - Delete solo REAL PENDING → confirm → DELETE /api/v1/bets/{id}
 */
import { fetchAPI } from '../api/client'
import { formatCop, formatPnl } from '../lib/formatters'
import type { BetItem } from '../api/types'

interface BetListProps {
  bets: BetItem[]
  onRefresh: () => void
}

/** Humaniza outcome_code al nombre del resultado */
function humanizeOutcome(code: string | null): string {
  if (!code) return '—'
  if (code === 'HOME') return 'Local gana'
  if (code === 'DRAW') return 'Empate'
  if (code === 'AWAY') return 'Visita gana'
  return code
}

/** Badge con color según estado */
function StatusBadge({ status }: { status: string }) {
  const map: Record<string, { label: string; cls: string }> = {
    pending: { label: 'PENDIENTE', cls: 'bg-gray-100 text-gray-700' },
    won: { label: 'GANADA', cls: 'bg-green-100 text-green-700' },
    lost: { label: 'PERDIDA', cls: 'bg-red-100 text-red-700' },
    void: { label: 'ANULADA', cls: 'bg-yellow-100 text-yellow-700' },
  }
  const { label, cls } = map[status] ?? { label: status, cls: 'bg-gray-100 text-gray-500' }
  return (
    <span className={`rounded px-1.5 py-0.5 text-xs font-semibold ${cls}`}>{label}</span>
  )
}

export default function BetList({ bets, onRefresh }: BetListProps) {
  if (bets.length === 0) {
    return <p className="py-4 text-sm text-gray-500">No hay apuestas registradas.</p>
  }

  async function handleDelete(id: number) {
    if (!window.confirm('¿Confirmas eliminar esta apuesta?')) return
    await fetchAPI(`/v1/bets/${id}`, { method: 'DELETE' })
    onRefresh()
  }

  const sorted = [...bets].sort((a, b) => {
    if (!a.placed_at) return 1
    if (!b.placed_at) return -1
    return b.placed_at.localeCompare(a.placed_at)
  })

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b text-xs uppercase text-gray-500">
            <th className="py-2 text-left">Partido</th>
            <th className="py-2 text-left">Pick</th>
            <th className="py-2 text-right">Cuota</th>
            <th className="py-2 text-right">Stake</th>
            <th className="py-2 text-center">Estado</th>
            <th className="py-2 text-right">PnL</th>
            <th className="py-2" />
          </tr>
        </thead>
        <tbody>
          {sorted.map((bet) => {
            const canDelete = bet.mode === 'real' && bet.status === 'pending'
            const pnlValue = bet.pnl ? parseFloat(bet.pnl) : null
            const stakeValue = parseFloat(bet.stake)

            return (
              <tr key={bet.id} className="border-b hover:bg-gray-50">
                <td className="py-2 pr-3">
                  Partido #{bet.match_id ?? '—'}
                </td>
                <td className="py-2 pr-3">{humanizeOutcome(bet.outcome_code)}</td>
                <td className="py-2 pr-3 text-right">{bet.odds_taken.toFixed(2)}</td>
                <td className="py-2 pr-3 text-right">{formatCop(stakeValue)}</td>
                <td className="py-2 text-center">
                  <StatusBadge status={bet.status} />
                </td>
                <td className={`py-2 text-right font-medium ${
                  pnlValue === null
                    ? 'text-gray-400'
                    : pnlValue >= 0
                    ? 'text-green-600'
                    : 'text-red-600'
                }`}>
                  {pnlValue !== null ? formatPnl(pnlValue) : '—'}
                </td>
                <td className="py-2 pl-2">
                  {canDelete && (
                    <button
                      type="button"
                      onClick={() => handleDelete(bet.id)}
                      aria-label="Eliminar apuesta"
                      className="rounded px-2 py-0.5 text-xs text-red-600 hover:bg-red-50 focus:outline-none focus:ring-1 focus:ring-red-500"
                    >
                      Eliminar
                    </button>
                  )}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
