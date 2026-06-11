/**
 * Tests TDD para FuturesDashboard
 *
 * Escenarios:
 *   FD1: tabla de campeones muestra equipos rankeados con % y FlagLabel
 *   FD2: avance de grupo — tab muestra equipos con p_advance_group
 *   FD3: señales vacías → sección visible sin crash
 *   FD4: error de fetch → ErrorState con "Reintentar"
 *   FD5: loading → Spinner visible
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'

// Mockear el módulo de API antes de importar el componente
vi.mock('../api/futures', () => ({
  getFutures: vi.fn(),
  getFuturesSignals: vi.fn(),
}))

import { getFutures, getFuturesSignals } from '../api/futures'
import FuturesDashboard from './FuturesDashboard'

const mockGetFutures = vi.mocked(getFutures)
const mockGetFuturesSignals = vi.mocked(getFuturesSignals)

const FUTURES_FIXTURE = {
  champions: [
    {
      team_id: 1,
      team: 'Brasil',
      group: 'A',
      p_champion: 0.22,
      p_advance_group: 0.85,
      p_reach_sf: 0.60,
      p_reach_final: 0.45,
    },
    {
      team_id: 2,
      team: 'France',
      group: 'D',
      p_champion: 0.18,
      p_advance_group: 0.80,
      p_reach_sf: 0.50,
      p_reach_final: 0.35,
    },
    {
      team_id: 3,
      team: 'Germany',
      group: 'B',
      p_champion: 0.12,
      p_advance_group: 0.75,
      p_reach_sf: 0.40,
      p_reach_final: 0.25,
    },
  ],
}

const SIGNALS_FIXTURE = {
  items: [
    {
      signal_id: 1,
      team_id: 2,
      team: 'France',
      p_champion: 0.18,
      edge: 0.04,
      best_odds: 7.14,
      bookmaker: 'bet365',
    },
  ],
}

function renderWithProviders(ui: React.ReactElement) {
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

describe('FuturesDashboard', () => {
  beforeEach(() => vi.clearAllMocks())

  it('FD1: muestra tabla de campeones rankeada con porcentajes', async () => {
    mockGetFutures.mockResolvedValue(FUTURES_FIXTURE)
    mockGetFuturesSignals.mockResolvedValue({ items: [] })

    renderWithProviders(<FuturesDashboard />)

    await waitFor(() => {
      // La tabla debe mostrar el primer equipo con su p_champion en %
      expect(screen.getByText('Brasil')).toBeInTheDocument()
      expect(screen.getByText('22.0%')).toBeInTheDocument()
    })

    // Primer equipo tiene mayor p_champion — aparece primero
    const rows = screen.getAllByTestId('champion-row')
    expect(rows).toHaveLength(3)
    expect(rows[0]).toHaveTextContent('Brasil')
    expect(rows[1]).toHaveTextContent('France')
    expect(rows[2]).toHaveTextContent('Germany')
  })

  it('FD1 triangulación: France muestra 18.0% como p_champion', async () => {
    mockGetFutures.mockResolvedValue(FUTURES_FIXTURE)
    mockGetFuturesSignals.mockResolvedValue({ items: [] })

    renderWithProviders(<FuturesDashboard />)

    await waitFor(() => {
      expect(screen.getByText('18.0%')).toBeInTheDocument()
      expect(screen.getByText('12.0%')).toBeInTheDocument()
    })
  })

  it('FD2: tab Advance Group muestra equipos con p_advance_group', async () => {
    mockGetFutures.mockResolvedValue(FUTURES_FIXTURE)
    mockGetFuturesSignals.mockResolvedValue({ items: [] })

    renderWithProviders(<FuturesDashboard />)

    // Esperar que los datos carguen
    await waitFor(() => expect(screen.getByText('Brasil')).toBeInTheDocument())

    // Hacer click en tab "Avance Grupo"
    fireEvent.click(screen.getByRole('tab', { name: /avance grupo/i }))

    await waitFor(() => {
      // Debe mostrar p_advance_group de Brasil como 85.0%
      expect(screen.getByText('85.0%')).toBeInTheDocument()
    })
  })

  it('FD3: sin señales → sección de señales visible sin crash', async () => {
    mockGetFutures.mockResolvedValue(FUTURES_FIXTURE)
    mockGetFuturesSignals.mockResolvedValue({ items: [] })

    renderWithProviders(<FuturesDashboard />)

    await waitFor(() => expect(screen.getByText('Brasil')).toBeInTheDocument())

    // La sección de señales debe existir aunque esté vacía
    expect(screen.getByText('Señales +EV Futuros')).toBeInTheDocument()
    expect(screen.getByText(/sin señales/i)).toBeInTheDocument()
  })

  it('FD3b: con señal → muestra edge y bookmaker', async () => {
    mockGetFutures.mockResolvedValue(FUTURES_FIXTURE)
    mockGetFuturesSignals.mockResolvedValue(SIGNALS_FIXTURE)

    renderWithProviders(<FuturesDashboard />)

    await waitFor(() => {
      // Edge badge de la señal: +4.0%
      expect(screen.getByText('+4.0%')).toBeInTheDocument()
      // Bookmaker
      expect(screen.getByText(/bet365/)).toBeInTheDocument()
    })
  })

  it('FD4: error de fetch muestra ErrorState con Reintentar', async () => {
    mockGetFutures.mockRejectedValue(new Error('API no disponible'))
    mockGetFuturesSignals.mockResolvedValue({ items: [] })

    renderWithProviders(<FuturesDashboard />)

    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument()
      expect(screen.getByText('Reintentar')).toBeInTheDocument()
    })
  })

  it('FD5: estado loading muestra Spinner', () => {
    // Promesa que nunca resuelve → estado loading permanente
    mockGetFutures.mockReturnValue(new Promise(() => {}))
    mockGetFuturesSignals.mockResolvedValue({ items: [] })

    renderWithProviders(<FuturesDashboard />)

    expect(screen.getByRole('status')).toBeInTheDocument()
  })
})
