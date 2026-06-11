import { useQuery } from '@tanstack/react-query'
import { fetchAPI } from '../api/client'
import type { UpcomingMatch } from '../api/types'
import MatchProbBar from '../components/MatchProbBar'
import AddToCuponButton from '../components/AddToCuponButton'
import { Spinner } from '../ui/Spinner'
import { ErrorState } from '../ui/ErrorState'

/** Agrupa partidos por fecha (ISODate string). Server es autoridad de orden. */
function groupByDate(matches: UpcomingMatch[]): [string, UpcomingMatch[]][] {
  const map = new Map<string, UpcomingMatch[]>()
  for (const m of matches) {
    const key = m.match_date
    if (!map.has(key)) map.set(key, [])
    map.get(key)!.push(m)
  }
  return Array.from(map.entries())
}

export default function MatchesPage() {
  const { data, isLoading, isError, refetch } = useQuery<UpcomingMatch[]>({
    queryKey: ['matches'],
    // limit=200: el default del server (50) cortaría los 72 de grupos (y los 104 con knockouts)
    queryFn: () => fetchAPI<UpcomingMatch[]>('/v1/matches/upcoming?limit=200'),
    staleTime: 55_000,
    refetchInterval: 60_000,
  })

  const groups = data ? groupByDate(data) : []

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-bold text-text">Partidos</h1>

      {isLoading && <Spinner />}
      {isError && <ErrorState onRetry={() => refetch()} />}

      {data && data.length === 0 && (
        <p className="py-8 text-center text-text-muted">No hay partidos próximos.</p>
      )}

      {groups.map(([date, matches]) => (
        <div key={date} className="space-y-2">
          {/* Sticky date header */}
          <h2 className="sticky top-16 z-10 border-b border-border bg-bg pb-1 text-sm font-semibold text-text-muted">
            {date}
          </h2>
          {matches.map((match) => (
            <div key={match.id}>
              <MatchProbBar match={match} />
              <div className="mt-1 flex flex-wrap gap-1 pl-1">
                <AddToCuponButton
                  matchId={match.id}
                  outcomeCode="HOME"
                  homeTeam={match.home_team}
                  awayTeam={match.away_team}
                  matchDate={match.match_date}
                />
                <AddToCuponButton
                  matchId={match.id}
                  outcomeCode="DRAW"
                  homeTeam={match.home_team}
                  awayTeam={match.away_team}
                  matchDate={match.match_date}
                />
                <AddToCuponButton
                  matchId={match.id}
                  outcomeCode="AWAY"
                  homeTeam={match.home_team}
                  awayTeam={match.away_team}
                  matchDate={match.match_date}
                />
              </div>
            </div>
          ))}
        </div>
      ))}
    </div>
  )
}
