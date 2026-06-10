import { useEffect, useRef } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchAPI } from '../api/client'
import type { SignalExplanation, ExplainStep } from '../api/types'
import Loading from './Loading'
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
 *
 * A11y: role=dialog aria-modal, autofocus en botón X (ref+useEffect),
 * cierre con Escape (keydown en window), click-outside (backdrop onClick).
 *
 * Responsive: panel derecho en desktop (md+), bottom sheet a ancho
 * completo en mobile (< sm = < 640 px).
 */
export default function ExplainDrawer({ signalId, onClose }: ExplainDrawerProps) {
  const closeButtonRef = useRef<HTMLButtonElement>(null)

  // Autofocus en botón X al abrir
  useEffect(() => {
    if (signalId !== null) {
      closeButtonRef.current?.focus()
    }
  }, [signalId])

  // Cerrar con tecla Escape
  useEffect(() => {
    if (signalId === null) return
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [signalId, onClose])

  const { data, isLoading, isError } = useQuery<SignalExplanation>({
    queryKey: ['explain', signalId],
    queryFn: () =>
      fetchAPI<SignalExplanation>(`/v1/signals/${signalId}/explain`),
    enabled: signalId !== null,
  })

  if (signalId === null) return null

  return (
    /* Backdrop — ocupa toda la pantalla; click aquí cierra el drawer */
    <div
      data-testid="drawer-backdrop"
      className="fixed inset-0 z-50 bg-black/40"
      onClick={onClose}
    >
      {/* Panel — detiene propagación para no cerrar al hacer click dentro */}
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Explicación de la señal"
        className={[
          'absolute overflow-y-auto bg-white shadow-xl',
          // Mobile: bottom sheet a ancho completo
          'bottom-0 left-0 right-0 max-h-[85vh] rounded-t-2xl',
          // Desktop (sm+): panel derecho fijo
          'sm:bottom-0 sm:left-auto sm:right-0 sm:top-0 sm:max-h-full sm:w-96 sm:rounded-l-2xl sm:rounded-tr-none',
        ].join(' ')}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b p-4">
          <h2 className="text-base font-semibold text-gray-900">
            ¿Cómo se calculó?
          </h2>
          <button
            ref={closeButtonRef}
            type="button"
            aria-label="Cerrar explicación"
            onClick={onClose}
            className="rounded p-1 text-gray-400 hover:text-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            ✕
          </button>
        </div>

        {/* Contenido */}
        <div className="p-4">
          {isLoading && <Loading />}

          {isError && (
            <p className="rounded border border-red-300 bg-red-50 p-3 text-sm text-red-700">
              Error al cargar explicación
            </p>
          )}

          {data && (
            <div className="space-y-5">
              {data.sections.map((section) => (
                <div key={section.key}>
                  <h3 className="mb-2 text-sm font-semibold text-gray-800">
                    {section.titulo}
                  </h3>

                  {section.note && (
                    <p className="mb-2 text-xs italic text-gray-500">{section.note}</p>
                  )}

                  <dl className="space-y-1">
                    {section.steps.map((step) => (
                      <div key={step.key} className="flex justify-between gap-2 text-sm">
                        <dt className="text-gray-600">
                          {step.glossary_term ? (
                            <GlossaryTerm term={step.glossary_term}>
                              {step.label_es}
                            </GlossaryTerm>
                          ) : (
                            step.label_es
                          )}
                        </dt>
                        <dd className="font-medium text-gray-900">
                          {formatStepValue(step)}
                        </dd>
                      </div>
                    ))}
                  </dl>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
