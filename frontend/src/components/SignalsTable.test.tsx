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
  describe('renderiza filas en el orden recibido (server es autoridad)', () => {
    it('muestra 3 filas cuando se pasan 3 señales', () => {
      const items = [
        makeSignal({ id: 1, edge: 0.20, home_team: 'España', away_team: 'Brasil' }),
        makeSignal({ id: 2, edge: 0.14, home_team: 'Francia', away_team: 'Alemania' }),
        makeSignal({ id: 3, edge: 0.08, home_team: 'Argentina', away_team: 'Uruguay' }),
      ]
      render(<SignalsTable items={items} />)
      const rows = screen.getAllByRole('row')
      // 3 filas de datos + 1 de encabezado = 4 rows
      expect(rows).toHaveLength(4)
    })

    it('preserva el orden dado: primera fila tiene el equipo de la primera señal', () => {
      const items = [
        makeSignal({ id: 1, edge: 0.20, home_team: 'España', away_team: 'Brasil' }),
        makeSignal({ id: 2, edge: 0.14, home_team: 'Francia', away_team: 'Alemania' }),
        makeSignal({ id: 3, edge: 0.08, home_team: 'Argentina', away_team: 'Uruguay' }),
      ]
      render(<SignalsTable items={items} />)
      const rows = screen.getAllByRole('row')
      // Primera fila de datos (índice 1, tras el encabezado)
      expect(within(rows[1]).getByText('España vs Brasil')).toBeInTheDocument()
      // Segunda fila
      expect(within(rows[2]).getByText('Francia vs Alemania')).toBeInTheDocument()
      // Tercera fila
      expect(within(rows[3]).getByText('Argentina vs Uruguay')).toBeInTheDocument()
    })

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
      // Sin datos → sin filas (ni encabezado si la tabla no se renderiza,
      // o solo encabezado si se renderiza con tbody vacío — ambos aceptables)
      expect(rows.length).toBeLessThanOrEqual(1)
    })
  })
})
