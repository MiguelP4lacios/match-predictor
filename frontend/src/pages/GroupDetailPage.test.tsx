/**
 * Integration tests — GroupDetailPage (cierra warning del verify: R10/task 4.6)
 * MemoryRouter con /grupos/:letra + fetchAPI mockeado.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import GroupDetailPage from './GroupDetailPage'
import type { GroupDetail } from '../api/types'

vi.mock('../api/client', () => ({
  fetchAPI: vi.fn(),
}))

import { fetchAPI } from '../api/client'
const mockFetchAPI = vi.mocked(fetchAPI)

function renderAt(path: string) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/grupos/:letra" element={<GroupDetailPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

const GRUPO_K: GroupDetail = {
  name: 'K',
  teams: ['Colombia', 'Portugal', 'DR Congo', 'Uzbekistan'],
  standings: [
    { team_name: 'Colombia', pj: 0, g: 0, e: 0, p: 0, gf: 0, gc: 0, dg: 0, pts: 0 },
    { team_name: 'DR Congo', pj: 0, g: 0, e: 0, p: 0, gf: 0, gc: 0, dg: 0, pts: 0 },
    { team_name: 'Portugal', pj: 0, g: 0, e: 0, p: 0, gf: 0, gc: 0, dg: 0, pts: 0 },
    { team_name: 'Uzbekistan', pj: 0, g: 0, e: 0, p: 0, gf: 0, gc: 0, dg: 0, pts: 0 },
  ],
  fixtures: [
    {
      id: 1,
      match_date: '2026-06-17',
      home_team: 'Uzbekistan',
      away_team: 'Colombia',
      status: 'SCHEDULED',
      p_home: 0.167,
      p_draw: 0.23,
      p_away: 0.603,
    },
    {
      id: 2,
      match_date: '2026-06-27',
      home_team: 'Colombia',
      away_team: 'Portugal',
      status: 'SCHEDULED',
      p_home: 0.4202,
      p_draw: 0.2846,
      p_away: 0.2952,
    },
  ],
}

describe('GroupDetailPage', () => {
  beforeEach(() => vi.clearAllMocks())

  it('pide /v1/groups/:letra y muestra standings y fixtures del grupo', async () => {
    mockFetchAPI.mockResolvedValue(GRUPO_K)

    renderAt('/grupos/K')

    // Uzbekistan appears in standings + fixture 1 (at least 1 match rendered)
    await waitFor(() => {
      expect(screen.getAllByText('Uzbekistan').length).toBeGreaterThanOrEqual(1)
    })
    expect(mockFetchAPI).toHaveBeenCalledWith('/v1/groups/K')
    expect(screen.getByText('Grupo K')).toBeInTheDocument()
    // Colombia appears in standings + both fixtures
    expect(screen.getAllByText('Colombia').length).toBeGreaterThanOrEqual(1)
    // Portugal appears in fixture 2 and standings
    expect(screen.getAllByText('Portugal').length).toBeGreaterThanOrEqual(1)
  })

  it('muestra mensaje de error para letra desconocida (API 404)', async () => {
    mockFetchAPI.mockRejectedValue(new Error('404'))

    renderAt('/grupos/Z')

    await waitFor(() => {
      expect(screen.getByText(/Grupo desconocido o sin datos/)).toBeInTheDocument()
    })
  })
})
