import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { fetchAPI } from '../api/client'
import type { GroupDetail } from '../api/types'
import GroupCard from '../components/GroupCard'
import MatchProbBar from '../components/MatchProbBar'
import Loading from '../components/Loading'
import ErrorBanner from '../components/ErrorBanner'

export default function GroupDetailPage() {
  const { letra } = useParams<{ letra: string }>()

  const { data, isLoading, isError, refetch } = useQuery<GroupDetail>({
    queryKey: ['group', letra],
    queryFn: () => fetchAPI<GroupDetail>(`/v1/groups/${letra}`),
    staleTime: 60_000,
    refetchInterval: 60_000,
    enabled: !!letra,
  })

  if (!letra) {
    return <p className="py-8 text-center text-gray-500">Grupo no especificado.</p>
  }

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-bold">Grupo {letra.toUpperCase()}</h1>

      {isLoading && <Loading />}
      {isError && (
        <div className="space-y-2">
          <p className="text-gray-600">Grupo desconocido o sin datos.</p>
          <ErrorBanner onRetry={() => refetch()} />
        </div>
      )}

      {data && (
        <>
          <GroupCard name={data.name} standings={data.standings} />

          {data.fixtures && data.fixtures.length > 0 && (
            <div className="space-y-3">
              <h2 className="font-semibold text-gray-700">Partidos</h2>
              {data.fixtures.map((match) => (
                <MatchProbBar
                  key={match.id}
                  match={{
                    id: match.id,
                    match_date: match.match_date,
                    kickoff_at: null,
                    home_team: match.home_team,
                    away_team: match.away_team,
                    neutral_site: false,
                    stage: 'group',
                    p_home: match.p_home,
                    p_draw: match.p_draw,
                    p_away: match.p_away,
                    low_confidence: false,
                  }}
                />
              ))}
            </div>
          )}
        </>
      )}
    </div>
  )
}
