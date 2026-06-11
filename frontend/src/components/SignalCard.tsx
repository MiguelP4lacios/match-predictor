import { useNavigate } from 'react-router-dom'
import { formatEdge, formatStake, formatOdds } from '../lib/formatters'
import type { SignalItem } from '../api/types'
import { Card } from '../ui/Card'
import { Badge } from '../ui/Badge'
import { Button } from '../ui/Button'
import { FlagLabel } from '../ui/FlagLabel'
import AddToCuponButton from './AddToCuponButton'

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
    <Card>
      {/* Header: fecha + partido */}
      <p className="mb-2 text-xs text-text-muted">
        {signal.match_date} · {signal.home_team} vs {signal.away_team}
      </p>

      {/* Apuesta */}
      <p data-testid="bet-label" className="mb-3 text-lg font-bold text-text">
        <span aria-hidden="true">🎯 </span>
        <span>Apostale a </span>
        {signal.outcome_code === 'DRAW' ? (
          <span>{outcomeLabel}</span>
        ) : (
          <FlagLabel team={outcomeLabel} size="md" />
        )}
      </p>

      {/* Cuota + bookmaker */}
      <p className="mb-2 text-sm text-text">
        {formatOdds(signal.best_odds)} ({signal.bookmaker})
      </p>

      {/* Edge badge — prominente, color success */}
      <div className="mb-2 flex items-center gap-2">
        <Badge variant="success" className="text-sm font-semibold">
          {formatEdge(signal.edge)}
        </Badge>
        <span className="text-xs text-text-muted">la cuota paga de más</span>
      </div>

      {/* Stake sugerido */}
      <p className="mb-3 text-sm text-text">
        Sugerido: <span className="font-semibold">${formatStake(signal.recommended_stake)}</span>
      </p>

      {/* CTAs */}
      <div className="flex flex-wrap gap-2">
        <Button
          variant="primary"
          size="md"
          onClick={() => onExplain(signal.id)}
        >
          ¿Por qué? →
        </Button>

        {signal.match_id !== null && signal.match_id !== undefined && (
          <Button
            variant="secondary"
            size="md"
            onClick={() =>
              navigate(
                `/apuestas?match_id=${signal.match_id}&outcome=${signal.outcome_code}&odds=${signal.best_odds}`,
              )
            }
          >
            Registrar apuesta
          </Button>
        )}

        {signal.match_id !== null && signal.match_id !== undefined && signal.outcome_code !== null && signal.outcome_code !== undefined && (
          <AddToCuponButton
            matchId={signal.match_id}
            outcomeCode={signal.outcome_code as 'HOME' | 'DRAW' | 'AWAY'}
            homeTeam={signal.home_team}
            awayTeam={signal.away_team}
            matchDate={signal.match_date}
          />
        )}
      </div>
    </Card>
  )
}
