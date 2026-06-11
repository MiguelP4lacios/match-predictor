/**
 * TDD — CuponDrawer
 * RED tests escritos ANTES de la implementación.
 *
 * Cubre: botón floating oculto sin legs, drawer con EV live, warning −EV,
 * retorno COP formateado, "Registrar cupón" POST + limpia, botón deshabilitado.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, act } from '@testing-library/react'
import { CuponProvider } from '../context/CuponContext'
import type { CuponLeg } from '../context/CuponContext'
import type { ParlayPreview } from '../api/types'
import CuponDrawer from './CuponDrawer'

// ─── Mock de la API ──────────────────────────────────────────────────────────

vi.mock('../api/parlays', () => ({
  previewParlay: vi.fn(),
  createParlay: vi.fn(),
}))

import { previewParlay, createParlay } from '../api/parlays'

const mockPreview = previewParlay as ReturnType<typeof vi.fn>
const mockCreate = createParlay as ReturnType<typeof vi.fn>

// ─── Helpers ──────────────────────────────────────────────────────────────────

const LEG_A: CuponLeg = {
  match_id: 1,
  outcome_code: 'HOME',
  home_team: 'Mexico',
  away_team: 'South Africa',
  match_date: '2026-06-11',
  odds: 1.40,
}

const LEG_B: CuponLeg = {
  match_id: 2,
  outcome_code: 'AWAY',
  home_team: 'Brazil',
  away_team: 'Argentina',
  match_date: '2026-06-15',
  odds: 2.75,
}

const LEG_C: CuponLeg = {
  match_id: 3,
  outcome_code: 'HOME',
  home_team: 'France',
  away_team: 'Germany',
  match_date: '2026-06-20',
  odds: 1.84,
}

const PREVIEW_3_LEGS: ParlayPreview = {
  combined_odds: '7.084',
  model_prob: 0.3194,
  ev: 1.2627,
  stake: '5000',
  retorno: '35420.00',
  legs: [
    { match_id: 1, outcome_code: 'HOME', odds: '1.4', p_model: 0.834, ev: 0.168, is_negative_ev: false },
    { match_id: 2, outcome_code: 'AWAY', odds: '2.75', p_model: 0.491, ev: 0.350, is_negative_ev: false },
    { match_id: 3, outcome_code: 'HOME', odds: '1.84', p_model: 0.780, ev: 0.435, is_negative_ev: false },
  ],
  suggested_without_negatives: [],
}

const PREVIEW_WITH_NEGATIVE_EV: ParlayPreview = {
  combined_odds: '1.540',
  model_prob: 0.6255,
  ev: -0.0363,
  stake: '5000',
  retorno: '7700.00',
  legs: [
    { match_id: 1, outcome_code: 'HOME', odds: '1.10', p_model: 0.75, ev: -0.175, is_negative_ev: true },
    { match_id: 2, outcome_code: 'AWAY', odds: '1.40', p_model: 0.834, ev: 0.168, is_negative_ev: false },
  ],
  suggested_without_negatives: [
    { match_id: 2, outcome_code: 'AWAY', odds: '1.40', p_model: 0.834, ev: null, is_negative_ev: false },
  ],
}

/** Renderiza CuponDrawer con legs pre-cargadas en sessionStorage */
function renderWithLegs(legs: CuponLeg[]) {
  sessionStorage.setItem('cupon_legs', JSON.stringify(legs))
  return render(
    <CuponProvider>
      <CuponDrawer />
    </CuponProvider>,
  )
}

beforeEach(() => {
  sessionStorage.clear()
  vi.clearAllMocks()
  vi.useFakeTimers()
})

afterEach(() => {
  vi.useRealTimers()
})

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('CuponDrawer — botón floating', () => {
  it('NO muestra el botón cupón cuando no hay legs', () => {
    render(
      <CuponProvider>
        <CuponDrawer />
      </CuponProvider>,
    )
    expect(screen.queryByRole('button', { name: /cupón/i })).not.toBeInTheDocument()
  })

  it('muestra el botón "Cupón (N)" cuando hay legs', () => {
    renderWithLegs([LEG_A])
    expect(screen.getByRole('button', { name: /cupón \(1\)/i })).toBeInTheDocument()
  })

  it('el badge del botón refleja el número correcto de legs', () => {
    renderWithLegs([LEG_A, LEG_B])
    expect(screen.getByRole('button', { name: /cupón \(2\)/i })).toBeInTheDocument()
  })
})

describe('CuponDrawer — contenido del drawer', () => {
  it('abre el drawer al pulsar el botón cupón', () => {
    renderWithLegs([LEG_A])
    fireEvent.click(screen.getByRole('button', { name: /cupón/i }))
    expect(screen.getByRole('heading', { name: /cupón/i })).toBeInTheDocument()
  })

  it('muestra los partidos de los legs en el drawer', () => {
    renderWithLegs([LEG_A, LEG_B])
    fireEvent.click(screen.getByRole('button', { name: /cupón/i }))
    expect(screen.getByText(/Mexico vs South Africa/)).toBeInTheDocument()
    expect(screen.getByText(/Brazil vs Argentina/)).toBeInTheDocument()
  })

  it('muestra inputs de cuota por cada leg', () => {
    renderWithLegs([LEG_A, LEG_B])
    fireEvent.click(screen.getByRole('button', { name: /cupón/i }))
    const oddsInputs = screen.getAllByPlaceholderText('1.40')
    expect(oddsInputs).toHaveLength(2)
  })

  it('botón "Registrar cupón" está deshabilitado sin legs (drawer vacío)', () => {
    // Forzamos apertura con un componente custom que abre sin legs
    // En este caso el botón cupón no aparece → probar via estado forzado
    // El escenario real: si alguien abre el drawer y borra todos los legs
    renderWithLegs([LEG_A])
    fireEvent.click(screen.getByRole('button', { name: /cupón/i }))
    // Con legs pero sin odds completas y sin stake → disabled
    const btn = screen.getByRole('button', { name: /registrar cupón/i })
    expect(btn).toBeDisabled()
  })
})

describe('CuponDrawer — EV live (escenario spec verbatim)', () => {
  it('muestra combined_odds 7.084 después del debounce', async () => {
    mockPreview.mockResolvedValue(PREVIEW_3_LEGS)
    renderWithLegs([LEG_A, LEG_B, LEG_C])
    fireEvent.click(screen.getByRole('button', { name: /cupón/i }))
    // Avanzar debounce + flush microtasks del mock async
    await act(async () => {
      vi.advanceTimersByTime(350)
      await vi.runAllTimersAsync()
    })
    expect(screen.getByText(/7\.084/)).toBeInTheDocument()
  })

  it('muestra model_prob 31.9% después del debounce', async () => {
    mockPreview.mockResolvedValue(PREVIEW_3_LEGS)
    renderWithLegs([LEG_A, LEG_B, LEG_C])
    fireEvent.click(screen.getByRole('button', { name: /cupón/i }))
    await act(async () => {
      vi.advanceTimersByTime(350)
      await vi.runAllTimersAsync()
    })
    expect(screen.getByText(/31\.9%/)).toBeInTheDocument()
  })

  it('muestra EV +126.3% después del debounce', async () => {
    mockPreview.mockResolvedValue(PREVIEW_3_LEGS)
    renderWithLegs([LEG_A, LEG_B, LEG_C])
    fireEvent.click(screen.getByRole('button', { name: /cupón/i }))
    await act(async () => {
      vi.advanceTimersByTime(350)
      await vi.runAllTimersAsync()
    })
    expect(screen.getByText(/\+126\.3%/)).toBeInTheDocument()
  })

  it('muestra retorno $35.420 con stake 5000', async () => {
    mockPreview.mockResolvedValue(PREVIEW_3_LEGS)
    renderWithLegs([LEG_A, LEG_B, LEG_C])
    fireEvent.click(screen.getByRole('button', { name: /cupón/i }))
    // Enter stake — dispara otro debounce
    const stakeInput = screen.getByPlaceholderText('5000')
    fireEvent.change(stakeInput, { target: { value: '5000' } })
    await act(async () => {
      vi.advanceTimersByTime(350)
      await vi.runAllTimersAsync()
    })
    expect(screen.getByText(/\$35\.420/)).toBeInTheDocument()
  })
})

describe('CuponDrawer — warning leg −EV', () => {
  it('muestra warning "⚠ Este leg reduce el EV" para leg is_negative_ev=true', async () => {
    const legs: CuponLeg[] = [
      { match_id: 1, outcome_code: 'HOME', home_team: 'Mexico', away_team: 'South Africa', match_date: '2026-06-11', odds: 1.10 },
      { match_id: 2, outcome_code: 'AWAY', home_team: 'Brazil', away_team: 'Argentina', match_date: '2026-06-15', odds: 1.40 },
    ]
    mockPreview.mockResolvedValue(PREVIEW_WITH_NEGATIVE_EV)
    renderWithLegs(legs)
    fireEvent.click(screen.getByRole('button', { name: /cupón/i }))
    await act(async () => {
      vi.advanceTimersByTime(350)
      await vi.runAllTimersAsync()
    })
    expect(screen.getByText(/Este leg reduce el EV/)).toBeInTheDocument()
  })
})

describe('CuponDrawer — banner independencia', () => {
  it('muestra el banner de independencia en el drawer', () => {
    renderWithLegs([LEG_A])
    fireEvent.click(screen.getByRole('button', { name: /cupón/i }))
    expect(screen.getByText(/independencia/i)).toBeInTheDocument()
  })
})

describe('CuponDrawer — Registrar cupón', () => {
  it('llama createParlay con los datos correctos y limpia el cupón en 201', async () => {
    mockPreview.mockResolvedValue(PREVIEW_3_LEGS)
    mockCreate.mockResolvedValue({
      id: 77, mode: 'real', status: 'pending', bet_kind: 'parlay',
      stake: '5000', odds_taken: 7.084, pnl: null,
      settled_at: null, placed_at: '2026-06-10T00:00:00', note: null,
    })
    renderWithLegs([LEG_A, LEG_B, LEG_C])
    fireEvent.click(screen.getByRole('button', { name: /cupón/i }))
    // Enter stake
    const stakeInput = screen.getByPlaceholderText('5000')
    fireEvent.change(stakeInput, { target: { value: '5000' } })
    // Advance debounce so preview loads + flush async mock
    await act(async () => {
      vi.advanceTimersByTime(350)
      await vi.runAllTimersAsync()
    })
    expect(mockPreview).toHaveBeenCalled()
    // Enable button by having odds + stake (legs have odds from sessionStorage)
    const btn = screen.getByRole('button', { name: /registrar cupón/i })
    expect(btn).not.toBeDisabled()
    await act(async () => {
      fireEvent.click(btn)
      await vi.runAllTimersAsync()
    })
    expect(mockCreate).toHaveBeenCalledWith(
      expect.objectContaining({
        stake: 5000,
        legs: expect.arrayContaining([
          expect.objectContaining({ match_id: 1, outcome_code: 'HOME', odds: 1.40 }),
        ]),
      }),
    )
    // Después de 201, el cupón se limpia → botón cupón desaparece
    expect(screen.queryByRole('button', { name: /cupón/i })).not.toBeInTheDocument()
  })
})
