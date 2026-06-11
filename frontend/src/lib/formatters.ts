/**
 * Formatters puros — ninguno calcula ni recomputa datos del servidor.
 * Solo formatean valores ya calculados por el modelo determinista.
 */

/**
 * Formatea un valor COP entero con separador de miles (punto, es-CO).
 * formatCop(12000) → "$12.000"  (sin decimales, sin espacios)
 * Implementación manual para resultados deterministas en cualquier entorno.
 */
export function formatCop(value: number): string {
  const rounded = Math.round(value)
  const abs = Math.abs(rounded)
  const str = abs.toString()
  const withDots = str.replace(/\B(?=(\d{3})+(?!\d))/g, '.')
  return `$${withDots}`
}

/**
 * Formatea P&L COP con signo.
 * - Positivo: "+$4.800"
 * - Negativo: "−$12.000"  (usa guion menos Unicode U+2212, no ASCII -)
 */
export function formatPnl(value: number): string {
  const formatted = formatCop(Math.abs(value))
  if (value < 0) return `−${formatted}`
  return `+${formatted}`
}

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
