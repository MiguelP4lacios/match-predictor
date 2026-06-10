import { formatROI } from '../lib/formatters'
import type { PaperStats as PaperStatsType } from '../api/types'

interface PaperStatsProps {
  stats: PaperStatsType
}

export default function PaperStats({ stats }: PaperStatsProps) {
  return (
    <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
      <StatCard label="Total apuestas" value={String(stats.total)} />
      <StatCard label="Abiertas" value={String(stats.open)} />
      <StatCard label="Cerradas" value={String(stats.settled)} />
      <StatCard
        label="ROI"
        value={formatROI(stats.roi)}
        highlight={stats.roi !== null && stats.roi > 0}
      />
    </div>
  )
}

interface StatCardProps {
  label: string
  value: string
  highlight?: boolean
}

function StatCard({ label, value, highlight = false }: StatCardProps) {
  return (
    <div className="rounded border bg-white p-4 shadow-sm">
      <p className="text-xs font-medium uppercase text-gray-500">{label}</p>
      <p
        className={`mt-1 text-2xl font-bold ${
          highlight ? 'text-green-600' : 'text-gray-800'
        }`}
      >
        {value}
      </p>
    </div>
  )
}
