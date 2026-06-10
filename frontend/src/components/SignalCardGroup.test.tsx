import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import SignalCardGroup from './SignalCardGroup'
import type { SignalItem } from '../api/types'

const makeSignal = (overrides: Partial<SignalItem> & { edge: number }): SignalItem => ({
  id: 1,
  match_date: '2026-06-20',
  kickoff_at: null,
  home_team: 'Haiti',
  away_team: 'Brasil',
  market_type: 'MATCH_1X2',
  outcome_code: 'HOME',
  p_model: 0.5,
  best_odds: 2.0,
  bookmaker: 'bet365',
  ev: 0.1,
  kelly_fraction: 0.05,
  recommended_stake: '50.00',
  captured_at: '2026-06-10T00:00:00',
  ...overrides,
})

describe('SignalCardGroup', () => {
  describe('escenario Haiti(2 señales) + Brasil(1 señal)', () => {
    const haitiHome = makeSignal({
      id: 1, edge: 0.097,
      home_team: 'Haiti', away_team: 'Scotland', match_date: '2026-06-20',
      outcome_code: 'HOME',
    })
    const haitiDraw = makeSignal({
      id: 2, edge: 0.051,
      home_team: 'Haiti', away_team: 'Scotland', match_date: '2026-06-20',
      outcome_code: 'DRAW',
    })
    const brasilAway = makeSignal({
      id: 3, edge: 0.141,
      home_team: 'Brasil', away_team: 'Argentina', match_date: '2026-06-21',
      outcome_code: 'AWAY',
    })

    it('muestra hint de exposición correlacionada para Haiti (2 señales)', () => {
      render(<SignalCardGroup items={[haitiHome, haitiDraw, brasilAway]} onExplain={vi.fn()} />)
      expect(
        screen.getByText('⚠ 2 señales sobre este partido — exposición correlacionada')
      ).toBeInTheDocument()
    })

    it('NO muestra hint para Brasil (1 señal)', () => {
      render(<SignalCardGroup items={[haitiHome, haitiDraw, brasilAway]} onExplain={vi.fn()} />)
      // Sólo 1 hint total (solo el partido con 2+ señales)
      const hints = screen.queryAllByText(/exposición correlacionada/)
      expect(hints).toHaveLength(1)
    })

    it('preserva el orden del servidor: Brasil primero si aparece antes en el input', () => {
      render(<SignalCardGroup items={[brasilAway, haitiHome, haitiDraw]} onExplain={vi.fn()} />)
      // Usar el testid del header de grupo (no el <p> del SignalCard que también contiene "vs")
      const groupHeaders = screen.getAllByTestId('group-header')
      expect(groupHeaders).toHaveLength(2)
      expect(groupHeaders[0]).toHaveTextContent('Brasil vs Argentina')
      expect(groupHeaders[1]).toHaveTextContent('Haiti vs Scotland')
    })

    it('renderiza todas las señales del grupo Haiti (9.7% y 5.1%)', () => {
      render(<SignalCardGroup items={[haitiHome, haitiDraw, brasilAway]} onExplain={vi.fn()} />)
      expect(screen.getByText('9.7%')).toBeInTheDocument()
      expect(screen.getByText('5.1%')).toBeInTheDocument()
    })
  })

  describe('grupo de señal única — sin hint', () => {
    it('Brasil vs Argentina con 1 señal no muestra texto de exposición correlacionada', () => {
      const single = makeSignal({
        id: 5, edge: 0.141,
        home_team: 'Brasil', away_team: 'Argentina', match_date: '2026-06-21',
        outcome_code: 'AWAY',
      })
      render(<SignalCardGroup items={[single]} onExplain={vi.fn()} />)
      expect(screen.queryByText(/exposición correlacionada/)).not.toBeInTheDocument()
    })
  })

  describe('estado vacío', () => {
    it('muestra "Sin señales con ese filtro" cuando items=[]', () => {
      render(<SignalCardGroup items={[]} onExplain={vi.fn()} />)
      expect(screen.getByText('Sin señales con ese filtro')).toBeInTheDocument()
    })
  })
})
