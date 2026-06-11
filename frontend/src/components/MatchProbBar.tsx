import { formatProbability } from '../lib/formatters'
import type { UpcomingMatch } from '../api/types'
import { Card } from '../ui/Card'
import { Badge } from '../ui/Badge'
import { FlagLabel } from '../ui/FlagLabel'

interface MatchProbBarProps {
  match: UpcomingMatch
}

export default function MatchProbBar({ match }: MatchProbBarProps) {
  const { home_team, away_team, p_home, p_draw, p_away, low_confidence } = match
  const hasProbabilities = p_home !== null && p_draw !== null && p_away !== null

  return (
    <Card>
      <div className="mb-2 flex items-center justify-between">
        <div data-testid="match-header" className="flex items-center gap-1 font-medium text-text">
          <FlagLabel team={home_team} size="sm" />
          <span className="text-text-muted"> vs </span>
          <FlagLabel team={away_team} size="sm" />
        </div>
        {low_confidence && (
          <Badge variant="warn">⚠ datos limitados</Badge>
        )}
      </div>

      {hasProbabilities && (
        <div className="space-y-1 text-xs">
          <div className="flex items-center gap-2">
            <span className="w-12 text-right text-text-muted">Local</span>
            <div className="flex-1 overflow-hidden rounded bg-border/30">
              <div
                className="h-4 rounded bg-primary"
                style={{ width: `${p_home! * 100}%` }}
              />
            </div>
            <span className="w-12 text-text">{formatProbability(p_home!)}</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-12 text-right text-text-muted">Empate</span>
            <div className="flex-1 overflow-hidden rounded bg-border/30">
              <div
                className="h-4 rounded bg-border"
                style={{ width: `${p_draw! * 100}%` }}
              />
            </div>
            <span className="w-12 text-text">{formatProbability(p_draw!)}</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-12 text-right text-text-muted">Visita</span>
            <div className="flex-1 overflow-hidden rounded bg-border/30">
              <div
                className="h-4 rounded bg-danger/60"
                style={{ width: `${p_away! * 100}%` }}
              />
            </div>
            <span className="w-12 text-text">{formatProbability(p_away!)}</span>
          </div>
        </div>
      )}
    </Card>
  )
}
