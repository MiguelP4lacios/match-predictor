import { describe, it, expect } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import SignalsTable from './SignalsTable'
import type { SignalItem } from '../api/types'

const makeSignal = (overrides: Partial<SignalItem> & { edge: number }): SignalItem => ({
  id: 1,
  match_date: '2026-06-15',
  kickoff_at: null,
  home_team: 'España',
  away_team: 'Brasil',
  market_type: 'MATCH_1X2',
  outcome_code: 'HOME',
  p_model: 0.55,
  best_odds: 2.1,
  bookmaker: 'bet365',
  ev: 0.05,
  kelly_fraction: 0.04,
  recommended_stake: '80.00',
  captured_at: '2026-06-15T10:00:00',
  ...overrides,
})

describe('SignalsTable', () => {
  describe('vista agrupada — 3 partidos distintos (1 señal cada uno)', () => {
    const items = [
      makeSignal({ id: 1, edge: 0.20, home_team: 'España', away_team: 'Brasil', match_date: '2026-06-15' }),
      makeSignal({ id: 2, edge: 0.14, home_team: 'Francia', away_team: 'Alemania', match_date: '2026-06-16' }),
      makeSignal({ id: 3, edge: 0.08, home_team: 'Argentina', away_team: 'Uruguay', match_date: '2026-06-17' }),
    ]

    it('renderiza un encabezado de grupo por partido', () => {
      render(<SignalsTable items={items} />)
      expect(screen.getByText('España vs Brasil')).toBeInTheDocument()
      expect(screen.getByText('Francia vs Alemania')).toBeInTheDocument()
      expect(screen.getByText('Argentina vs Uruguay')).toBeInTheDocument()
    })

    it('preserva el orden del server: España(06-15), Francia(06-16), Argentina(06-17)', () => {
      render(<SignalsTable items={items} />)
      const rows = screen.getAllByRole('row')
      // Orden de primera aparición en la respuesta (cronológico) — el cliente NO re-ordena.
      // Estructura: [thead, group-España, row-España, group-Francia, row-Francia, group-Argentina, row-Argentina]
      expect(within(rows[1]).getByText('España vs Brasil')).toBeInTheDocument()
      expect(within(rows[3]).getByText('Francia vs Alemania')).toBeInTheDocument()
      expect(within(rows[5]).getByText('Argentina vs Uruguay')).toBeInTheDocument()
    })

    it('NO muestra hint de exposición correlacionada cuando hay 1 señal por partido', () => {
      render(<SignalsTable items={items} />)
      expect(screen.queryByText(/exposición correlacionada/)).not.toBeInTheDocument()
    })
  })

  describe('hint de exposición correlacionada', () => {
    it('muestra hint cuando hay 2+ señales del mismo partido', () => {
      // Partido A: Haiti vs Scotland con 2 señales; Partido B: 1 señal
      const bAway = makeSignal({
        id: 3, edge: 0.141,
        home_team: 'Brasil', away_team: 'Argentina', match_date: '2026-06-21',
        outcome_code: 'AWAY',
      })
      const aHome = makeSignal({
        id: 1, edge: 0.097,
        home_team: 'Haiti', away_team: 'Scotland', match_date: '2026-06-20',
        outcome_code: 'HOME',
      })
      const aDraw = makeSignal({
        id: 2, edge: 0.051,
        home_team: 'Haiti', away_team: 'Scotland', match_date: '2026-06-20',
        outcome_code: 'DRAW',
      })
      render(<SignalsTable items={[bAway, aHome, aDraw]} />)
      expect(screen.getByText('⚠ 2 señales sobre este partido — exposición correlacionada')).toBeInTheDocument()
    })

    it('el hint aparece en el grupo con 2 señales, no en el de 1 señal', () => {
      const bAway = makeSignal({
        id: 3, edge: 0.141,
        home_team: 'Brasil', away_team: 'Argentina', match_date: '2026-06-21',
        outcome_code: 'AWAY',
      })
      const aHome = makeSignal({
        id: 1, edge: 0.097,
        home_team: 'Haiti', away_team: 'Scotland', match_date: '2026-06-20',
        outcome_code: 'HOME',
      })
      const aDraw = makeSignal({
        id: 2, edge: 0.051,
        home_team: 'Haiti', away_team: 'Scotland', match_date: '2026-06-20',
        outcome_code: 'DRAW',
      })
      render(<SignalsTable items={[bAway, aHome, aDraw]} />)
      const rows = screen.getAllByRole('row')
      // Orden de primera aparición en el input: B primero, A segundo (el cliente no re-ordena)
      // rows[0]=thead, rows[1]=group-B-header, rows[2]=row-B, rows[3]=group-A-header(+hint), rows[4]=row-A-HOME, rows[5]=row-A-DRAW
      expect(within(rows[1]).queryByText(/exposición correlacionada/)).not.toBeInTheDocument()
      expect(within(rows[3]).getByText('⚠ 2 señales sobre este partido — exposición correlacionada')).toBeInTheDocument()
    })

    it('escenario numérico: B primero por orden de aparición, A(9.7%+5.1%) segundo con hint', () => {
      const bAway = makeSignal({
        id: 3, edge: 0.141,
        home_team: 'Brasil', away_team: 'Argentina', match_date: '2026-06-21',
        outcome_code: 'AWAY',
      })
      const aHome = makeSignal({
        id: 1, edge: 0.097,
        home_team: 'Haiti', away_team: 'Scotland', match_date: '2026-06-20',
        outcome_code: 'HOME',
      })
      const aDraw = makeSignal({
        id: 2, edge: 0.051,
        home_team: 'Haiti', away_team: 'Scotland', match_date: '2026-06-20',
        outcome_code: 'DRAW',
      })
      render(<SignalsTable items={[bAway, aHome, aDraw]} />)
      const rows = screen.getAllByRole('row')
      // rows: [thead, B-header, B-row, A-header+hint, A-HOME-row, A-DRAW-row] = 6 total
      expect(rows).toHaveLength(6)
      expect(within(rows[1]).getByText('Brasil vs Argentina')).toBeInTheDocument()
      expect(within(rows[3]).getByText('Haiti vs Scotland')).toBeInTheDocument()
      expect(within(rows[3]).getByText('⚠ 2 señales sobre este partido — exposición correlacionada')).toBeInTheDocument()
      // 14.1% en el grupo B
      expect(within(rows[2]).getByText('14.1%')).toBeInTheDocument()
      // 9.7% y 5.1% en grupo A
      expect(within(rows[4]).getByText('9.7%')).toBeInTheDocument()
      expect(within(rows[5]).getByText('5.1%')).toBeInTheDocument()
    })
  })

  describe('formatters dentro de señales', () => {
    it('muestra el edge formateado a 1 decimal con %', () => {
      const items = [makeSignal({ edge: 0.0832 })]
      render(<SignalsTable items={items} />)
      expect(screen.getByText('8.3%')).toBeInTheDocument()
    })

    it('muestra el stake formateado a 2 decimales (string input)', () => {
      const items = [makeSignal({ edge: 0.10, recommended_stake: '112.7345' })]
      render(<SignalsTable items={items} />)
      expect(screen.getByText('112.73')).toBeInTheDocument()
    })
  })

  describe('estado vacío', () => {
    it('muestra "Sin señales con ese filtro" cuando items=[]', () => {
      render(<SignalsTable items={[]} />)
      expect(screen.getByText('Sin señales con ese filtro')).toBeInTheDocument()
    })

    it('no renderiza ninguna fila de datos cuando items=[]', () => {
      render(<SignalsTable items={[]} />)
      const rows = screen.queryAllByRole('row')
      expect(rows.length).toBeLessThanOrEqual(1)
    })
  })
})
