import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import SignalCard from './SignalCard'
import type { SignalItem } from '../api/types'

const mockNavigate = vi.fn()
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return { ...actual, useNavigate: () => mockNavigate }
})

const makeSignal = (overrides: Partial<SignalItem> = {}): SignalItem => ({
  id: 10,
  match_id: 99,
  match_date: '2026-06-11',
  kickoff_at: null,
  home_team: 'México',
  away_team: 'South Africa',
  market_type: 'MATCH_1X2',
  outcome_code: 'HOME',
  p_model: 0.83394,
  best_odds: 1.47,
  bookmaker: 'gtbets',
  edge: 0.14724,
  ev: 0.22589,
  kelly_fraction: 0.12016,
  recommended_stake: '120.16',
  captured_at: '2026-06-09T17:28:05',
  ...overrides,
})

describe('SignalCard', () => {
  describe('escenario id=10 — México HOME (verbatim spec)', () => {
    it('muestra badge de edge "14.7%"', () => {
      render(<SignalCard signal={makeSignal()} onExplain={vi.fn()} />)
      expect(screen.getByText('14.7%')).toBeInTheDocument()
    })

    it('muestra stake "$120.16"', () => {
      render(<SignalCard signal={makeSignal()} onExplain={vi.fn()} />)
      expect(screen.getByText('$120.16')).toBeInTheDocument()
    })

    it('muestra cuota "1.47 (gtbets)"', () => {
      render(<SignalCard signal={makeSignal()} onExplain={vi.fn()} />)
      expect(screen.getByText('1.47 (gtbets)')).toBeInTheDocument()
    })

    it('muestra "Apostale a México" para outcome HOME', () => {
      render(<SignalCard signal={makeSignal()} onExplain={vi.fn()} />)
      expect(screen.getByText('Apostale a México')).toBeInTheDocument()
    })

    it('muestra botón "¿Por qué? →"', () => {
      render(<SignalCard signal={makeSignal()} onExplain={vi.fn()} />)
      expect(screen.getByRole('button', { name: /¿Por qué/ })).toBeInTheDocument()
    })

    it('llama a onExplain(id) al pulsar "¿Por qué? →"', () => {
      const onExplain = vi.fn()
      render(<SignalCard signal={makeSignal({ id: 10 })} onExplain={onExplain} />)
      fireEvent.click(screen.getByRole('button', { name: /¿Por qué/ }))
      expect(onExplain).toHaveBeenCalledWith(10)
    })

    it('muestra la fecha y el partido en el header', () => {
      render(<SignalCard signal={makeSignal()} onExplain={vi.fn()} />)
      expect(screen.getByText(/2026-06-11/)).toBeInTheDocument()
      expect(screen.getByText(/México vs South Africa/)).toBeInTheDocument()
    })
  })

  describe('outcomes humanizados', () => {
    it('DRAW → "Apostale a Empate"', () => {
      render(<SignalCard signal={makeSignal({ outcome_code: 'DRAW' })} onExplain={vi.fn()} />)
      expect(screen.getByText('Apostale a Empate')).toBeInTheDocument()
    })

    it('AWAY → "Apostale a South Africa" (via away_team del fixture)', () => {
      // makeSignal default away_team = 'South Africa'
      render(
        <SignalCard
          signal={makeSignal({ outcome_code: 'AWAY' })}
          onExplain={vi.fn()}
        />
      )
      expect(screen.getByText('Apostale a South Africa')).toBeInTheDocument()
    })
  })

  describe('formatters reusados (sin aritmética propia)', () => {
    it('edge=0.064 → badge "6.4%"', () => {
      render(<SignalCard signal={makeSignal({ edge: 0.064, recommended_stake: '18.93' })} onExplain={vi.fn()} />)
      expect(screen.getByText('6.4%')).toBeInTheDocument()
    })

    it('recommended_stake="18.93" → "$18.93"', () => {
      render(<SignalCard signal={makeSignal({ edge: 0.064, recommended_stake: '18.93' })} onExplain={vi.fn()} />)
      expect(screen.getByText('$18.93')).toBeInTheDocument()
    })
  })
})

describe('Registrar apuesta button (4.8)', () => {
  it('el badge de edge dice "la cuota paga de más" — nunca "ventaja" a secas (ambiguo)', () => {
    render(
      <MemoryRouter>
        <SignalCard signal={makeSignal({ edge: 0.064 })} onExplain={vi.fn()} />
      </MemoryRouter>,
    )
    expect(screen.getByText('la cuota paga de más')).toBeInTheDocument()
    expect(screen.queryByText(/^ventaja$/)).not.toBeInTheDocument()
  })

  it('botón "Registrar apuesta" navega a /apuestas con match_id, outcome y odds', () => {
    mockNavigate.mockClear()
    render(
      <MemoryRouter>
        <SignalCard
          signal={makeSignal({ match_id: 99, outcome_code: 'HOME', best_odds: 1.47 })}
          onExplain={vi.fn()}
        />
      </MemoryRouter>,
    )

    fireEvent.click(screen.getByRole('button', { name: /registrar apuesta/i }))

    expect(mockNavigate).toHaveBeenCalledWith(
      '/apuestas?match_id=99&outcome=HOME&odds=1.47',
    )
  })

  it('NO muestra botón "Registrar apuesta" cuando match_id es null', () => {
    render(
      <MemoryRouter>
        <SignalCard signal={makeSignal({ match_id: null })} onExplain={vi.fn()} />
      </MemoryRouter>,
    )
    expect(screen.queryByRole('button', { name: /registrar apuesta/i })).not.toBeInTheDocument()
  })
})
