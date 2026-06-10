import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchAPI } from '../api/client'
import type { SignalsResponse } from '../api/types'
import SignalsTable from '../components/SignalsTable'
import Loading from '../components/Loading'
import ErrorBanner from '../components/ErrorBanner'

export default function SignalsPage() {
  const [minEdge, setMinEdge] = useState('')

  const params = new URLSearchParams()
  if (minEdge) params.set('min_edge', minEdge)
  params.set('limit', '100')
  const qs = params.toString()

  const { data, isLoading, isError, refetch } = useQuery<SignalsResponse>({
    queryKey: ['signals', minEdge],
    queryFn: () => fetchAPI<SignalsResponse>(`/v1/signals?${qs}`),
    staleTime: 55_000,
    refetchInterval: 60_000,
  })

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold">Señales +EV</h1>
        <div className="flex items-center gap-2">
          <label htmlFor="min-edge" className="text-sm text-gray-600">
            Edge mínimo
          </label>
          <select
            id="min-edge"
            value={minEdge}
            onChange={(e) => setMinEdge(e.target.value)}
            className="rounded border px-2 py-1 text-sm"
          >
            <option value="">Todos</option>
            <option value="0.05">5%</option>
            <option value="0.10">10%</option>
            <option value="0.15">15%</option>
            <option value="0.20">20%</option>
          </select>
        </div>
      </div>

      {isLoading && <Loading />}
      {isError && <ErrorBanner onRetry={() => refetch()} />}
      {data && <SignalsTable items={data.items} />}
    </div>
  )
}
