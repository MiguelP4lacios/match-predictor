import { Fragment } from 'react'
import { formatEdge, formatProbability, formatStake, formatOdds } from '../lib/formatters'
import { groupSignals } from '../lib/groupSignals'
import type { SignalItem } from '../api/types'

interface SignalsTableProps {
  items: SignalItem[]
}

const OUTCOME_LABEL: Record<string, (home: string, away: string) => string> = {
  HOME: (home) => home,
  DRAW: () => 'Empate',
  AWAY: (_home, away) => away,
}

export default function SignalsTable({ items }: SignalsTableProps) {
  if (items.length === 0) {
    return (
      <p className="py-8 text-center text-gray-500">
        Sin señales con ese filtro
      </p>
    )
  }

  const groups = groupSignals(items)

  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-sm">
        <thead>
          <tr className="border-b bg-gray-50 text-left text-xs font-semibold uppercase text-gray-500">
            <th className="px-3 py-2">Apostar a</th>
            <th className="px-3 py-2">P(model)</th>
            <th className="px-3 py-2">Mejor cuota</th>
            <th className="px-3 py-2">Edge</th>
            <th className="px-3 py-2">Stake</th>
          </tr>
        </thead>
        <tbody>
          {groups.map((group) => (
            <Fragment key={group.match_key}>
              {/* Encabezado de grupo: fecha + partido + hint opcional */}
              <tr className="border-b bg-blue-50">
                <td colSpan={5} className="px-3 py-2">
                  <span className="text-xs text-gray-500">{group.match_date}</span>
                  {' '}
                  <span className="font-semibold">{group.home_team} vs {group.away_team}</span>
                  {group.signals.length >= 2 && (
                    <span className="ml-2 text-xs font-medium text-amber-700">
                      ⚠ {group.signals.length} señales sobre este partido — exposición correlacionada
                    </span>
                  )}
                </td>
              </tr>

              {/* Filas de señales del grupo */}
              {group.signals.map((signal) => {
                const outcomeFn = OUTCOME_LABEL[signal.outcome_code] ?? (() => signal.outcome_code)
                return (
                  <tr key={signal.id} className="border-b hover:bg-gray-50">
                    <td className="px-3 py-2">
                      {outcomeFn(signal.home_team, signal.away_team)}
                    </td>
                    <td className="px-3 py-2">{formatProbability(signal.p_model)}</td>
                    <td className="px-3 py-2">
                      {formatOdds(signal.best_odds)}{' '}
                      <span className="text-xs text-gray-400">{signal.bookmaker}</span>
                    </td>
                    <td className="px-3 py-2 font-semibold text-green-700">
                      {formatEdge(signal.edge)}
                    </td>
                    <td className="px-3 py-2">{formatStake(signal.recommended_stake)}</td>
                  </tr>
                )
              })}
            </Fragment>
          ))}
        </tbody>
      </table>
    </div>
  )
}
