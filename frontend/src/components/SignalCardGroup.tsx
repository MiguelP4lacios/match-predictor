import { groupSignals } from '../lib/groupSignals'
import SignalCard from './SignalCard'
import type { SignalItem } from '../api/types'

interface SignalCardGroupProps {
  items: SignalItem[]
  onExplain: (id: number) => void
}

/**
 * Agrupa señales por partido usando `groupSignals` (función pura reutilizada).
 * - Grupos con ≥2 señales muestran el hint de exposición correlacionada.
 * - Grupos con 1 señal no muestran el hint.
 * - El orden de grupos = primera aparición en la respuesta del servidor.
 */
export default function SignalCardGroup({ items, onExplain }: SignalCardGroupProps) {
  if (items.length === 0) {
    return (
      <p className="py-8 text-center text-text-muted">
        Sin señales con ese filtro
      </p>
    )
  }

  const groups = groupSignals(items)

  return (
    <div className="space-y-6">
      {groups.map((group) => (
        <div key={group.match_key}>
          {/* Encabezado de grupo */}
          <div className="mb-2">
            <span
              data-testid="group-header"
              className="text-sm font-semibold text-text"
            >
              {group.home_team} vs {group.away_team}
            </span>
            <span className="ml-2 text-xs text-text-muted">{group.match_date}</span>
          </div>

          {/* Hint de exposición correlacionada */}
          {group.signals.length >= 2 && (
            <p className="mb-2 text-xs font-medium text-warn">
              ⚠ {group.signals.length} señales sobre este partido — exposición correlacionada
            </p>
          )}

          {/* Cards del grupo */}
          <div className="space-y-3">
            {group.signals.map((signal) => (
              <SignalCard key={signal.id} signal={signal} onExplain={onExplain} />
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}
