/**
 * Formatters puros — ninguno calcula ni recomputa datos del servidor.
 * Solo formatean valores ya calculados por el modelo determinista.
 */

/** Formatea un edge float (ej. 0.0832) → "8.3%" */
export function formatEdge(value: number): string {
  return `${(value * 100).toFixed(1)}%`
}

/** Formatea una probabilidad float (ej. 0.4202) → "42.0%" */
export function formatProbability(value: number): string {
  return `${(value * 100).toFixed(1)}%`
}

/**
 * Formatea el stake que viene como STRING desde la API (Pydantic serializa
 * Decimal → string). Ej. "112.7345" → "112.73"
 */
export function formatStake(value: string): string {
  return parseFloat(value).toFixed(2)
}

/** Formatea cuotas float (ej. 3.9) → "3.90" */
export function formatOdds(value: number): string {
  return value.toFixed(2)
}

/**
 * Formatea ROI: null → "—" (invariante de honestidad — NUNCA mostrar "0%").
 * Positivo: "+12.5%". Negativo: "-5.0%".
 */
export function formatROI(value: number | null): string {
  if (value === null) return '—'
  const pct = (value * 100).toFixed(1)
  return value >= 0 ? `+${pct}%` : `${pct}%`
}
