/**
 * api/health — tipado y función cliente para GET /api/v1/health/full.
 * Los veredictos vienen YA calculados del servidor; el front nunca los calcula.
 * La forma refleja EXACTAMENTE la respuesta anidada del backend (HealthFull).
 */

import { fetchAPI } from './client'

export type Verdict = 'ok' | 'warn' | 'stale'

export interface OddsCaptureHealth {
  last_at: string | null
  age_hours: number | null
  verdict: Verdict
}

export interface OddsCreditsHealth {
  remaining: number | null
  verdict: Verdict
}

export interface ModelHealth {
  name: string | null
  verdict: Verdict
}

export interface ResultsHealth {
  latest_date: string | null
  verdict: Verdict
}

export interface HealthFull {
  overall: Verdict
  odds_capture: OddsCaptureHealth
  odds_credits: OddsCreditsHealth
  model: ModelHealth
  results: ResultsHealth
}

export function getHealthFull(): Promise<HealthFull> {
  return fetchAPI<HealthFull>('/v1/health/full')
}
