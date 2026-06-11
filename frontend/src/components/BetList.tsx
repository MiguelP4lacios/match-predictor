/**
 * BetList — lista de apuestas con estado coloreado y PnL formateado.
 * - Filas ordenadas por placed_at DESC
 * - Delete solo REAL PENDING → confirm → DELETE /api/v1/bets/{id}
 */
import { fetchAPI } from '../api/client'
import { formatCop, formatPnl } from '../lib/formatters'
import type { BetItem } from '../api/types'
import { Badge, type BadgeVariant } from '../ui/Badge'
import { Button } from '../ui/Button'

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

const STATUS_CONFIG: Record<string, { label: string; variant: BadgeVariant }> = {
  pending: { label: 'PENDIENTE', variant: 'neutral' },
  won: { label: 'GANADA', variant: 'success' },
  lost: { label: 'PERDIDA', variant: 'danger' },
  void: { label: 'ANULADA', variant: 'warn' },
}

export default function BetList({ bets, onRefresh }: BetListProps) {
  if (bets.length === 0) {
    return <p className="py-4 text-sm text-text-muted">No hay apuestas registradas.</p>
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
          <tr className="border-b border-border text-xs uppercase text-text-muted">
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
            const statusConf = STATUS_CONFIG[bet.status] ?? { label: bet.status, variant: 'neutral' as BadgeVariant }

            return (
              <tr key={bet.id} className="border-b border-border hover:bg-bg">
                <td className="py-2 pr-3 text-text">
                  Partido #{bet.match_id ?? '—'}
                </td>
                <td className="py-2 pr-3 text-text">{humanizeOutcome(bet.outcome_code)}</td>
                <td className="py-2 pr-3 text-right text-text">{bet.odds_taken.toFixed(2)}</td>
                <td className="py-2 pr-3 text-right text-text">{formatCop(stakeValue)}</td>
                <td className="py-2 text-center">
                  <Badge variant={statusConf.variant}>{statusConf.label}</Badge>
                </td>
                <td className={`py-2 text-right font-medium ${
                  pnlValue === null
                    ? 'text-text-muted'
                    : pnlValue >= 0
                    ? 'text-success'
                    : 'text-danger'
                }`}>
                  {pnlValue !== null ? formatPnl(pnlValue) : '—'}
                </td>
                <td className="py-2 pl-2">
                  {canDelete && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleDelete(bet.id)}
                      aria-label="Eliminar apuesta"
                      className="text-danger hover:bg-danger/10"
                    >
                      Eliminar
                    </Button>
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
