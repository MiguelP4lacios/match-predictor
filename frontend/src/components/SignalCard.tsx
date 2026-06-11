import { useNavigate } from 'react-router-dom'
import { formatEdge, formatStake, formatOdds } from '../lib/formatters'
import type { SignalItem } from '../api/types'

interface SignalCardProps {
  signal: SignalItem
  onExplain: (id: number) => void
}

/** Humaniza el código de outcome al nombre del equipo o "Empate". */
function resolveOutcomeLabel(
  outcomeCode: string,
  homeTeam: string,
  awayTeam: string,
): string {
  if (outcomeCode === 'HOME') return homeTeam
  if (outcomeCode === 'DRAW') return 'Empate'
  if (outcomeCode === 'AWAY') return awayTeam
  return outcomeCode
}

/**
 * Tarjeta de señal +EV — lenguaje de hincha, sin aritmética propia.
 * Todos los valores numéricos provienen del servidor y son formateados
 * exclusivamente con `formatters.ts`.
 */
export default function SignalCard({ signal, onExplain }: SignalCardProps) {
  const navigate = useNavigate()
  const outcomeLabel = resolveOutcomeLabel(
    signal.outcome_code,
    signal.home_team,
    signal.away_team,
  )

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
      {/* Header: fecha + partido */}
      <p className="mb-2 text-xs text-gray-500">
        {signal.match_date} · {signal.home_team} vs {signal.away_team}
      </p>

      {/* Apuesta */}
      <p className="mb-3 text-lg font-bold text-gray-900">
        <span aria-hidden="true">🎯 </span>
        <span>Apostale a {outcomeLabel}</span>
      </p>

      {/* Cuota + bookmaker */}
      <p className="mb-2 text-sm text-gray-700">
        {formatOdds(signal.best_odds)} ({signal.bookmaker})
      </p>

      {/* Edge badge — "sobre la cuota", NO sobre el rival: la señal es de VALOR,
          no de favoritismo (el favorito del partido puede ser el otro equipo) */}
      <div className="mb-2 flex items-center gap-2">
        <span className="rounded-full bg-green-100 px-2 py-0.5 text-sm font-semibold text-green-800">
          {formatEdge(signal.edge)}
        </span>
        <span className="text-xs text-gray-500">la cuota paga de más</span>
      </div>

      {/* Stake sugerido */}
      <p className="mb-3 text-sm text-gray-700">
        Sugerido: <span className="font-semibold">${formatStake(signal.recommended_stake)}</span>
      </p>

      {/* CTAs */}
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          onClick={() => onExplain(signal.id)}
          className="rounded bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          ¿Por qué? →
        </button>

        {signal.match_id !== null && signal.match_id !== undefined && (
          <button
            type="button"
            onClick={() =>
              navigate(
                `/apuestas?match_id=${signal.match_id}&outcome=${signal.outcome_code}&odds=${signal.best_odds}`,
              )
            }
            className="rounded border border-blue-600 px-3 py-1.5 text-sm font-medium text-blue-600 hover:bg-blue-50 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            Registrar apuesta
          </button>
        )}
      </div>
    </div>
  )
}
