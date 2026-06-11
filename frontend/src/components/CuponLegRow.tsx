/**
 * CuponLegRow — fila de una pierna dentro del CuponDrawer.
 * Muestra partido, pick, input de cuota BetPlay y warning −EV si aplica.
 */

import type { CuponLeg } from '../context/CuponContext'
import type { LegDiagnostic } from '../api/types'

interface CuponLegRowProps {
  leg: CuponLeg
  diagnostic?: LegDiagnostic
  onOddsChange(match_id: number, outcome_code: string, odds: number | null): void
  onRemove(match_id: number, outcome_code: string): void
}

function humanizeOutcome(code: string, homeTeam: string, awayTeam: string): string {
  if (code === 'HOME') return homeTeam
  if (code === 'DRAW') return 'Empate'
  if (code === 'AWAY') return awayTeam
  return code
}

export default function CuponLegRow({ leg, diagnostic, onOddsChange, onRemove }: CuponLegRowProps) {
  const pick = humanizeOutcome(leg.outcome_code, leg.home_team, leg.away_team)

  return (
    <div className="rounded border border-gray-200 bg-gray-50 p-2 text-sm">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <p className="truncate font-medium text-gray-800">
            {leg.home_team} vs {leg.away_team}
          </p>
          <p className="text-xs text-gray-500">
            {leg.match_date} · <span className="font-semibold">{pick}</span>
          </p>
        </div>
        <button
          type="button"
          aria-label={`Quitar ${pick}`}
          onClick={() => onRemove(leg.match_id, leg.outcome_code)}
          className="ml-1 shrink-0 rounded p-0.5 text-gray-400 hover:text-red-500"
        >
          ×
        </button>
      </div>

      {/* Input de cuota BetPlay */}
      <div className="mt-1.5 flex items-center gap-2">
        <label className="text-xs text-gray-500">Cuota BetPlay:</label>
        <input
          type="number"
          step="0.01"
          min="1.01"
          placeholder="1.40"
          defaultValue={leg.odds ?? ''}
          aria-label={`Cuota ${pick}`}
          onChange={(e) => {
            const val = e.target.value ? Number(e.target.value) : null
            onOddsChange(leg.match_id, leg.outcome_code, val)
          }}
          className="w-20 rounded border border-gray-300 px-2 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-blue-400"
        />
      </div>

      {/* Warning −EV */}
      {diagnostic?.is_negative_ev && (
        <p className="mt-1 text-xs font-medium text-amber-600">
          ⚠ Este leg reduce el EV del cupón
        </p>
      )}
    </div>
  )
}
