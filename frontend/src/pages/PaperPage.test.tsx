/**
 * PaperPage es redirigido a /apuestas — tests adaptados al nuevo shape.
 * El componente PaperPage ya no existe como página activa.
 * BetsPage.test.tsx cubre la nueva ruta.
 * Este archivo mantiene compatibilidad de importación para no borrar tests existentes.
 *
 * NOTE: PaperPage fue reemplazada por BetsPage + redirect /paper → /apuestas.
 * Tests de BetsPage en BetsPage.test.tsx
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import BetsPage from './BetsPage'

vi.mock('../api/client', () => ({
  fetchAPI: vi.fn(),
}))

import { fetchAPI } from '../api/client'
const mockFetchAPI = vi.mocked(fetchAPI)

const emptyModeStats = {
  total: 0,
  pending: 0,
  settled: 0,
  won: 0,
  lost: 0,
  staked: null,
  returns: null,
  roi: null,
}

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <BetsPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('BetsPage (formerly PaperPage) — per-mode stats', () => {
  beforeEach(() => vi.clearAllMocks())

  it('muestra "—" para ROI null (sin apuestas cerradas)', async () => {
    mockFetchAPI.mockImplementation((path: string) => {
      if (path === '/v1/paper') {
        return Promise.resolve({ paper: emptyModeStats, real: emptyModeStats })
      }
      if (path === '/v1/bets') return Promise.resolve([])
      if (path.includes('/v1/matches/upcoming')) return Promise.resolve([])
      return Promise.resolve(null)
    })

    renderPage()

    await waitFor(() => {
      const dashes = screen.getAllByText('—')
      expect(dashes.length).toBeGreaterThanOrEqual(2)
    })
    expect(screen.queryByText('0%')).not.toBeInTheDocument()
    expect(screen.queryByText('0.0%')).not.toBeInTheDocument()
  })

  it('muestra ROI positivo con signo + y %', async () => {
    mockFetchAPI.mockImplementation((path: string) => {
      if (path === '/v1/paper') {
        return Promise.resolve({
          paper: emptyModeStats,
          real: { ...emptyModeStats, total: 10, settled: 8, won: 6, roi: 0.125 },
        })
      }
      if (path === '/v1/bets') return Promise.resolve([])
      if (path.includes('/v1/matches/upcoming')) return Promise.resolve([])
      return Promise.resolve(null)
    })

    renderPage()

    await waitFor(() => {
      expect(screen.getByText('+12.5%')).toBeInTheDocument()
    })
  })
})
