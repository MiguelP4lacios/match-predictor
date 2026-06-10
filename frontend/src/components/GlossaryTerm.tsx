import { glossary } from '../lib/glossary'

interface GlossaryTermProps {
  /** Clave del glosario (ej. "edge", "kelly"). Si no existe, renderiza children sin ícono. */
  term: string
  children: React.ReactNode
}

/**
 * Término expandible `<details>`-style, touch-friendly.
 * - Si `term` tiene entrada en el glosario → muestra el ícono ? y la definición al expandir.
 * - Si no tiene entrada → renderiza `children` plano, sin ícono.
 */
export default function GlossaryTerm({ term, children }: GlossaryTermProps) {
  const definition = glossary[term]

  if (!definition) {
    return <>{children}</>
  }

  return (
    <details className="inline">
      <summary className="inline cursor-pointer list-none">
        {children}{' '}
        <span
          aria-hidden="true"
          className="inline-flex h-4 w-4 items-center justify-center rounded-full border border-gray-400 text-xs text-gray-500"
        >
          ?
        </span>
      </summary>
      <p className="mt-1 text-xs text-gray-600">{definition}</p>
    </details>
  )
}
