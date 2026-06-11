/**
 * Wrappers de la API de parlays sobre fetchAPI.
 * El front NUNCA calcula cuota combinada, model_prob ni EV — SOLO llama al servidor.
 */

import { fetchAPI } from './client'
import type { ParlayCreate, ParlayItem, ParlayLegInput, ParlayPreview } from './types'

export interface PreviewRequest {
  legs: ParlayLegInput[]
  stake?: number
}

/** POST /parlays/preview — sin persistencia; retorna diagnóstico completo */
export async function previewParlay(req: PreviewRequest): Promise<ParlayPreview> {
  return fetchAPI<ParlayPreview>('/v1/parlays/preview', {
    method: 'POST',
    body: JSON.stringify(req),
  })
}

/** POST /parlays — persiste el parlay; retorna 201 con el id creado */
export async function createParlay(data: ParlayCreate): Promise<ParlayItem> {
  return fetchAPI<ParlayItem>('/v1/parlays', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

/** GET /parlays?mode=... — lista parlays, opcionalmente filtrados por modo */
export async function fetchParlays(mode?: string): Promise<ParlayItem[]> {
  const query = mode ? `?mode=${mode}` : ''
  return fetchAPI<ParlayItem[]>(`/v1/parlays${query}`)
}
