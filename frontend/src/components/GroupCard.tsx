import type { StandingRow } from '../api/types'

interface GroupCardProps {
  name: string
  standings: StandingRow[]
}

export default function GroupCard({ name, standings }: GroupCardProps) {
  return (
    <div className="rounded border bg-white shadow-sm">
      <div className="border-b bg-gray-50 px-4 py-2 font-semibold">{name}</div>
      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr className="border-b text-xs font-semibold uppercase text-gray-500">
              <th className="px-2 py-2 text-center">Pos</th>
              <th className="px-2 py-2 text-left">Equipo</th>
              <th className="px-2 py-2 text-center">PJ</th>
              <th className="px-2 py-2 text-center">G</th>
              <th className="px-2 py-2 text-center">E</th>
              <th className="px-2 py-2 text-center">P</th>
              <th className="px-2 py-2 text-center">GF</th>
              <th className="px-2 py-2 text-center">GC</th>
              <th className="px-2 py-2 text-center">DG</th>
              <th className="px-2 py-2 text-center">Pts</th>
            </tr>
          </thead>
          <tbody>
            {standings.map((row, idx) => (
              <tr key={row.team_name} className="border-b last:border-0 hover:bg-gray-50">
                <td className="px-2 py-2 text-center text-gray-500">{idx + 1}</td>
                <td className="px-2 py-2 font-medium">{row.team_name}</td>
                <td className="px-2 py-2 text-center">{row.pj}</td>
                <td className="px-2 py-2 text-center">{row.g}</td>
                <td className="px-2 py-2 text-center">{row.e}</td>
                <td className="px-2 py-2 text-center">{row.p}</td>
                <td className="px-2 py-2 text-center">{row.gf}</td>
                <td className="px-2 py-2 text-center">{row.gc}</td>
                <td className="px-2 py-2 text-center">{row.dg}</td>
                <td className="px-2 py-2 text-center font-semibold">{row.pts}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
