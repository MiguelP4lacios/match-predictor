import type { SignalItem } from '../api/types'

export interface SignalGroup {
  match_key: string
  match_date: string
  home_team: string
  away_team: string
  signals: SignalItem[]
}

/**
 * Agrupa señales por partido (match_date + home_team + away_team).
 *
 * - Los grupos preservan el orden de PRIMERA APARICIÓN en la respuesta del
 *   servidor (que ordena por fecha) — el server es la autoridad, el cliente
 *   no re-ordena.
 * - Dentro de cada grupo, el orden de las señales es el del servidor.
 * - El cliente NUNCA recalcula p_model, edge ni stake: solo reagrupa para presentación.
 */
export function groupSignals(items: SignalItem[]): SignalGroup[] {
  const groupMap = new Map<string, SignalGroup>()

  for (const item of items) {
    const key = `${item.match_date}|${item.home_team}|${item.away_team}`
    const existing = groupMap.get(key)
    if (existing) {
      existing.signals.push(item)
    } else {
      groupMap.set(key, {
        match_key: key,
        match_date: item.match_date,
        home_team: item.home_team,
        away_team: item.away_team,
        signals: [item],
      })
    }
  }

  // Map preserva orden de inserción → orden del server (cronológico) intacto.
  return Array.from(groupMap.values())
}
