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
 * - Los grupos se ordenan por max(edge) del grupo DESC.
 * - Dentro de cada grupo, el orden de las señales es el del servidor (sin reordenar).
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

  return Array.from(groupMap.values()).sort((a, b) => {
    const maxA = Math.max(...a.signals.map((s) => s.edge))
    const maxB = Math.max(...b.signals.map((s) => s.edge))
    return maxB - maxA
  })
}
