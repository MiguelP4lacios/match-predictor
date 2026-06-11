import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { CuponProvider } from '../context/CuponContext'
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

/** Helper — CuponProvider es requerido por AddToCuponButton */
function renderCard(signal: SignalItem, onExplain = vi.fn()) {
  return render(
    <CuponProvider>
      <SignalCard signal={signal} onExplain={onExplain} />
    </CuponProvider>,
  )
}

function renderCardInRouter(signal: SignalItem, onExplain = vi.fn()) {
  return render(
    <CuponProvider>
      <MemoryRouter>
        <SignalCard signal={signal} onExplain={onExplain} />
      </MemoryRouter>
    </CuponProvider>,
  )
}

describe('SignalCard', () => {
  describe('escenario id=10 — México HOME (verbatim spec)', () => {
    it('muestra badge de edge "14.7%"', () => {
      renderCard(makeSignal())
      expect(screen.getByText('14.7%')).toBeInTheDocument()
    })

    it('muestra stake "$120.16"', () => {
      renderCard(makeSignal())
      expect(screen.getByText('$120.16')).toBeInTheDocument()
    })

    it('muestra cuota "1.47 (gtbets)"', () => {
      renderCard(makeSignal())
      expect(screen.getByText('1.47 (gtbets)')).toBeInTheDocument()
    })

    it('muestra "Apostale a México" para outcome HOME', () => {
      renderCard(makeSignal())
      expect(screen.getByText('Apostale a México')).toBeInTheDocument()
    })

    it('muestra botón "¿Por qué? →"', () => {
      renderCard(makeSignal())
      expect(screen.getByRole('button', { name: /¿Por qué/ })).toBeInTheDocument()
    })

    it('llama a onExplain(id) al pulsar "¿Por qué? →"', () => {
      const onExplain = vi.fn()
      renderCard(makeSignal({ id: 10 }), onExplain)
      fireEvent.click(screen.getByRole('button', { name: /¿Por qué/ }))
      expect(onExplain).toHaveBeenCalledWith(10)
    })

    it('muestra la fecha y el partido en el header', () => {
      renderCard(makeSignal())
      expect(screen.getByText(/2026-06-11/)).toBeInTheDocument()
      expect(screen.getByText(/México vs South Africa/)).toBeInTheDocument()
    })
  })

  describe('outcomes humanizados', () => {
    it('DRAW → "Apostale a Empate"', () => {
      renderCard(makeSignal({ outcome_code: 'DRAW' }))
      expect(screen.getByText('Apostale a Empate')).toBeInTheDocument()
    })

    it('AWAY → "Apostale a South Africa" (via away_team del fixture)', () => {
      renderCard(makeSignal({ outcome_code: 'AWAY' }))
      expect(screen.getByText('Apostale a South Africa')).toBeInTheDocument()
    })
  })

  describe('formatters reusados (sin aritmética propia)', () => {
    it('edge=0.064 → badge "6.4%"', () => {
      renderCard(makeSignal({ edge: 0.064, recommended_stake: '18.93' }))
      expect(screen.getByText('6.4%')).toBeInTheDocument()
    })

    it('recommended_stake="18.93" → "$18.93"', () => {
      renderCard(makeSignal({ edge: 0.064, recommended_stake: '18.93' }))
      expect(screen.getByText('$18.93')).toBeInTheDocument()
    })
  })
})

describe('Registrar apuesta button (4.8)', () => {
  it('el badge de edge dice "la cuota paga de más" — nunca "ventaja" a secas (ambiguo)', () => {
    renderCardInRouter(makeSignal({ edge: 0.064 }))
    expect(screen.getByText('la cuota paga de más')).toBeInTheDocument()
    expect(screen.queryByText(/^ventaja$/)).not.toBeInTheDocument()
  })

  it('botón "Registrar apuesta" navega a /apuestas con match_id, outcome y odds', () => {
    mockNavigate.mockClear()
    renderCardInRouter(makeSignal({ match_id: 99, outcome_code: 'HOME', best_odds: 1.47 }))
    fireEvent.click(screen.getByRole('button', { name: /registrar apuesta/i }))
    expect(mockNavigate).toHaveBeenCalledWith(
      '/apuestas?match_id=99&outcome=HOME&odds=1.47',
    )
  })

  it('NO muestra botón "Registrar apuesta" cuando match_id es null', () => {
    renderCardInRouter(makeSignal({ match_id: null }))
    expect(screen.queryByRole('button', { name: /registrar apuesta/i })).not.toBeInTheDocument()
  })
})
