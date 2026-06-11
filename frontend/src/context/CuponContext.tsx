/**
 * CuponContext — estado global del cupón de bloques (parlay bet-slip).
 * Persiste en sessionStorage para sobrevivir navegación entre páginas.
 *
 * INVARIANTE: el front NUNCA calcula cuotas ni EV — solo acumula legs
 * y delega toda la aritmética al endpoint POST /parlays/preview.
 */

import React, { createContext, useContext, useEffect, useReducer } from 'react'

// ─── Tipos ────────────────────────────────────────────────────────────────────

export interface CuponLeg {
  match_id: number
  outcome_code: 'HOME' | 'DRAW' | 'AWAY'
  home_team: string
  away_team: string
  match_date: string
  /** Cuota BetPlay ingresada por el usuario; null = sin ingresar todavía */
  odds: number | null
}

interface CuponContextValue {
  legs: CuponLeg[]
  addLeg(leg: Omit<CuponLeg, 'odds'>): void
  removeLeg(match_id: number, outcome_code: string): void
  updateOdds(match_id: number, outcome_code: string, odds: number | null): void
  clear(): void
}

// ─── Storage key ─────────────────────────────────────────────────────────────

const STORAGE_KEY = 'cupon_legs'

function loadFromStorage(): CuponLeg[] {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY)
    if (!raw) return []
    return JSON.parse(raw) as CuponLeg[]
  } catch {
    return []
  }
}

function saveToStorage(legs: CuponLeg[]): void {
  sessionStorage.setItem(STORAGE_KEY, JSON.stringify(legs))
}

// ─── Reducer ──────────────────────────────────────────────────────────────────

type Action =
  | { type: 'ADD'; leg: Omit<CuponLeg, 'odds'> }
  | { type: 'REMOVE'; match_id: number; outcome_code: string }
  | { type: 'UPDATE_ODDS'; match_id: number; outcome_code: string; odds: number | null }
  | { type: 'CLEAR' }

function isDuplicate(legs: CuponLeg[], match_id: number, outcome_code: string): boolean {
  return legs.some((l) => l.match_id === match_id && l.outcome_code === outcome_code)
}

function cuponReducer(state: CuponLeg[], action: Action): CuponLeg[] {
  switch (action.type) {
    case 'ADD': {
      if (isDuplicate(state, action.leg.match_id, action.leg.outcome_code)) return state
      return [...state, { ...action.leg, odds: null }]
    }
    case 'REMOVE':
      return state.filter(
        (l) => !(l.match_id === action.match_id && l.outcome_code === action.outcome_code),
      )
    case 'UPDATE_ODDS':
      return state.map((l) =>
        l.match_id === action.match_id && l.outcome_code === action.outcome_code
          ? { ...l, odds: action.odds }
          : l,
      )
    case 'CLEAR':
      return []
    default:
      return state
  }
}

// ─── Context ──────────────────────────────────────────────────────────────────

const CuponContext = createContext<CuponContextValue | null>(null)

export function CuponProvider({ children }: { children: React.ReactNode }) {
  const [legs, dispatch] = useReducer(cuponReducer, undefined, loadFromStorage)

  // Persist on every state change
  useEffect(() => {
    saveToStorage(legs)
  }, [legs])

  function addLeg(leg: Omit<CuponLeg, 'odds'>): void {
    dispatch({ type: 'ADD', leg })
  }

  function removeLeg(match_id: number, outcome_code: string): void {
    dispatch({ type: 'REMOVE', match_id, outcome_code })
  }

  function updateOdds(match_id: number, outcome_code: string, odds: number | null): void {
    dispatch({ type: 'UPDATE_ODDS', match_id, outcome_code, odds })
  }

  function clear(): void {
    dispatch({ type: 'CLEAR' })
  }

  return (
    <CuponContext.Provider value={{ legs, addLeg, removeLeg, updateOdds, clear }}>
      {children}
    </CuponContext.Provider>
  )
}

export function useCupon(): CuponContextValue {
  const ctx = useContext(CuponContext)
  if (!ctx) throw new Error('useCupon must be used inside CuponProvider')
  return ctx
}
