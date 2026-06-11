import { useQuery } from '@tanstack/react-query'
import { fetchAPI } from '../api/client'
import type { ModelInfo, CalibrationBin } from '../api/types'
import { Card } from '../ui/Card'
import { Stat } from '../ui/Stat'
import { Badge } from '../ui/Badge'
import { Spinner } from '../ui/Spinner'
import { ErrorState } from '../ui/ErrorState'

export default function ModelPage() {
  const { data, isLoading, isError, refetch } = useQuery<ModelInfo>({
    queryKey: ['model'],
    queryFn: () => fetchAPI<ModelInfo>('/v1/model'),
    staleTime: 300_000, // 5 min — datos de backtest no cambian con polling rápido
  })

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-bold text-text">Modelo</h1>

      {isLoading && <Spinner />}
      {isError && <ErrorState onRetry={() => refetch()} />}

      {data && (
        <>
          {/* Semáforo + métricas hero */}
          <Card>
            <div className="mb-3 flex items-center gap-3">
              <p className="text-lg font-semibold text-text">
                {data.backtest.beats_baselines
                  ? '✅ Supera baselines'
                  : '❌ No supera baselines'}
              </p>
              <Badge variant={data.backtest.beats_baselines ? 'success' : 'danger'}>
                {data.backtest.beats_baselines ? 'Calibrado' : 'Sin calibrar'}
              </Badge>
            </div>
            <p className="mb-4 text-sm text-text-muted">
              Evaluado sobre {data.backtest.eval_n} partidos ({data.backtest.eval_window})
            </p>

            {/* Stat cards — métricas principales */}
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
              <Stat label="Brier" value={data.backtest.brier.toFixed(4)} />
              <Stat label="Log-loss" value={data.backtest.logloss.toFixed(4)} />
              <Stat label="Partidos" value={String(data.backtest.eval_n)} />
              <Stat label="Ventana" value={data.backtest.eval_window} />
            </div>
          </Card>

          {/* Tabla calibración */}
          {data.backtest.calibration_table.length > 0 ? (
            <CalibrationTable bins={data.backtest.calibration_table} />
          ) : (
            <p className="py-4 text-center text-text-muted">Sin datos de calibración</p>
          )}
        </>
      )}
    </div>
  )
}

function CalibrationTable({ bins }: { bins: CalibrationBin[] }) {
  return (
    <Card title="Calibración (backtest)">
      <table className="w-full border-collapse text-sm">
        <thead>
          <tr className="border-b border-border text-xs font-semibold uppercase text-text-muted">
            <th className="px-3 py-2 text-left">Bin</th>
            <th className="px-3 py-2 text-right">Pred. media</th>
            <th className="px-3 py-2 text-right">Frec. obs.</th>
            <th className="px-3 py-2 text-right">N</th>
          </tr>
        </thead>
        <tbody>
          {bins.map((bin, i) => (
            <tr key={i} className="border-b border-border last:border-0 hover:bg-bg">
              <td className="px-3 py-2 text-text-muted">
                {(bin.bin_low * 100).toFixed(0)}%–{(bin.bin_high * 100).toFixed(0)}%
              </td>
              <td className="px-3 py-2 text-right text-text">
                {(bin.mean_predicted * 100).toFixed(1)}%
              </td>
              <td className="px-3 py-2 text-right text-text">
                {(bin.observed_freq * 100).toFixed(1)}%
              </td>
              <td className="px-3 py-2 text-right text-text-muted">{bin.count}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </Card>
  )
}
