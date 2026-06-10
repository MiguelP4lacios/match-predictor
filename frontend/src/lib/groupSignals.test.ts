import { describe, it, expect } from 'vitest'
import { groupSignals } from './groupSignals'
import type { SignalItem } from '../api/types'

const makeSignal = (
  overrides: Partial<SignalItem> & { edge: number },
): SignalItem => ({
  id: 1,
  match_date: '2026-06-20',
  kickoff_at: null,
  home_team: 'Haiti',
  away_team: 'Scotland',
  market_type: 'MATCH_1X2',
  outcome_code: 'HOME',
  p_model: 0.45,
  best_odds: 3.5,
  bookmaker: 'bet365',
  ev: 0.05,
  kelly_fraction: 0.03,
  recommended_stake: '60.00',
  captured_at: '2026-06-20T10:00:00',
  ...overrides,
})

describe('groupSignals', () => {
  it('retorna array vacío cuando items=[]', () => {
    expect(groupSignals([])).toEqual([])
  })

  it('retorna un grupo cuando hay una sola señal', () => {
    const signal = makeSignal({ edge: 0.097, home_team: 'Haiti', away_team: 'Scotland' })
    const groups = groupSignals([signal])
    expect(groups).toHaveLength(1)
    expect(groups[0].home_team).toBe('Haiti')
    expect(groups[0].away_team).toBe('Scotland')
    expect(groups[0].signals).toHaveLength(1)
    expect(groups[0].signals[0]).toBe(signal)
  })

  it('escenario numérico: B(0.141) primero, luego A(0.097, 0.051) en ese orden', () => {
    // Partido A: Haiti vs Scotland — 2 señales
    const aHome = makeSignal({
      id: 1,
      edge: 0.097,
      home_team: 'Haiti',
      away_team: 'Scotland',
      outcome_code: 'HOME',
      match_date: '2026-06-20',
    })
    const aDraw = makeSignal({
      id: 2,
      edge: 0.051,
      home_team: 'Haiti',
      away_team: 'Scotland',
      outcome_code: 'DRAW',
      match_date: '2026-06-20',
    })
    // Partido B: Brasil vs Argentina — 1 señal
    const bAway = makeSignal({
      id: 3,
      edge: 0.141,
      home_team: 'Brasil',
      away_team: 'Argentina',
      outcome_code: 'AWAY',
      match_date: '2026-06-21',
    })

    // El servidor envía en edge DESC global: B(0.141), A-HOME(0.097), A-DRAW(0.051)
    const groups = groupSignals([bAway, aHome, aDraw])

    expect(groups).toHaveLength(2)

    // B tiene max_edge=0.141 > max_edge A=0.097 → B es primero
    expect(groups[0].home_team).toBe('Brasil')
    expect(groups[0].away_team).toBe('Argentina')
    expect(groups[0].signals).toHaveLength(1)
    expect(groups[0].signals[0].edge).toBe(0.141)

    // A es segundo con 2 señales en orden del servidor
    expect(groups[1].home_team).toBe('Haiti')
    expect(groups[1].away_team).toBe('Scotland')
    expect(groups[1].signals).toHaveLength(2)
    expect(groups[1].signals[0].edge).toBe(0.097)
    expect(groups[1].signals[1].edge).toBe(0.051)
  })

  it('preserva el orden de señales dentro del grupo (orden del servidor)', () => {
    const home = makeSignal({
      id: 1,
      edge: 0.097,
      outcome_code: 'HOME',
      home_team: 'Haiti',
      away_team: 'Scotland',
    })
    const draw = makeSignal({
      id: 2,
      edge: 0.051,
      outcome_code: 'DRAW',
      home_team: 'Haiti',
      away_team: 'Scotland',
    })
    const groups = groupSignals([home, draw])
    expect(groups[0].signals[0].outcome_code).toBe('HOME')
    expect(groups[0].signals[1].outcome_code).toBe('DRAW')
  })

  it('distingue partidos del mismo equipo en fechas distintas', () => {
    const s1 = makeSignal({
      id: 1,
      edge: 0.097,
      home_team: 'Haiti',
      away_team: 'Scotland',
      match_date: '2026-06-20',
    })
    const s2 = makeSignal({
      id: 2,
      edge: 0.141,
      home_team: 'Haiti',
      away_team: 'Scotland',
      match_date: '2026-06-25',
    })
    const groups = groupSignals([s2, s1])
    expect(groups).toHaveLength(2)
  })

  it('construye match_key como "fecha|local|visitante"', () => {
    const signal = makeSignal({ edge: 0.097, home_team: 'Haiti', away_team: 'Scotland', match_date: '2026-06-20' })
    const groups = groupSignals([signal])
    expect(groups[0].match_key).toBe('2026-06-20|Haiti|Scotland')
  })
})
