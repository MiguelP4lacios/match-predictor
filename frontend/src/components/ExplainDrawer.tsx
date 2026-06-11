import { useQuery } from '@tanstack/react-query'
import { fetchAPI } from '../api/client'
import type { SignalExplanation, ExplainStep } from '../api/types'
import { Sheet } from '../ui/Sheet'
import { Spinner } from '../ui/Spinner'
import GlossaryTerm from './GlossaryTerm'
import { formatEdge, formatProbability, formatOdds } from '../lib/formatters'

interface ExplainDrawerProps {
  /** ID de la señal a explicar. null = drawer cerrado / no montado. */
  signalId: number | null
  onClose: () => void
}

/**
 * Formatea el valor de un paso:
 * - Si `formatted` está presente → renderiza verbatim (intermedios ilustrativos).
 * - Si `formatted` es null → aplica el formatter canónico según la clave.
 * - Fallback → String(raw).
 */
function formatStepValue(step: ExplainStep): string {
  if (step.formatted !== null && step.formatted !== undefined) return step.formatted
  const { raw, key } = step
  if (raw === null || raw === undefined) return '—'
  if (typeof raw === 'boolean') return raw ? 'Sí' : 'No'
  if (typeof raw === 'string') return `$${parseFloat(raw).toFixed(2)}`
  if (typeof raw === 'number') {
    if (key === 'edge' || key === 'ev') return formatEdge(raw)
    if (key.startsWith('p_') || key === 'kelly_fraction') return formatProbability(raw)
    if (key.includes('odds') || key === 'best_odds') return formatOdds(raw)
    return formatProbability(raw)
  }
  return String(raw)
}

/**
 * Drawer de explicación trazable de una señal +EV.
 * Chrome vía Sheet (backdrop + panel + Escape + botón X).
 */
export default function ExplainDrawer({ signalId, onClose }: ExplainDrawerProps) {
  const { data, isLoading, isError } = useQuery<SignalExplanation>({
    queryKey: ['explain', signalId],
    queryFn: () =>
      fetchAPI<SignalExplanation>(`/v1/signals/${signalId}/explain`),
    enabled: signalId !== null,
  })

  return (
    <Sheet
      open={signalId !== null}
      onClose={onClose}
      title="¿Cómo se calculó?"
      side="right"
    >
      {isLoading && <Spinner />}

      {isError && (
        <p className="rounded border border-danger/30 bg-danger/10 p-3 text-sm text-danger">
          Error al cargar explicación
        </p>
      )}

      {data && (
        <div className="space-y-5">
          {data.sections.map((section) => (
            <div key={section.key}>
              <h3 className="mb-2 text-sm font-semibold text-text">
                {section.titulo}
              </h3>

              {section.note && (
                <p className="mb-2 text-xs italic text-text-muted">{section.note}</p>
              )}

              <dl className="space-y-1">
                {section.steps.map((step) => (
                  <div key={step.key} className="flex justify-between gap-2 text-sm">
                    <dt className="text-text-muted">
                      {step.glossary_term ? (
                        <GlossaryTerm term={step.glossary_term}>
                          {step.label_es}
                        </GlossaryTerm>
                      ) : (
                        step.label_es
                      )}
                    </dt>
                    <dd className="font-medium text-text">
                      {formatStepValue(step)}
                    </dd>
                  </div>
                ))}
              </dl>
            </div>
          ))}
        </div>
      )}
    </Sheet>
  )
}
