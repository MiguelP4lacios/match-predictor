/**
 * Capa de datos — Futuros Monte Carlo WC2026.
 *
 * getFutures()        → GET /api/v1/futures/probabilities
 * getFuturesSignals() → GET /api/v1/futures/signals
 */

import { fetchAPI } from './client'
import type { FuturesList, FuturesSignalResponse } from './types'

export function getFutures(): Promise<FuturesList> {
  return fetchAPI<FuturesList>('/v1/futures/probabilities')
}

export function getFuturesSignals(): Promise<FuturesSignalResponse> {
  return fetchAPI<FuturesSignalResponse>('/v1/futures/signals')
}
