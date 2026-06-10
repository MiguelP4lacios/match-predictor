import { useQuery } from '@tanstack/react-query'
import { fetchAPI } from '../api/client'
import type { PaperStats } from '../api/types'
import PaperStatsComponent from '../components/PaperStats'
import Loading from '../components/Loading'
import ErrorBanner from '../components/ErrorBanner'

export default function PaperPage() {
  const { data, isLoading, isError, refetch } = useQuery<PaperStats>({
    queryKey: ['paper'],
    queryFn: () => fetchAPI<PaperStats>('/v1/paper'),
    staleTime: 60_000,
    refetchInterval: 60_000,
  })

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-bold">Paper Trading</h1>

      {isLoading && <Loading />}
      {isError && <ErrorBanner onRetry={() => refetch()} />}
      {data && <PaperStatsComponent stats={data} />}
    </div>
  )
}
