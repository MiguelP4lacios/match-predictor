import { useQuery } from '@tanstack/react-query'
import { fetchAPI } from '../api/client'
import type { UpcomingMatch } from '../api/types'
import MatchProbBar from '../components/MatchProbBar'
import Loading from '../components/Loading'
import ErrorBanner from '../components/ErrorBanner'

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
    queryFn: () => fetchAPI<UpcomingMatch[]>('/v1/matches/upcoming'),
    staleTime: 55_000,
    refetchInterval: 60_000,
  })

  const groups = data ? groupByDate(data) : []

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-bold">Partidos</h1>

      {isLoading && <Loading />}
      {isError && <ErrorBanner onRetry={() => refetch()} />}

      {data && data.length === 0 && (
        <p className="py-8 text-center text-gray-500">No hay partidos próximos.</p>
      )}

      {groups.map(([date, matches]) => (
        <div key={date} className="space-y-2">
          <h2 className="border-b pb-1 text-sm font-semibold text-gray-500">{date}</h2>
          {matches.map((match) => (
            <MatchProbBar key={match.id} match={match} />
          ))}
        </div>
      ))}
    </div>
  )
}
