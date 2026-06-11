/**
 * Integration tests — MatchesPage
 * Regresión del bug "solo 2 partidos de Colombia": el default del server (limit=50)
 * cortaba los 72 fixtures de grupos. La página DEBE pedir limit=200.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { CuponProvider } from '../context/CuponContext'
import MatchesPage from './MatchesPage'
import type { UpcomingMatch } from '../api/types'

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
      <CuponProvider>{ui}</CuponProvider>
    </QueryClientProvider>,
  )
}

function match(partial: Partial<UpcomingMatch>): UpcomingMatch {
  return {
    id: 1,
    match_date: '2026-06-17',
    kickoff_at: null,
    home_team: 'Local FC',
    away_team: 'Visita FC',
    neutral_site: true,
    low_confidence: false,
    p_home: 0.4,
    p_draw: 0.3,
    p_away: 0.3,
    ...partial,
  } as UpcomingMatch
}

describe('MatchesPage', () => {
  beforeEach(() => vi.clearAllMocks())

  it('pide limit=200 al server (el default 50 corta los 72 de grupos)', async () => {
    mockFetchAPI.mockResolvedValue([])

    renderWithQuery(<MatchesPage />)

    await waitFor(() => {
      expect(mockFetchAPI).toHaveBeenCalledWith('/v1/matches/upcoming?limit=200')
    })
  })

  it('renderiza partidos de TODAS las fechas devueltas (sin recortar)', async () => {
    mockFetchAPI.mockResolvedValue([
      match({ id: 1, match_date: '2026-06-17', home_team: 'Uzbekistan', away_team: 'Colombia' }),
      match({ id: 2, match_date: '2026-06-23', home_team: 'Colombia', away_team: 'DR Congo' }),
      match({ id: 3, match_date: '2026-06-27', home_team: 'Colombia', away_team: 'Portugal' }),
    ])

    renderWithQuery(<MatchesPage />)

    // Uzbekistan appears only in match 1 — unique identifier
    await waitFor(() => {
      expect(screen.getByText('Uzbekistan')).toBeInTheDocument()
    })
    // DR Congo and Portugal each appear once
    expect(screen.getByText('DR Congo')).toBeInTheDocument()
    expect(screen.getByText('Portugal')).toBeInTheDocument()
    // Date header for the last date group
    expect(screen.getByText('2026-06-27')).toBeInTheDocument()
  })
})
