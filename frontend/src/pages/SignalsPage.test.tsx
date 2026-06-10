/**
 * Integration tests — SignalsPage
 * QueryClient wrapper + mocked fetchAPI → verifica data flow real
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import SignalsPage from './SignalsPage'

vi.mock('../api/client', () => ({
  fetchAPI: vi.fn(),
}))

import { fetchAPI } from '../api/client'
const mockFetchAPI = vi.mocked(fetchAPI)

function renderWithQuery(ui: React.ReactElement) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>)
}

const SIGNAL_FIXTURE = {
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
  edge: 0.0832,
  ev: 0.05,
  kelly_fraction: 0.04,
  recommended_stake: '80.00',
  captured_at: '2026-06-15T10:00:00',
}

describe('SignalsPage', () => {
  beforeEach(() => vi.clearAllMocks())

  describe('con datos del servidor', () => {
    it('renderiza la fila de la señal cuando la query resuelve', async () => {
      mockFetchAPI.mockResolvedValue({ items: [SIGNAL_FIXTURE], total: 1 })

      renderWithQuery(<SignalsPage />)

      await waitFor(() => {
        expect(screen.getByText('España vs Brasil')).toBeInTheDocument()
      })
      expect(screen.getByText('8.3%')).toBeInTheDocument()
    })

    it('muestra múltiples señales en el orden dado por el server', async () => {
      mockFetchAPI.mockResolvedValue({
        items: [
          { ...SIGNAL_FIXTURE, id: 1, home_team: 'España', away_team: 'Brasil', edge: 0.20 },
          { ...SIGNAL_FIXTURE, id: 2, home_team: 'Francia', away_team: 'Alemania', edge: 0.10 },
        ],
        total: 2,
      })

      renderWithQuery(<SignalsPage />)

      await waitFor(() => {
        expect(screen.getByText('España vs Brasil')).toBeInTheDocument()
      })
      expect(screen.getByText('Francia vs Alemania')).toBeInTheDocument()
    })
  })

  describe('estado vacío', () => {
    it('muestra empty state cuando items=[]', async () => {
      mockFetchAPI.mockResolvedValue({ items: [], total: 0 })

      renderWithQuery(<SignalsPage />)

      await waitFor(() => {
        expect(screen.getByText('Sin señales con ese filtro')).toBeInTheDocument()
      })
    })
  })

  describe('estado de error', () => {
    it('muestra ErrorBanner cuando la query falla', async () => {
      mockFetchAPI.mockRejectedValue(new Error('500 Internal Server Error'))

      renderWithQuery(<SignalsPage />)

      await waitFor(() => {
        expect(screen.getByRole('alert')).toBeInTheDocument()
      })
    })
  })
})
