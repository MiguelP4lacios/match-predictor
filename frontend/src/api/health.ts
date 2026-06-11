/**
 * api/health — tipado y función cliente para GET /api/v1/health/full.
 * El LLM NUNCA calcula veredictos; los datos vienen ya calculados del servidor.
 */

import { fetchAPI } from './client'

export type Verdict = 'ok' | 'warn' | 'stale'

export interface HealthMetric {
  value: string | number | null
  verdict: Verdict
  threshold: string
}

export interface HealthFull {
  overall: Verdict
  last_odds_capture: HealthMetric
  odds_age: HealthMetric
  credits_remaining: HealthMetric
  model_version: HealthMetric
  last_finished: HealthMetric
}

export function getHealthFull(): Promise<HealthFull> {
  return fetchAPI<HealthFull>('/v1/health/full')
}
