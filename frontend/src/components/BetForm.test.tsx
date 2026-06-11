/**
 * Tests para BetForm — TDD RED antes de implementar el componente.
 * Estrategia: RTL + mocks de fetchAPI (no llamadas reales)
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import BetForm from './BetForm'
import type { UpcomingMatch } from '../api/types'

vi.mock('../api/client', () => ({
  fetchAPI: vi.fn(),
  ApiError: class ApiError extends Error {
    status: number
    fieldErrors?: Record<string, string>
    constructor(
      status: number,
      message: string,
      fieldErrors?: Record<string, string>,
    ) {
      super(message)
      this.name = 'ApiError'
      this.status = status
      this.fieldErrors = fieldErrors
    }
  },
}))

import { fetchAPI } from '../api/client'
const mockFetchAPI = vi.mocked(fetchAPI)

const makeMatch = (overrides: Partial<UpcomingMatch> = {}): UpcomingMatch => ({
  id: 42,
  match_date: '2026-06-15',
  kickoff_at: null,
  home_team: 'Argentina',
  away_team: 'Brasil',
  neutral_site: false,
  stage: 'GROUP',
  p_home: 0.45,
  p_draw: 0.27,
  p_away: 0.28,
  low_confidence: false,
  ...overrides,
})

function renderForm(matches: UpcomingMatch[] = [makeMatch()], initialPath = '/apuestas') {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <BetForm matches={matches} onSuccess={vi.fn()} />
    </MemoryRouter>,
  )
}

describe('BetForm (4.5)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('muestra el selector de partido con los equipos', () => {
    renderForm()
    expect(screen.getByRole('combobox', { name: /partido/i })).toBeInTheDocument()
    expect(screen.getByText(/Argentina vs Brasil/)).toBeInTheDocument()
  })

  it('muestra el selector de resultado con nombres de equipos al elegir partido', async () => {
    renderForm()
    const matchSelect = screen.getByRole('combobox', { name: /partido/i })
    fireEvent.change(matchSelect, { target: { value: '42' } })

    // findByRole espera el re-render async
    const outcomeSelect = await screen.findByRole('combobox', { name: /resultado/i })
    expect(outcomeSelect).toBeInTheDocument()
    expect(screen.getByText('Argentina gana')).toBeInTheDocument()
    expect(screen.getByText('Empate')).toBeInTheDocument()
    expect(screen.getByText('Brasil gana')).toBeInTheDocument()
  })

  it('envía POST /api/v1/bets con los campos correctos al hacer submit', async () => {
    mockFetchAPI.mockResolvedValueOnce({ id: 1 } as never)
    const { container } = renderForm()

    // Seleccionar partido
    fireEvent.change(screen.getByRole('combobox', { name: /partido/i }), {
      target: { value: '42' },
    })

    // Esperar que el select de resultado aparezca
    await screen.findByRole('combobox', { name: /resultado/i })

    fireEvent.change(screen.getByRole('combobox', { name: /resultado/i }), {
      target: { value: 'HOME' },
    })
    fireEvent.change(screen.getByLabelText(/cuota/i), { target: { value: '1.85' } })
    fireEvent.change(screen.getByLabelText(/stake/i), { target: { value: '12000' } })

    // Usar fireEvent.submit en el form para evitar problemas de validación HTML5 en jsdom
    fireEvent.submit(container.querySelector('form')!)

    await waitFor(() => {
      expect(mockFetchAPI).toHaveBeenCalledWith(
        '/v1/bets',
        expect.objectContaining({
          method: 'POST',
          body: expect.stringContaining('"match_id":42'),
        }),
      )
    })
  })

  it('muestra error de campo (422) debajo del input correspondiente', async () => {
    // Usar un objeto duck-typed (no instanceof) para simular ApiError
    const err = { status: 422, message: 'Validation error', fieldErrors: { stake: 'must be > 0' } }
    mockFetchAPI.mockRejectedValueOnce(err)

    const { container } = renderForm()

    fireEvent.change(screen.getByRole('combobox', { name: /partido/i }), {
      target: { value: '42' },
    })
    await screen.findByRole('combobox', { name: /resultado/i })

    fireEvent.change(screen.getByRole('combobox', { name: /resultado/i }), {
      target: { value: 'HOME' },
    })
    fireEvent.change(screen.getByLabelText(/cuota/i), { target: { value: '1.85' } })
    fireEvent.change(screen.getByLabelText(/stake/i), { target: { value: '0' } })

    fireEvent.submit(container.querySelector('form')!)

    await waitFor(() => {
      expect(screen.getByText('must be > 0')).toBeInTheDocument()
    })
  })

  it('prefill desde query params ?match_id=42&outcome=HOME&odds=1.85', () => {
    renderForm([makeMatch()], '/apuestas?match_id=42&outcome=HOME&odds=1.85')

    // match_id=42 debe estar preseleccionado
    const matchSelect = screen.getByRole('combobox', { name: /partido/i })
    expect((matchSelect as HTMLSelectElement).value).toBe('42')

    // cuota debe estar prefillada
    expect((screen.getByLabelText(/cuota/i) as HTMLInputElement).value).toBe('1.85')
  })
})
