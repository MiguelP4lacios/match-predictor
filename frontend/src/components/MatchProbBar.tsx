import { formatProbability } from '../lib/formatters'
import type { UpcomingMatch } from '../api/types'

interface MatchProbBarProps {
  match: UpcomingMatch
}

export default function MatchProbBar({ match }: MatchProbBarProps) {
  const { home_team, away_team, p_home, p_draw, p_away, low_confidence } = match
  const hasProbabilities = p_home !== null && p_draw !== null && p_away !== null

  return (
    <div className="rounded border bg-white p-3 shadow-sm">
      <div className="mb-2 flex items-center justify-between">
        <span className="font-medium">
          {home_team} vs {away_team}
        </span>
        {low_confidence && (
          <span className="rounded bg-yellow-100 px-2 py-0.5 text-xs text-yellow-700">
            ⚠ datos limitados
          </span>
        )}
      </div>

      {hasProbabilities && (
        <div className="space-y-1 text-xs">
          <div className="flex items-center gap-2">
            <span className="w-12 text-right text-gray-500">Local</span>
            <div className="flex-1 overflow-hidden rounded bg-gray-100">
              <div
                className="h-4 rounded bg-blue-500"
                style={{ width: `${p_home! * 100}%` }}
              />
            </div>
            <span className="w-12">{formatProbability(p_home!)}</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-12 text-right text-gray-500">Empate</span>
            <div className="flex-1 overflow-hidden rounded bg-gray-100">
              <div
                className="h-4 rounded bg-gray-400"
                style={{ width: `${p_draw! * 100}%` }}
              />
            </div>
            <span className="w-12">{formatProbability(p_draw!)}</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-12 text-right text-gray-500">Visita</span>
            <div className="flex-1 overflow-hidden rounded bg-gray-100">
              <div
                className="h-4 rounded bg-red-400"
                style={{ width: `${p_away! * 100}%` }}
              />
            </div>
            <span className="w-12">{formatProbability(p_away!)}</span>
          </div>
        </div>
      )}
    </div>
  )
}
