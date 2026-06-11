import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchAPI } from '../api/client'
import type { SignalsResponse } from '../api/types'
import SignalCardGroup from '../components/SignalCardGroup'
import ExplainDrawer from '../components/ExplainDrawer'
import { Spinner } from '../ui/Spinner'
import { ErrorState } from '../ui/ErrorState'

export default function SignalsPage() {
  const [minEdge, setMinEdge] = useState('')
  const [selectedSignalId, setSelectedSignalId] = useState<number | null>(null)

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
        <h1 className="text-xl font-bold text-text">Señales +EV</h1>
        <div className="flex items-center gap-2">
          <label htmlFor="min-edge" className="text-sm text-text-muted">
            Edge mínimo
          </label>
          <select
            id="min-edge"
            value={minEdge}
            onChange={(e) => setMinEdge(e.target.value)}
            className="rounded border border-border bg-surface px-2 py-1 text-sm text-text"
          >
            <option value="">Todos</option>
            <option value="0.05">5%</option>
            <option value="0.10">10%</option>
            <option value="0.15">15%</option>
            <option value="0.20">20%</option>
          </select>
        </div>
      </div>

      {isLoading && <Spinner />}
      {isError && <ErrorState onRetry={() => refetch()} />}
      {data && (
        <SignalCardGroup
          items={data.items}
          onExplain={(id) => setSelectedSignalId(id)}
        />
      )}

      <ExplainDrawer
        signalId={selectedSignalId}
        onClose={() => setSelectedSignalId(null)}
      />
    </div>
  )
}
