/**
 * Tests para BetsPage — TDD RED antes de implementar.
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

function renderPage(initialPath = '/apuestas') {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[initialPath]}>
        <BetsPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('BetsPage (4.7)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('muestra stats PAPER y REAL', async () => {
    mockFetchAPI.mockImplementation((path: string) => {
      if (path === '/v1/paper') {
        return Promise.resolve({
          paper: { ...emptyModeStats, total: 5, roi: null },
          real: { ...emptyModeStats, total: 2, staked: '24000', returns: '28800', roi: 0.20 },
        })
      }
      if (path === '/v1/bets') return Promise.resolve({ items: [], total: 0 })
      if (path.includes('/v1/matches/upcoming')) return Promise.resolve([])
      return Promise.resolve(null)
    })

    renderPage()

    await waitFor(() => {
      expect(screen.getByText('Paper')).toBeInTheDocument()
      expect(screen.getByText('Real')).toBeInTheDocument()
    })
  })

  it('ModeStatsBlock REAL: roi=null → "—"', async () => {
    mockFetchAPI.mockImplementation((path: string) => {
      if (path === '/v1/paper') {
        return Promise.resolve({
          paper: emptyModeStats,
          real: emptyModeStats,
        })
      }
      if (path === '/v1/bets') return Promise.resolve({ items: [], total: 0 })
      if (path.includes('/v1/matches/upcoming')) return Promise.resolve([])
      return Promise.resolve(null)
    })

    renderPage()

    await waitFor(() => {
      // Should show "—" for roi null — at least two (paper + real)
      const dashes = screen.getAllByText('—')
      expect(dashes.length).toBeGreaterThanOrEqual(2)
    })
  })

  it('ModeStatsBlock REAL: roi=0.20 → "+20.0%"', async () => {
    mockFetchAPI.mockImplementation((path: string) => {
      if (path === '/v1/paper') {
        return Promise.resolve({
          paper: emptyModeStats,
          real: { ...emptyModeStats, total: 2, settled: 2, won: 2, staked: '24000', returns: '28800', roi: 0.20 },
        })
      }
      if (path === '/v1/bets') return Promise.resolve({ items: [], total: 0 })
      if (path.includes('/v1/matches/upcoming')) return Promise.resolve([])
      return Promise.resolve(null)
    })

    renderPage()

    await waitFor(() => {
      expect(screen.getByText('+20.0%')).toBeInTheDocument()
    })
  })
})
