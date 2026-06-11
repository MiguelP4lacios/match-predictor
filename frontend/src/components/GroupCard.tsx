import { useState, Fragment } from 'react'
import { Card } from '../ui/Card'
import { FlagLabel } from '../ui/FlagLabel'
import type { StandingRow } from '../api/types'

interface GroupCardProps {
  name: string
  standings: StandingRow[]
}

export default function GroupCard({ name, standings }: GroupCardProps) {
  const [expandedRow, setExpandedRow] = useState<number | null>(null)

  function toggleRow(idx: number) {
    setExpandedRow((prev) => (prev === idx ? null : idx))
  }

  return (
    <Card title={name}>
      <table className="w-full border-collapse text-sm">
        <thead>
          <tr className="border-b border-border text-xs font-semibold uppercase text-text-muted">
            <th className="px-2 py-2 text-center">Pos</th>
            <th className="px-2 py-2 text-left">Equipo</th>
            <th className="px-2 py-2 text-center">PJ</th>
            <th className="hidden px-2 py-2 text-center md:table-cell">G</th>
            <th className="hidden px-2 py-2 text-center md:table-cell">E</th>
            <th className="hidden px-2 py-2 text-center md:table-cell">P</th>
            <th className="hidden px-2 py-2 text-center md:table-cell">GF</th>
            <th className="hidden px-2 py-2 text-center md:table-cell">GC</th>
            <th className="px-2 py-2 text-center">DG</th>
            <th className="px-2 py-2 text-center">Pts</th>
          </tr>
        </thead>
        <tbody>
          {standings.map((row, idx) => {
            const isQualify = idx < 2
            const isExpanded = expandedRow === idx
            return (
              <Fragment key={row.team_name}>
                <tr
                  data-qualify={isQualify ? 'true' : undefined}
                  onClick={() => toggleRow(idx)}
                  className={`cursor-pointer border-b border-border last:border-0 hover:bg-bg ${
                    isQualify ? 'border-l-2 border-l-qualify' : ''
                  }`}
                >
                  <td className="px-2 py-2 text-center text-text-muted">{idx + 1}</td>
                  <td className="px-2 py-2 font-medium">
                    <FlagLabel team={row.team_name} size="sm" />
                  </td>
                  <td className="px-2 py-2 text-center">{row.pj}</td>
                  <td className="hidden px-2 py-2 text-center md:table-cell">{row.g}</td>
                  <td className="hidden px-2 py-2 text-center md:table-cell">{row.e}</td>
                  <td className="hidden px-2 py-2 text-center md:table-cell">{row.p}</td>
                  <td className="hidden px-2 py-2 text-center md:table-cell">{row.gf}</td>
                  <td className="hidden px-2 py-2 text-center md:table-cell">{row.gc}</td>
                  <td className="px-2 py-2 text-center">{row.dg}</td>
                  <td className="px-2 py-2 text-center font-semibold">{row.pts}</td>
                </tr>
                {isExpanded && (
                  <tr
                    data-testid={`expanded-${idx}`}
                    className="border-b border-border bg-bg md:hidden"
                  >
                    <td colSpan={10} className="px-4 py-2">
                      <div className="flex flex-wrap gap-4 text-xs text-text-muted">
                        <span><span className="font-semibold text-text">G</span> {row.g}</span>
                        <span><span className="font-semibold text-text">E</span> {row.e}</span>
                        <span><span className="font-semibold text-text">P</span> {row.p}</span>
                        <span><span className="font-semibold text-text">GF</span> {row.gf}</span>
                        <span><span className="font-semibold text-text">GC</span> {row.gc}</span>
                      </div>
                    </td>
                  </tr>
                )}
              </Fragment>
            )
          })}
        </tbody>
      </table>
    </Card>
  )
}
