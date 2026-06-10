import { useQuery } from '@tanstack/react-query'
import { fetchAPI } from '../api/client'
import type { ModelInfo, CalibrationBin } from '../api/types'
import Loading from '../components/Loading'
import ErrorBanner from '../components/ErrorBanner'

export default function ModelPage() {
  const { data, isLoading, isError, refetch } = useQuery<ModelInfo>({
    queryKey: ['model'],
    queryFn: () => fetchAPI<ModelInfo>('/v1/model'),
    staleTime: 300_000, // 5 min — datos de backtest no cambian con polling rápido
  })

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-bold">Modelo</h1>

      {isLoading && <Loading />}
      {isError && <ErrorBanner onRetry={() => refetch()} />}

      {data && (
        <>
          {/* Semáforo */}
          <div className="rounded border bg-white p-4 shadow-sm">
            <p className="text-lg font-semibold">
              {data.backtest.beats_baselines
                ? '✅ Supera baselines'
                : '❌ No supera baselines'}
            </p>
            <p className="mt-1 text-sm text-gray-500">
              Evaluado sobre {data.backtest.eval_n} partidos ({data.backtest.eval_window})
            </p>
          </div>

          {/* Métricas vs baselines */}
          <div className="rounded border bg-white shadow-sm">
            <div className="border-b bg-gray-50 px-4 py-2 font-semibold">
              Métricas vs Baselines
            </div>
            <div className="overflow-x-auto">
              <table className="w-full border-collapse text-sm">
                <thead>
                  <tr className="border-b text-xs font-semibold uppercase text-gray-500">
                    <th className="px-3 py-2 text-left">Métrica</th>
                    <th className="px-3 py-2 text-right">Modelo</th>
                    {Object.keys(data.backtest.baselines).map((k) => (
                      <th key={k} className="px-3 py-2 text-right capitalize">
                        {k}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  <tr className="border-b">
                    <td className="px-3 py-2 font-medium">Brier</td>
                    <td className="px-3 py-2 text-right font-semibold">
                      {data.backtest.brier.toFixed(4)}
                    </td>
                    {Object.values(data.backtest.baselines).map((v, i) => (
                      <td key={i} className="px-3 py-2 text-right text-gray-500">
                        {v.toFixed(4)}
                      </td>
                    ))}
                  </tr>
                  <tr>
                    <td className="px-3 py-2 font-medium">Log-loss</td>
                    <td className="px-3 py-2 text-right font-semibold">
                      {data.backtest.logloss.toFixed(4)}
                    </td>
                    {Object.values(data.backtest.baselines).map((_, i) => (
                      <td key={i} className="px-3 py-2 text-right text-gray-500">
                        —
                      </td>
                    ))}
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          {/* Tabla de calibración */}
          {data.backtest.calibration_table.length > 0 ? (
            <CalibrationTable bins={data.backtest.calibration_table} />
          ) : (
            <p className="py-4 text-center text-gray-500">Sin datos de calibración</p>
          )}
        </>
      )}
    </div>
  )
}

function CalibrationTable({ bins }: { bins: CalibrationBin[] }) {
  return (
    <div className="rounded border bg-white shadow-sm">
      <div className="border-b bg-gray-50 px-4 py-2 font-semibold">
        Calibración (backtest)
      </div>
      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr className="border-b text-xs font-semibold uppercase text-gray-500">
              <th className="px-3 py-2 text-left">Bin</th>
              <th className="px-3 py-2 text-right">Pred. media</th>
              <th className="px-3 py-2 text-right">Frec. obs.</th>
              <th className="px-3 py-2 text-right">N</th>
            </tr>
          </thead>
          <tbody>
            {bins.map((bin, i) => (
              <tr key={i} className="border-b last:border-0 hover:bg-gray-50">
                <td className="px-3 py-2 text-gray-500">
                  {(bin.bin_low * 100).toFixed(0)}%–{(bin.bin_high * 100).toFixed(0)}%
                </td>
                <td className="px-3 py-2 text-right">
                  {(bin.mean_predicted * 100).toFixed(1)}%
                </td>
                <td className="px-3 py-2 text-right">
                  {(bin.observed_freq * 100).toFixed(1)}%
                </td>
                <td className="px-3 py-2 text-right text-gray-500">{bin.count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
