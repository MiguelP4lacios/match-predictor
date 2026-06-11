/**
 * Integration tests — SignalsPage
 * QueryClient wrapper + mocked fetchAPI → verifica data flow real
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
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
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        {ui}
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

const SIGNAL_FIXTURE = {
  id: 1,
  match_id: null,
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
    it('renderiza tarjetas con nombre de partido (NO tabla)', async () => {
      mockFetchAPI.mockResolvedValue({ items: [SIGNAL_FIXTURE], total: 1 })

      renderWithQuery(<SignalsPage />)

      await waitFor(() => {
        expect(screen.getByText('España vs Brasil')).toBeInTheDocument()
      })
      expect(screen.getByText('8.3%')).toBeInTheDocument()
      // La especificación prohíbe <table> — la página usa tarjetas
      expect(screen.queryByRole('table')).not.toBeInTheDocument()
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

    it('cada tarjeta tiene botón "¿Por qué? →"', async () => {
      mockFetchAPI.mockResolvedValue({ items: [SIGNAL_FIXTURE], total: 1 })

      renderWithQuery(<SignalsPage />)

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /¿Por qué\?/i })).toBeInTheDocument()
      })
    })
  })

  describe('interacción con ExplainDrawer', () => {
    it('clic en "¿Por qué? →" abre el drawer y llama a /v1/signals/{id}/explain', async () => {
      // Primera llamada: listado de señales
      mockFetchAPI.mockResolvedValueOnce({ items: [SIGNAL_FIXTURE], total: 1 })
      // Segunda llamada: explicación (lazy)
      mockFetchAPI.mockResolvedValueOnce({
        signal_id: 1,
        sections: [
          {
            key: 'apuesta',
            titulo: 'La apuesta',
            note: null,
            steps: [
              { key: 'p_model', label_es: 'P(modelo)', raw: 0.55, formatted: null, glossary_term: null },
            ],
          },
        ],
      })

      renderWithQuery(<SignalsPage />)

      // Esperar a que cargue la lista
      await waitFor(() => {
        expect(screen.getByRole('button', { name: /¿Por qué\?/i })).toBeInTheDocument()
      })

      // Hacer clic en "¿Por qué? →"
      fireEvent.click(screen.getByRole('button', { name: /¿Por qué\?/i }))

      // El drawer debe abrirse (role=dialog)
      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument()
      })

      // fetchAPI debe haber sido llamado con la URL de explain
      expect(mockFetchAPI).toHaveBeenCalledWith(`/v1/signals/${SIGNAL_FIXTURE.id}/explain`)
    })

    it('clic en X del drawer lo cierra', async () => {
      mockFetchAPI.mockResolvedValueOnce({ items: [SIGNAL_FIXTURE], total: 1 })
      mockFetchAPI.mockResolvedValueOnce({ signal_id: 1, sections: [] })

      renderWithQuery(<SignalsPage />)

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /¿Por qué\?/i })).toBeInTheDocument()
      })

      fireEvent.click(screen.getByRole('button', { name: /¿Por qué\?/i }))

      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument()
      })

      // Cerrar con el botón X (aria-label="Cerrar explicación")
      fireEvent.click(screen.getByRole('button', { name: /Cerrar explicación/i }))

      await waitFor(() => {
        expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
      })
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
