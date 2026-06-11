/**
 * AddToCuponButton — botón reutilizable para agregar un leg al cupón.
 * Usado en SignalCard y en las filas de MatchesPage.
 *
 * Al pulsar, llama addLeg del CuponContext con odds=null
 * (el usuario las completa dentro del CuponDrawer).
 */

import { useCupon } from '../context/CuponContext'

interface AddToCuponButtonProps {
  matchId: number
  outcomeCode: 'HOME' | 'DRAW' | 'AWAY'
  homeTeam: string
  awayTeam: string
  matchDate: string
}

/** Etiqueta del pick: el equipo al que se le apuesta, o "Empate". */
function pickLabel(outcomeCode: 'HOME' | 'DRAW' | 'AWAY', homeTeam: string, awayTeam: string): string {
  if (outcomeCode === 'HOME') return homeTeam
  if (outcomeCode === 'AWAY') return awayTeam
  return 'Empate'
}

export default function AddToCuponButton({
  matchId,
  outcomeCode,
  homeTeam,
  awayTeam,
  matchDate,
}: AddToCuponButtonProps) {
  const { addLeg } = useCupon()
  const label = pickLabel(outcomeCode, homeTeam, awayTeam)

  return (
    <button
      type="button"
      aria-label={`Agregar al cupón: ${label}`}
      onClick={() => addLeg({ match_id: matchId, outcome_code: outcomeCode, home_team: homeTeam, away_team: awayTeam, match_date: matchDate })}
      className="rounded border border-green-600 px-3 py-1.5 text-sm font-medium text-green-700 hover:bg-green-50 focus:outline-none focus:ring-2 focus:ring-green-500"
    >
      + {label}
    </button>
  )
}
