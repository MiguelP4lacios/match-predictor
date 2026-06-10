import { useQuery } from '@tanstack/react-query'
import { fetchAPI } from '../api/client'
import type { GroupItem } from '../api/types'
import GroupCard from '../components/GroupCard'
import Loading from '../components/Loading'
import ErrorBanner from '../components/ErrorBanner'

export default function GroupsPage() {
  const { data, isLoading, isError, refetch } = useQuery<GroupItem[]>({
    queryKey: ['groups'],
    queryFn: () => fetchAPI<GroupItem[]>('/v1/groups'),
    staleTime: 60_000,
    refetchInterval: 60_000,
  })

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-bold">Grupos — WC 2026</h1>

      {isLoading && <Loading />}
      {isError && <ErrorBanner onRetry={() => refetch()} />}
      {data && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {data.map((group) => (
            <GroupCard key={group.name} name={group.name} standings={group.standings} />
          ))}
        </div>
      )}
    </div>
  )
}
